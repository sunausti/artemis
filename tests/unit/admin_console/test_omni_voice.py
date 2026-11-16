# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

import base64
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import Mock
import wave

import httpx
import pytest

from apps.admin_console.schemas.voice_schema import VoiceSettings
from apps.admin_console.services.voice_service import VoiceService


def wav_bytes(rate=24000):
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\0\0" * 240)
    return output.getvalue()


def test_legacy_settings_keep_split_mode_and_omni_endpoints_are_validated():
    assert VoiceSettings().voice_mode == "split"
    with pytest.raises(ValueError):
        VoiceSettings(voice_mode="omni", omni_base_url="file:///model")
    assert (
        VoiceSettings(omni_base_url="http://localhost:18100/v3/").omni_base_url
        == "http://localhost:18100/v3"
    )


@pytest.mark.asyncio
async def test_omni_transcribes_audio_through_chat_not_split_asr(tmp_path):
    audio = wav_bytes()

    def upstream(request):
        assert str(request.url) == "http://localhost:18100/v3/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3-omni"
        assert payload["modalities"] == ["text"]
        assert payload["stream"] is False
        content = payload["messages"][-1]["content"]
        part = next(p for p in content if p["type"] == "input_audio")
        assert part["input_audio"]["format"] == "wav"
        assert base64.b64decode(part["input_audio"]["data"]) == audio
        return httpx.Response(200, json={"choices": [{"message": {"content": "打开设置"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
        service = VoiceService(tmp_path, client=client)
        service.save(VoiceSettings(voice_mode="omni", omni_base_url="http://localhost:18100/v3"))
        assert await service.transcribe(audio, "voice.wav") == "打开设置"


@pytest.mark.asyncio
@pytest.mark.parametrize("wav_output", [True, False])
async def test_omni_speech_decodes_wave_or_pcm_without_double_header(tmp_path, wav_output):
    raw = wav_bytes(16000) if wav_output else b"\0\0" * 240

    def upstream(request):
        payload = json.loads(request.content)
        assert request.url.path == "/v3/chat/completions"
        assert payload["modalities"] == ["text", "audio"]
        assert payload["stream"] is False
        assert payload["messages"][-1]["content"] == "任务已取消。"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "任务已取消。",
                            "audio": {"data": base64.b64encode(raw).decode()},
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
        service = VoiceService(tmp_path, client=client)
        service.save(VoiceSettings(voice_mode="omni", omni_sample_rate=24000))
        result = await service.synthesize("任务已取消。")
    with wave.open(BytesIO(result)) as wav:
        assert wav.getframerate() == (16000 if wav_output else 24000)
        assert wav.getnframes() == 240


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        {},
        {"audio": {"data": "invalid!"}},
        {"audio": {"data": base64.b64encode(b"odd").decode()}},
    ],
)
async def test_omni_missing_or_invalid_audio_fails_explicitly(tmp_path, message):
    response = httpx.Response(200, json={"choices": [{"message": message}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
        service = VoiceService(tmp_path, client=client)
        service.save(VoiceSettings(voice_mode="omni"))
        with pytest.raises(ValueError):
            await service.synthesize("完成")


def test_omni_runtime_routes_every_model_and_forces_text_only(tmp_path):
    service = VoiceService(tmp_path)
    runtime = service.model_runtime(
        VoiceSettings(
            voice_mode="omni",
            omni_base_url="http://localhost:18100/v3",
            omni_model="my-omni",
        )
    )
    assert runtime["OPENAI_BASE_URL"] == "http://localhost:18100/v3"
    assert runtime["ARTEMIS_OPENAI_TEXT_ONLY"] == "true"
    assert runtime["ARTEMIS_MODEL_IMAGE_MAX_EDGE"] == "640"
    config = json.loads(Path(runtime["ARTEMIS_ARTEMIS_JSONC"]).read_text())
    assert config["default"]["model"] == "my-omni"
    assert config["agent"]["memory"]["chunking"]["model"] == "my-omni"
    assert config["agent"]["flash"]["step_summarizer"]["enabled"] is False
    assert all(v["model"] == "my-omni" for v in config["nodes"].values())
    split = service.model_runtime(VoiceSettings())
    assert split["ARTEMIS_OPENAI_TEXT_ONLY"] == "false"


def test_worker_omni_flag_reaches_openai_request(monkeypatch):
    from artemis.llm.router import ModelEndpoint, ModelFactory, ModelProvider
    from artemis.llm import request_timing

    create = Mock()
    monkeypatch.setattr(request_timing, "TimedChatOpenAI", create)
    monkeypatch.setenv("ARTEMIS_OPENAI_TEXT_ONLY", "true")
    ModelFactory.create_model(ModelEndpoint(provider=ModelProvider.OPENAI, model_name="qwen3-omni"))
    assert create.call_args.kwargs["model_kwargs"]["modalities"] == ["text"]


def test_omni_worker_flag_is_task_scoped(tmp_path, monkeypatch):
    from apps.admin_console.services.task_queue_service import TaskQueueService
    from artemis.runtime.adb_endpoint import AdbEndpoint, AdbTarget

    monkeypatch.delenv("ARTEMIS_OPENAI_TEXT_ONLY", raising=False)
    runtime = VoiceService(tmp_path).model_runtime(VoiceSettings(voice_mode="omni"))
    target = AdbTarget(AdbEndpoint.local(), "fake-device")
    _, env = TaskQueueService._build_worker_invocation(
        {"model_runtime": runtime}, "run", "id", "goal", "flash", target
    )
    assert env["ARTEMIS_OPENAI_TEXT_ONLY"] == "true"
    assert env["ARTEMIS_MODEL_IMAGE_MAX_EDGE"] == "640"
    _, regular = TaskQueueService._build_worker_invocation({}, "run", "id", "goal", "flash", target)
    assert "ARTEMIS_OPENAI_TEXT_ONLY" not in regular


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"choices": []},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "<think>思考</think>打开设置"}}]},
        {"choices": [{"message": {"content": "打开设置", "tool_calls": [{"id": "x"}]}}]},
    ],
)
async def test_bad_omni_transcription_is_not_submitted(tmp_path, body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    ) as client:
        service = VoiceService(tmp_path, client=client)
        service.save(VoiceSettings(voice_mode="omni"))
        with pytest.raises(ValueError):
            await service.transcribe(wav_bytes(), "voice.wav")


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [httpx.Response(503), httpx.Response(200, text="not json")])
async def test_omni_upstream_failure_is_explicit(tmp_path, response):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
        service = VoiceService(tmp_path, client=client)
        service.save(VoiceSettings(voice_mode="omni"))
        with pytest.raises(ValueError):
            await service.transcribe(wav_bytes(), "voice.wav")
