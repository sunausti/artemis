# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# https://www.apache.org/licenses/LICENSE-2.0

import json
from pathlib import Path
import wave
from io import BytesIO

import httpx
import pytest
from pydantic import ValidationError


def modules():
    from apps.admin_console.schemas.voice_schema import VoiceSettings
    from apps.admin_console.services.voice_service import VoiceService

    return VoiceSettings, VoiceService


def test_settings_persist_and_bad_urls_are_rejected(tmp_path):
    Settings, Service = modules()
    service = Service(tmp_path)
    settings = Settings(llm_base_url="http://127.0.0.1:18080/v3/")
    service.save(settings)
    assert Service(tmp_path).load().llm_base_url == "http://127.0.0.1:18080/v3"
    for url in (
        "file:///tmp/audio",
        "http://user:password@localhost:8090/v1",
        "http://localhost:99999/v1",
    ):
        with pytest.raises(ValidationError):
            Settings(asr_base_url=url)


@pytest.mark.asyncio
async def test_asr_upload_and_tts_pcm_wave(tmp_path):
    Settings, Service = modules()
    requests = []

    def upstream(request):
        requests.append(request)
        if request.url.path.endswith("transcriptions"):
            assert b"RIFF" in request.content
            assert b"sensevoice" in request.content
            return httpx.Response(200, json={"text": " 打开蓝牙设置 "})
        body = json.loads(request.content)
        assert body["voice"] == "vivian"
        assert body["response_format"] == "pcm"
        return httpx.Response(200, content=b"\x00\x00" * 240)

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
        service = Service(tmp_path, client=client)
        service.save(
            Settings(
                asr_base_url="http://localhost:18090/v1", tts_base_url="http://localhost:18094/v1"
            )
        )
        assert await service.transcribe(b"RIFFtest", "audio.wav") == "打开蓝牙设置"
        audio = await service.synthesize("正在处理")
        with wave.open(BytesIO(audio)) as wav:
            assert wav.getframerate() == 24000
            assert wav.getnchannels() == 1
            assert wav.getnframes() == 240
    assert requests[0].url.port == 18090
    assert requests[1].url.port == 18094


@pytest.mark.asyncio
async def test_audio_errors_are_not_successful_recognition(tmp_path):
    _, Service = modules()
    for response in (
        httpx.Response(503, text="unavailable"),
        httpx.Response(200, json={"text": "  "}),
    ):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
            with pytest.raises(ValueError):
                await Service(tmp_path, client=client).transcribe(b"RIFFtest", "audio.wav")


def test_model_snapshot_is_immutable_and_applied_only_to_voice_worker(tmp_path, monkeypatch):
    Settings, Service = modules()
    from apps.admin_console.services.task_queue_service import TaskQueueService
    from artemis.runtime.adb_endpoint import AdbEndpoint, AdbTarget

    service = Service(tmp_path)
    service.save(Settings(llm_base_url="http://localhost:18080/v3", llm_model="local-qwen"))
    runtime = service.model_runtime()
    config = json.loads(Path(runtime["ARTEMIS_ARTEMIS_JSONC"]).read_text())
    assert config["default"]["model"] == "local-qwen"
    assert config["agent"]["memory"]["chunking"]["model"] == "local-qwen"
    assert all(value["provider"] == "openai" for value in config["nodes"].values())
    service.save(Settings(llm_base_url="http://localhost:28080/v3", llm_model="next-qwen"))
    assert runtime["OPENAI_BASE_URL"] == "http://localhost:18080/v3"
    assert json.loads(Path(runtime["ARTEMIS_ARTEMIS_JSONC"]).read_text()) == config
    monkeypatch.setenv("OPENAI_BASE_URL", "http://original:8080/v3")
    target = AdbTarget(AdbEndpoint.local(), "fake-device")
    _, voice_env = TaskQueueService._build_worker_invocation(
        {"model_runtime": runtime},
        "run",
        "sid",
        "goal",
        "flash",
        target,
    )
    _, regular_env = TaskQueueService._build_worker_invocation(
        {},
        "run",
        "sid",
        "goal",
        "flash",
        target,
    )
    assert voice_env["OPENAI_BASE_URL"] == "http://localhost:18080/v3"
    assert regular_env["OPENAI_BASE_URL"] == "http://original:8080/v3"


def test_voice_task_result_uses_recorded_report_not_model_guess(monkeypatch):
    from apps.admin_console.routers import voice

    monkeypatch.setattr(voice.session_repo, "get_session_by_id", lambda _: {"status": "completed"})
    monkeypatch.setattr(voice.trace_store, "read_status", lambda _: None)
    monkeypatch.setattr(
        voice,
        "read_final_report",
        lambda _: {"status": "completed", "explanation": "蓝牙开关已开启"},
    )
    assert voice.task_details("test") == {
        "session_id": "test",
        "status": "completed",
        "message": "蓝牙开关已开启",
    }


def test_final_report_is_extracted_from_recorded_steps(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import contextmanager
    from apps.admin_console.routers import voice

    connection = sqlite3.connect(tmp_path / "steps.db")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE steps(session_id TEXT, step_number INTEGER, action_taken TEXT)"
    )
    report = {"status": "failed", "explanation": "找不到蓝牙开关"}
    connection.execute(
        "INSERT INTO steps VALUES (?, ?, ?)",
        ("sid", 2, json.dumps({"action": "report_task_status", "args": report})),
    )

    @contextmanager
    def database():
        yield connection

    monkeypatch.setattr(voice, "db_session", database)
    try:
        assert voice.read_final_report("sid") == report
    finally:
        connection.close()


@pytest.mark.asyncio
async def test_voice_submission_passes_model_snapshot_to_queue(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from apps.admin_console.routers import tasks
    from apps.admin_console.services import voice_service as service_module
    from apps.admin_console.schemas.task_schema import RunRequest

    Settings, Service = modules()
    service = Service(tmp_path)
    service.save(Settings(llm_base_url="http://localhost:18080/v3"))
    monkeypatch.setattr(service_module, "voice_service", service)
    monkeypatch.setattr(
        tasks.readiness_engine, "run_device_submission_probe", AsyncMock(return_value=None)
    )
    enqueue = AsyncMock(return_value={"tasks": [{"session_id": "voice-id"}]})
    monkeypatch.setattr(tasks, "task_queue_service", SimpleNamespace(enqueue_tasks=enqueue))
    await tasks.run_task(RunRequest(goal="打开设置", use_voice_settings=True, ingress="voice"))
    assert (
        enqueue.call_args.kwargs["model_runtime"]["OPENAI_BASE_URL"] == "http://localhost:18080/v3"
    )
    await tasks.run_task(RunRequest(goal="普通任务"))
    assert enqueue.call_args.kwargs["model_runtime"] is None


@pytest.mark.asyncio
async def test_voice_routes_serve_assets_and_settings_without_lifespan(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from apps.admin_console.routers import voice

    Settings, Service = modules()
    monkeypatch.setattr(voice, "voice_service", Service(tmp_path))
    app = FastAPI()
    app.include_router(voice.router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        assert (await client.get("/voice")).status_code == 200
        assert (await client.get("/voice/voice.js")).status_code == 200
        assert (await client.get("/voice/unknown.txt")).status_code == 404
        result = await client.put(
            "/api/voice/settings",
            json=Settings(llm_base_url="http://localhost:18080/v3").model_dump(),
        )
        assert result.status_code == 200
        assert (await client.get("/api/voice/settings")).json()[
            "llm_base_url"
        ] == "http://localhost:18080/v3"
