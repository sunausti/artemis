# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

"""Deterministic checks for repeated UI actions and explicit search mis-targets."""

from collections import Counter
import hashlib
import json
import re


def search_target_conflict(name, args, elements):
    target = args.get("target")
    if name not in {"click", "tap", "input_text"} or type(target) is not int:
        return None
    if not 1 <= target <= len(elements):
        return None
    description = str(args.get("target_description", ""))
    if not re.search(r"search|搜索", description, re.I):
        return None
    element = elements[target - 1]
    label = str(element.get("text") or element.get("content-desc") or "")
    if re.search(
        r"扫一扫|扫码|扫描二维码|语音识别|语音搜索|scan\s*(?:qr|code)|voice\s*(?:search|input)",
        label,
        re.I,
    ):
        return (
            f"Target mismatch: index {target} is explicitly labelled '{label}', not a search field. "
            "Read the CURRENT UI list and choose the actual search box; do not retry this target. "
            "If no search box is listed, use ask_explorer or return from the scanner first."
        )
    return None


class LoopGuard:
    def __init__(self):
        self.visits = Counter()

    def check(self, name, args, elements, screenshot):
        # Waiting and scroll gestures can be intentional repetitions. Count only
        # point actions and app relaunches, against the entire current UI state.
        if name not in {"click", "tap", "long_press", "input_text", "manage_app"}:
            return None
        clean_elements = [
            {key: element.get(key) for key in ("text", "resource_id", "class", "bounds", "center")}
            for element in elements
        ]
        state = json.dumps(clean_elements, ensure_ascii=False, sort_keys=True)
        if not elements:
            state = hashlib.sha256(screenshot or b"").hexdigest()
        action = dict(args)
        action.pop("target_description", None)
        target = action.get("target")
        if type(target) is int and 1 <= target <= len(elements):
            action["target"] = clean_elements[target - 1]
        key = (name, state, json.dumps(action, ensure_ascii=False, sort_keys=True))
        self.visits[key] += 1
        if self.visits[key] >= 3:
            return "检测到同一界面反复执行同一操作，已停止以避免重复误操作。任务尚未完成。"
        return None
