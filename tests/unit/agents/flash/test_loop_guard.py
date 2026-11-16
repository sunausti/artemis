# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

from artemis.agents.flash.loop_guard import LoopGuard, search_target_conflict


def elements(index=30, text="扫一扫", resource="id/scan"):
    return [{"index": index, "text": text, "resource_id": resource, "center": [919, 47]}]


def test_search_description_cannot_target_explicit_scan_or_voice_control():
    args = {"target": 1, "target_description": "search input field"}
    assert "扫一扫" in search_target_conflict("click", args, elements())
    assert search_target_conflict("click", args, elements(text="语音识别"))
    assert search_target_conflict("click", args, elements(text="搜索")) is None
    assert (
        search_target_conflict(
            "click", {"target": 1, "target_description": "scan QR code"}, elements()
        )
        is None
    )
    assert (
        search_target_conflict(
            "click", {"target": [359, 33], "target_description": "search"}, elements()
        )
        is None
    )


def test_same_screen_action_cycle_is_stopped_on_third_visit_despite_index_changes():
    guard = LoopGuard()
    for visit in range(3):
        problem = guard.check("click", {"target": 1}, elements(index=visit + 1), b"ignored")
        if visit < 2:
            assert problem is None
        else:
            assert "重复" in problem
        guard.check(
            "press_key", {"key": "back"}, elements(text="返回", resource="id/back"), b"ignored"
        )


def test_changed_target_and_input_progress_do_not_trigger_loop():
    guard = LoopGuard()
    for i in range(10):
        assert guard.check("input_text", {"target": 1, "text": str(i)}, elements(), None) is None
    assert guard.check("click", {"target": 1}, elements(text="搜索"), None) is None


def test_invalid_indices_repeat_only_on_same_state():
    guard = LoopGuard()
    args = {"target": 958}
    assert guard.check("click", args, [], b"screen1") is None
    assert guard.check("click", args, [], b"screen2") is None
    assert guard.check("click", args, [], b"screen1") is None
    assert guard.check("click", args, [], b"screen1")
