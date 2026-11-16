# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

"""Voice worker fast launch; fall back to the regular CLI only before a side effect."""

import argparse
import asyncio
import os
import sys
import time
from types import SimpleNamespace

from artemis.runtime.adb_endpoint import adb_command
from artemis.runtime.app_catalog import device_catalog, simple_launch_name
from artemis.runtime.fast_launch import launch_known_app


async def execute(args) -> bool:
    name = simple_launch_name(args.goal)
    if not name or not args.device_serial:
        return False

    async def shell(command):
        proc = await asyncio.create_subprocess_exec(
            *adb_command(["-s", args.device_serial, "shell", command]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=12)
        except BaseException:
            if proc.returncode is None:
                proc.kill()
            await proc.wait()
            raise
        if proc.returncode:
            raise RuntimeError(err.decode(errors="replace")[:500])
        return out.decode(errors="replace")

    started = time.monotonic()
    try:
        catalog, user, installed = await device_catalog(
            shell,
            os.environ.get("ADB_SERVER_SOCKET", "local"),
            args.device_serial,
        )
        package = catalog.resolve(name, installed)
    except Exception:
        return False
    if not package:
        return False
    resolution_s = time.monotonic() - started
    from artemis.data_engine.engine import DataEngine
    from artemis.runtime.device_lock import DeviceExecutionLock
    from artemis.runtime.cancel_requests import watch_for_cancel_request

    ctx = SimpleNamespace(execution_setup=None, device=None)
    engine = DataEngine(ctx)
    lock = DeviceExecutionLock(device_id=args.device_serial, description=f"Fast launch {name}")
    locked = False
    session_started = False
    status = "failed"
    watcher = None
    task = asyncio.current_task()
    try:
        # Acquire is a blocking FIFO operation; the worker's cancellation
        # watcher cancels the thread wait through a shared event.
        import threading

        waiting_cancel = threading.Event()
        watcher = asyncio.create_task(
            watch_for_cancel_request(waiting_cancel.set, session_id=args.session_id)
        )
        await asyncio.to_thread(
            lock.acquire, blocking=True, timeout=15, cancel_event=waiting_cancel
        )
        locked = True
        engine.start_session(
            args.goal,
            {"profile": "flash", "execution_path": "fast_launch", "device_id": args.device_serial},
            args.session_id,
        )
        session_started = True
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)
        watcher = asyncio.create_task(
            watch_for_cancel_request(task.cancel, session_id=args.session_id)
        )
        if waiting_cancel.is_set():
            raise asyncio.CancelledError
        result = await launch_known_app(package, user, shell)
        status = "completed" if result["outcome"] == "opened" else "failed"
        result["timings"]["catalog_resolution_s"] = resolution_s
        result["timings"]["worker_total_s"] = time.monotonic() - started
        explanation = (
            f"已打开{name}。" if status == "completed" else f"未完成打开{name}：{result['message']}"
        )
        engine.record_trace(
            type="span",
            name="fast_app_launch",
            payload=result,
            duration=result["timings"]["worker_total_s"],
            status="success" if status == "completed" else "failed",
        )
        engine.record_step(
            action_taken={
                "action": "report_task_status",
                "args": {"status": status, "explanation": explanation},
            },
            extra_metadata={"fast_launch": result},
        )
        if status == "completed":
            try:
                catalog.remember(name, package)
            except OSError:
                pass  # Cache persistence must not change a successful launch.
    except asyncio.CancelledError:
        status = "cancelled"
    except Exception as exc:
        if session_started:
            engine.record_step(
                action_taken={
                    "action": "report_task_status",
                    "args": {"status": "failed", "explanation": str(exc)[:500]},
                }
            )
        else:
            raise
    finally:
        if watcher:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
        if session_started:
            engine.end_session(status)
        try:
            await engine.shutdown()
        finally:
            if locked:
                lock.release()
    return True


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("goal")
    parser.add_argument("--device-serial")
    parser.add_argument("--session-id")
    args, _ = parser.parse_known_args()
    if not asyncio.run(execute(args)):
        os.execv(sys.executable, [sys.executable, "-m", "artemis.main", *sys.argv[1:]])


if __name__ == "__main__":
    main()
