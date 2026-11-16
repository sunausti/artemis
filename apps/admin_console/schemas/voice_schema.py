# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# https://www.apache.org/licenses/LICENSE-2.0

"""Configuration for the local voice bridge."""

from urllib.parse import urlsplit
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VoiceSettings(BaseModel):
    voice_mode: Literal["split", "omni"] = "split"
    omni_base_url: str = "http://127.0.0.1:8100/v3"
    omni_model: str = "qwen3-omni"
    omni_sample_rate: int = Field(default=24000, ge=8000, le=48000)
    asr_base_url: str = "http://127.0.0.1:8090/v1"
    asr_model: str = "sensevoice"
    asr_language: str = "auto"
    llm_base_url: str = "http://127.0.0.1:8080/v3"
    llm_model: str = "Qwen3.6-35B-A3B-int4-ov"
    tts_base_url: str = "http://127.0.0.1:8094/v1"
    tts_model: str = "qwen3-tts"
    tts_voice: str = "vivian"
    tts_sample_rate: int = Field(default=24000, ge=8000, le=48000)
    device_serial: str = "127.0.0.1:5555"

    @field_validator("asr_base_url", "llm_base_url", "tts_base_url", "omni_base_url")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("请输入 HTTP/HTTPS 服务地址，不包含账号、查询参数或片段")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("端口必须在 1 到 65535 之间")
        return value

    @field_validator(
        "asr_model",
        "asr_language",
        "llm_model",
        "tts_model",
        "tts_voice",
        "device_serial",
        "omni_model",
    )
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 256:
            raise ValueError("此字段不能为空，且最多 256 个字符")
        return value


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
