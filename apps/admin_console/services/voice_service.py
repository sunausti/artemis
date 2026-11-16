# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# https://www.apache.org/licenses/LICENSE-2.0

"""Persistent voice settings, local audio proxying and per-task model snapshots."""

from contextlib import asynccontextmanager
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import wave

import httpx

from apps.admin_console.schemas.voice_schema import VoiceSettings
from apps.admin_console.services import omni_voice
from artemis.config.paths import get_app_dir, get_config_path
from third_party.mobile_use.utils.file import load_jsonc


MAX_AUDIO_BYTES = 12 * 1024 * 1024


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".voice-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class VoiceService:
    def __init__(self, app_dir: Path | None = None, *, client: httpx.AsyncClient | None = None):
        self._app_dir = app_dir
        self._client = client

    @property
    def app_dir(self) -> Path:
        return self._app_dir if self._app_dir is not None else get_app_dir()

    def load(self) -> VoiceSettings:
        path = self.app_dir / "voice-settings.json"
        if path.exists():
            return VoiceSettings.model_validate_json(path.read_text(encoding="utf-8"))
        return VoiceSettings(
            llm_base_url=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8080/v3"),
            device_serial=os.environ.get("ADB_DEVICE_SERIAL", "127.0.0.1:5555"),
        )

    def save(self, settings: VoiceSettings) -> VoiceSettings:
        atomic_write(self.app_dir / "voice-settings.json", settings.model_dump_json(indent=2))
        return settings

    @asynccontextmanager
    async def client(self):
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(120, connect=5), trust_env=False
            ) as client:
                yield client

    @staticmethod
    async def read_response(response: httpx.Response, limit: int) -> bytes:
        if response.status_code >= 400:
            raise ValueError(f"本地语音服务返回 HTTP {response.status_code}")
        content = bytearray()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > limit:
                raise ValueError("语音服务响应超过大小限制")
        return bytes(content)

    async def transcribe(self, audio: bytes, filename: str) -> str:
        if not audio or len(audio) > MAX_AUDIO_BYTES:
            raise ValueError("音频为空或超过 12 MiB 限制")
        settings = self.load()
        if settings.voice_mode == "omni":
            message = await self.omni_chat(
                settings,
                omni_voice.transcription_request(settings.omni_model, audio),
                65536,
            )
            return omni_voice.transcription_text(message)
        data = {"model": settings.asr_model, "response_format": "json"}
        if settings.asr_language != "auto":
            data["language"] = settings.asr_language
        try:
            async with self.client() as client:
                async with client.stream(
                    "POST",
                    settings.asr_base_url + "/audio/transcriptions",
                    data=data,
                    files={"file": (filename, audio, "audio/wav")},
                ) as response:
                    payload = json.loads(await self.read_response(response, 65536))
            text = payload.get("text") if isinstance(payload, dict) else None
            if not isinstance(text, str) or not text.strip():
                raise ValueError("没有识别到语音，请重试")
            return text.strip()
        except httpx.HTTPError as exc:
            raise ValueError("无法连接本地 ASR 服务，请检查语音设置") from exc

    async def synthesize(self, text: str) -> bytes:
        settings = self.load()
        if not text.strip():
            raise ValueError("播报文字不能为空")
        if settings.voice_mode == "omni":
            message = await self.omni_chat(
                settings,
                omni_voice.speech_request(settings.omni_model, text),
                MAX_AUDIO_BYTES * 4 // 3 + 65536,
            )
            return omni_voice.speech_wave(message, settings.omni_sample_rate, MAX_AUDIO_BYTES)
        try:
            async with self.client() as client:
                async with client.stream(
                    "POST",
                    settings.tts_base_url + "/audio/speech",
                    json={
                        "model": settings.tts_model,
                        "input": text,
                        "voice": settings.tts_voice,
                        "response_format": "pcm",
                        "sample_rate": settings.tts_sample_rate,
                        "stream": False,
                    },
                ) as response:
                    pcm = await self.read_response(response, MAX_AUDIO_BYTES)
        except httpx.HTTPError as exc:
            raise ValueError("无法连接本地 TTS 服务，请检查语音设置") from exc
        if not pcm or len(pcm) % 2:
            raise ValueError("TTS 没有返回有效的 PCM16 音频")
        output = BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(settings.tts_sample_rate)
            wav.writeframes(pcm)
        return output.getvalue()

    async def omni_chat(self, settings: VoiceSettings, body: dict, limit: int) -> dict:
        try:
            async with self.client() as client:
                async with client.stream(
                    "POST",
                    settings.omni_base_url + "/chat/completions",
                    json=body,
                ) as response:
                    content = await self.read_response(response, limit)
            return omni_voice.response_message(json.loads(content))
        except httpx.HTTPError as exc:
            raise ValueError("无法连接本地 Omni 服务，请检查语音设置") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Omni 服务没有返回有效 JSON") from exc

    def model_runtime(self, settings: VoiceSettings | None = None) -> dict[str, str]:
        settings = settings or self.load()
        is_omni = settings.voice_mode == "omni"
        model_name = settings.omni_model if is_omni else settings.llm_model
        base_url = settings.omni_base_url if is_omni else settings.llm_base_url
        with get_config_path("artemis.jsonc").open(encoding="utf-8") as file:
            config = load_jsonc(file)
        model = {
            "provider": "openai",
            "model": model_name,
            "temperature": 0.0,
            "enable_grounding": False,
            "fallback": {"provider": "openai", "model": model_name},
        }
        config["default"] = model
        config["nodes"] = {
            name: dict(model)
            for name in (
                "planner",
                "operator",
                "explorer",
                "summarizer",
                "operator_summarizer",
                "log_reader_sub_agent",
                "log_analyzer",
                "diagnoser",
                "checker",
                "planner_avatar",
                "history_analyzer_expert",
                "diagnoser_expert",
                "history_analyzer",
                "output_analyzer",
                "outputter",
                "hopper",
                "video_analyzer",
                "object_detector",
                "validator_pixel_safety_net",
                "planner_validation",
            )
        }
        agent = config.setdefault("agent", {})
        flash = agent.setdefault("flash", {})
        flash["max_turns"] = 30
        flash["explorer_mode"] = "pro"
        flash.setdefault("step_summarizer", {})["model"] = model_name
        if is_omni:
            flash["step_summarizer"]["enabled"] = False
        memory = agent.setdefault("memory", {})
        memory.setdefault("chunking", {})["model"] = model_name
        memory.setdefault("runtime", {})["max_concurrency"] = 1
        agent["video_analyzer"] = {"enabled": False, "enable_ledger": False}
        agent.setdefault("pro", {})["video_analyzer"] = {"enabled": False, "enable_ledger": False}
        agent.setdefault("explorer", {})["caching"] = False
        agent.setdefault("denylisted_tools", {})["explorer"] = ["get_ocr_list"]
        content = json.dumps(config, ensure_ascii=False, indent=2)
        digest = hashlib.sha256(content.encode()).hexdigest()
        path = self.app_dir / "voice-models" / f"{digest}.jsonc"
        if not path.exists():
            atomic_write(path, content)
        return {
            "ARTEMIS_ARTEMIS_JSONC": str(path),
            "OPENAI_BASE_URL": base_url,
            "OPENAI_API_KEY": "local-ovms",
            "ARTEMIS_OPENAI_TEXT_ONLY": "true" if is_omni else "false",
            "ARTEMIS_MODEL_IMAGE_MAX_EDGE": "640" if is_omni else "0",
        }


voice_service = VoiceService()
