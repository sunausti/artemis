# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# https://www.apache.org/licenses/LICENSE-2.0

"""Start the container's ADB server, verify its TCP target, then exec Artemis."""

import math
import os
import re
import subprocess
import sys
import time


def positive_number(name: str, default: str) -> float:
    value = float(os.environ.get(name, default))
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


def main() -> None:
    try:
        host = os.environ.get("ADB_HOST", "127.0.0.1")
        if host not in {"127.0.0.1", "localhost"}:
            raise ValueError("ADB_HOST must be loopback: this container owns its ADB server")
        port = int(os.environ.get("ADB_PORT", "5037"))
        if not 1 <= port <= 65535:
            raise ValueError("ADB_PORT must be between 1 and 65535")
        serial = os.environ.get("ADB_DEVICE_SERIAL", "127.0.0.1:5555")
        match = re.fullmatch(r"(?:[A-Za-z0-9._-]+|\[[0-9A-Fa-f:]+\]):([0-9]+)", serial)
        if not match or not 1 <= int(match[1]) <= 65535:
            raise ValueError(
                "ADB_DEVICE_SERIAL must be a TCP device address such as 127.0.0.1:5555"
            )
        socket = f"tcp:{host}:{port}"
        if os.environ.get("ADB_SERVER_SOCKET", socket) != socket:
            raise ValueError("ADB_SERVER_SOCKET conflicts with ADB_HOST/ADB_PORT")
        timeout = positive_number("ARTEMIS_ADB_CONNECT_TIMEOUT", "60")
        interval = positive_number("ARTEMIS_ADB_RETRY_INTERVAL", "2")
        command = sys.argv[1:]
        if not command:
            web_port = int(os.environ.get("PORT", "8000"))
            if not 1 <= web_port <= 65535:
                raise ValueError("PORT must be between 1 and 65535")
            command = [
                sys.executable,
                "-m",
                "apps.admin_console.server",
                "--host",
                os.environ.get("ARTEMIS_SERVER_HOST", "127.0.0.1"),
                "--port",
                str(web_port),
            ]
        os.environ.update(
            ADB_HOST=host, ADB_PORT=str(port), ADB_SERVER_SOCKET=socket, ADB_DEVICE_SERIAL=serial
        )
        adb = ["adb", "-H", host, "-P", str(port)]
        deadline = time.monotonic() + timeout

        def run_adb(*arguments: str) -> subprocess.CompletedProcess:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for Android device {serial}")
            return subprocess.run(
                [*adb, *arguments],
                capture_output=True,
                text=True,
                timeout=min(10.0, remaining),
            )

        started = run_adb("start-server")
        if started.returncode:
            raise RuntimeError(f"ADB server failed to start: {started.stderr.strip()}")
        print(f"[container] ADB server {socket}; Android target {serial}", flush=True)
        last_status = "unavailable"
        while time.monotonic() < deadline:
            try:
                connected = run_adb("connect", serial)
                state = run_adb("-s", serial, "get-state")
                last_status = " ".join(
                    part.strip()
                    for part in (state.stdout, state.stderr, connected.stdout)
                    if part.strip()
                )
                if "unauthorized" in last_status.lower():
                    raise RuntimeError(
                        f"Android device {serial} is unauthorized. Authorize this container's "
                        "ADB key on Android and persist /root/.android."
                    )
                if state.returncode == 0 and state.stdout.strip() == "device":
                    print(f"[container] Android target ready: {serial}", flush=True)
                    os.execvp(command[0], command)
            except subprocess.TimeoutExpired:
                last_status = "ADB command timed out"
            time.sleep(min(interval, max(0.0, deadline - time.monotonic())))
        raise TimeoutError(f"Timed out waiting for Android device {serial}: {last_status}")
    except (ValueError, OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as exc:
        print(f"[container] {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
