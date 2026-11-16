# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

import pytest


def test_simple_launch_parser_rejects_compound_and_vague_commands():
    from artemis.runtime.app_catalog import simple_launch_name

    assert simple_launch_name("打开应用宝") == "应用宝"
    assert simple_launch_name("请打开设置。") == "设置"
    assert simple_launch_name("open Firefox") == "Firefox"
    for text in (
        "打开",
        "打开设置并关闭蓝牙",
        "打开应用宝搜索微信",
        "打开设置查看蓝牙",
        "打开设置，不要修改",
    ):
        assert simple_launch_name(text) is None


def test_catalog_cache_persists_validates_packages_and_isolates_users(tmp_path):
    from artemis.runtime.app_catalog import AppCatalog

    catalog = AppCatalog(tmp_path, "device-endpoint-user0")
    installed = {"com.tencent.android.qqdownloader", "com.android.settings"}
    assert catalog.resolve("应用宝", installed) == "com.tencent.android.qqdownloader"
    catalog.remember("我的商店", "com.tencent.android.qqdownloader")
    assert (
        AppCatalog(tmp_path, "device-endpoint-user0").resolve("我的商店", installed)
        == "com.tencent.android.qqdownloader"
    )
    assert AppCatalog(tmp_path, "device-endpoint-user10").resolve("我的商店", installed) is None
    assert catalog.resolve("我的商店", {"com.android.settings"}) is None
    assert catalog.resolve("相机", installed) is None


@pytest.mark.asyncio
async def test_launch_uses_explicit_component_and_reports_permission_page_blocked(tmp_path):
    from artemis.runtime.fast_launch import launch_known_app

    calls = []

    async def shell(command):
        calls.append(command)
        if command.startswith("cmd package resolve-activity"):
            return "com.tencent.android.qqdownloader/.MainActivity"
        if command.startswith("am start"):
            return "Status: ok\nTotalTime: 123"
        return "topResumedActivity=ActivityRecord{abc u0 com.android.settings/.spa.SpaActivity t15}"

    result = await launch_known_app("com.tencent.android.qqdownloader", 0, shell)
    assert result["outcome"] == "blocked"
    assert any(
        "am start --user 0 -W -n com.tencent.android.qqdownloader/.MainActivity" == c for c in calls
    )
    assert "launch_command_s" in result["timings"]
    assert "foreground_check_s" in result["timings"]


@pytest.mark.asyncio
async def test_target_resumed_activity_is_required_for_opened():
    from artemis.runtime.fast_launch import launch_known_app

    async def shell(command):
        if command.startswith("cmd package"):
            return "com.android.settings/.Settings"
        if command.startswith("am start"):
            return "Status: ok"
        return "topResumedActivity=ActivityRecord{abc u0 com.android.settings/.Settings t15}"

    result = await launch_known_app("com.android.settings", 0, shell)
    assert result["outcome"] == "opened"


@pytest.mark.asyncio
async def test_failed_launch_is_not_reported_opened():
    from artemis.runtime.fast_launch import launch_known_app

    async def shell(command):
        if command.startswith("cmd package"):
            return "com.android.settings/.Settings"
        return "Error: Activity not started"

    result = await launch_known_app("com.android.settings", 0, shell)
    assert result["outcome"] == "failed"


def test_only_simple_voice_launch_uses_fast_worker(monkeypatch):
    from apps.admin_console.services.task_queue_service import TaskQueueService
    from artemis.runtime.adb_endpoint import AdbEndpoint, AdbTarget

    target = AdbTarget(AdbEndpoint.local(), "fake-device")
    command, _ = TaskQueueService._build_worker_invocation(
        {"ingress": "voice"}, "run", "id", "打开应用宝", "flash", target
    )
    assert command[2] == "artemis.runtime.fast_launch_worker"
    for item, goal in (({}, "打开应用宝"), ({"ingress": "voice"}, "打开设置并关闭蓝牙")):
        command, _ = TaskQueueService._build_worker_invocation(
            item, "run", "id", goal, "flash", target
        )
        assert command[2] == "artemis.main"


def test_expired_catalog_entry_is_not_used(tmp_path, monkeypatch):
    from artemis.runtime.app_catalog import AppCatalog
    import time

    catalog = AppCatalog(tmp_path, "device")
    catalog.remember("我的应用", "com.example.app")
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + catalog.TTL + 1)
    assert catalog.resolve("我的应用", {"com.example.app"}) is None


@pytest.mark.asyncio
async def test_fast_worker_persists_report_without_starting_agent(tmp_path, monkeypatch):
    import argparse
    from unittest.mock import AsyncMock, Mock
    from artemis.runtime import fast_launch_worker as worker
    from artemis.data_engine import engine as engine_module
    from artemis.runtime import device_lock

    catalog = Mock()
    catalog.resolve.return_value = "com.android.settings"
    monkeypatch.setattr(
        worker, "device_catalog", AsyncMock(return_value=(catalog, 0, {"com.android.settings"}))
    )
    monkeypatch.setattr(
        worker,
        "launch_known_app",
        AsyncMock(
            return_value={
                "outcome": "opened",
                "message": "ok",
                "timings": {},
            }
        ),
    )
    engine = Mock()
    engine.shutdown = AsyncMock()
    monkeypatch.setattr(engine_module, "DataEngine", Mock(return_value=engine))
    lock = Mock()
    monkeypatch.setattr(device_lock, "DeviceExecutionLock", Mock(return_value=lock))
    args = argparse.Namespace(goal="打开设置", device_serial="fake", session_id="sid")
    assert await worker.execute(args) is True
    engine.start_session.assert_called_once()
    engine.end_session.assert_called_once_with("completed")
    assert (
        engine.record_step.call_args.kwargs["action_taken"]["args"]["explanation"] == "已打开设置。"
    )
    lock.release.assert_called_once()


@pytest.mark.asyncio
async def test_real_engine_fast_session_persists_timings_and_terminal_status(tmp_path, monkeypatch):
    import argparse
    import sqlite3
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock
    from artemis.runtime import fast_launch_worker as worker
    from artemis.data_engine import engine as engine_module
    from artemis.runtime import device_lock

    catalog = Mock()
    catalog.resolve.return_value = "com.android.settings"
    monkeypatch.setattr(
        worker, "device_catalog", AsyncMock(return_value=(catalog, 0, {"com.android.settings"}))
    )
    monkeypatch.setattr(
        worker,
        "launch_known_app",
        AsyncMock(
            return_value={
                "outcome": "opened",
                "message": "ok",
                "timings": {"launch_command_s": 0.1},
            }
        ),
    )
    real_engine = engine_module.DataEngine(
        SimpleNamespace(
            execution_setup=SimpleNamespace(traces_path=tmp_path),
            device=None,
        )
    )
    monkeypatch.setattr(engine_module, "DataEngine", lambda _: real_engine)
    monkeypatch.setattr(device_lock, "DeviceExecutionLock", Mock(return_value=Mock()))
    assert await worker.execute(
        argparse.Namespace(
            goal="打开设置",
            device_serial="fake",
            session_id="12345678-1234-1234-1234-123456789abc",
        )
    )
    with sqlite3.connect(tmp_path / "data_engine.db") as connection:
        assert connection.execute("SELECT status FROM sessions").fetchone()[0] == "completed"
        assert connection.execute("SELECT count(*) FROM steps").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT count(*) FROM traces WHERE name='fast_app_launch'"
            ).fetchone()[0]
            == 1
        )
