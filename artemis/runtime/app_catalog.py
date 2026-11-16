# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

"""Exact installed-app aliases shared by fast launch and the Hopper fallback."""

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

ALIASES = {
    "应用宝": ("com.tencent.android.qqdownloader",),
    "设置": ("com.android.settings", "com.android.car.settings"),
    "settings": ("com.android.settings", "com.android.car.settings"),
    "相机": ("com.android.camera2",),
    "camera": ("com.android.camera2",),
    "firefox": ("org.mozilla.firefox", "org.mozilla.fenix.debug"),
    "chrome": ("com.android.chrome", "org.chromium.chrome"),
}
PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+")


def simple_launch_name(goal: str) -> str | None:
    match = re.fullmatch(
        r"\s*(?:请)?(?:打开|启动|open\s+|launch\s+)([^\n。！!，,；;？?]+)[。！!]?\s*", goal, re.I
    )
    if not match:
        return None
    name = match[1].strip().strip("\"'“”")
    if (
        not name
        or len(name) > 80
        or re.search(r"并|然后|搜索|查看|进入|关闭|播放|安装|\band\b|\bthen\b", name, re.I)
    ):
        return None
    return name


class AppCatalog:
    TTL = 7 * 24 * 3600

    def __init__(self, directory: Path, identity: str):
        self.path = (
            directory / "app-catalog" / (hashlib.sha256(identity.encode()).hexdigest() + ".json")
        )

    def _entries(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def resolve(self, name: str, installed: set[str]) -> str | None:
        if PACKAGE.fullmatch(name) and name in installed:
            return name
        key = name.casefold().strip()
        candidates = [p for p in ALIASES.get(key, ()) if p in installed]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return None
        entry = self._entries().get(key)
        if isinstance(entry, dict) and time.time() - entry.get("saved_at", 0) < self.TTL:
            package = entry.get("package")
            if isinstance(package, str) and PACKAGE.fullmatch(package) and package in installed:
                return package
        return None

    def remember(self, name: str, package: str) -> None:
        if not PACKAGE.fullmatch(package):
            return
        entries = self._entries()
        entries[name.casefold().strip()] = {"package": package, "saved_at": time.time()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".catalog-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(entries, file, ensure_ascii=False)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


async def device_catalog(shell, endpoint: str, serial: str):
    """Use hardware identity and Android user; never share aliases across devices."""
    from artemis.config.paths import get_app_dir

    user = int((await shell("am get-current-user")).strip())
    hardware = (await shell("getprop ro.serialno")).strip()
    if not hardware:
        raise ValueError("Device identity unavailable")
    catalog = AppCatalog(get_app_dir(), f"{endpoint}/{serial}/{hardware}/user{user}")
    packages = await shell(f"pm list packages --user {user}")
    installed = {
        line.removeprefix("package:").strip()
        for line in packages.splitlines()
        if line.startswith("package:")
    }
    return catalog, user, installed
