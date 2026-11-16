# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

"""Deterministic launch and actual resumed-activity verification, without an LLM."""

import asyncio
import re
import time

from artemis.runtime.app_catalog import PACKAGE

COMPONENT = re.compile(r"[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+")
RESUMED = re.compile(
    r"(?:topResumedActivity|mResumedActivity|ResumedActivity)[:=]\s*ActivityRecord\{[^}]*?\s([\w.]+)/([\w.$]+)\s"
)


async def launch_known_app(package: str, user: int, shell) -> dict:
    if not PACKAGE.fullmatch(package) or user < 0:
        raise ValueError("Invalid launch target")
    started = time.monotonic()
    timings = {}
    resolution = await shell(
        f"cmd package resolve-activity --brief --user {user} -a android.intent.action.MAIN "
        f"-c android.intent.category.LAUNCHER {package}"
    )
    components = [
        line.strip() for line in resolution.splitlines() if COMPONENT.fullmatch(line.strip())
    ]
    timings["activity_resolution_s"] = time.monotonic() - started
    if len(components) != 1 or components[0].split("/")[0] != package:
        return {
            "outcome": "failed",
            "message": "没有找到唯一的应用启动 Activity",
            "timings": timings,
        }
    before_launch = time.monotonic()
    output = await shell(f"am start --user {user} -W -n {components[0]}")
    timings["launch_command_s"] = time.monotonic() - before_launch
    if re.search(r"Error:|Exception|Permission Denial", output, re.I):
        return {"outcome": "failed", "message": output.strip()[:500], "timings": timings}
    before_check = time.monotonic()
    deadline = before_check + 5.0
    current = None
    while True:
        dump = await shell("dumpsys activity activities")
        match = RESUMED.search(dump)
        current = match[1] if match else None
        if current == package:
            outcome, message = "opened", "目标应用已在前台"
            break
        if current in {
            "com.android.settings",
            "com.android.car.settings",
            "com.android.permissioncontroller",
            "com.google.android.permissioncontroller",
        }:
            outcome, message = "blocked", f"启动后进入系统页面 {current}，尚未确认目标应用主界面"
            break
        if time.monotonic() >= deadline:
            outcome, message = "failed", f"未确认目标应用进入前台，当前为 {current or '未知'}"
            break
        await asyncio.sleep(0.25)
    timings["foreground_check_s"] = time.monotonic() - before_check
    timings["total_s"] = time.monotonic() - started
    return {
        "outcome": outcome,
        "message": message,
        "foreground_package": current,
        "timings": timings,
    }
