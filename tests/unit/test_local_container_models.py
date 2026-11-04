# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# https://www.apache.org/licenses/LICENSE-2.0

"""Local container model configuration must route memory calls to OVMS."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from artemis.config.agent import load_agent_config
from artemis.config.llm import parse_llm_config
from artemis.services import llm as llm_service


CONFIG = Path(__file__).resolve().parents[2] / "config" / "artemis.local.jsonc"


def test_local_config_resolves_agents_utilities_and_memory(monkeypatch):
    monkeypatch.setenv("ARTEMIS_ARTEMIS_JSONC", str(CONFIG))
    cfg = parse_llm_config()
    for role in ("operator", "planner", "explorer", "summarizer"):
        model = getattr(cfg, role)
        assert model.provider == "openai"
        assert model.model == "Qwen3.6-35B-A3B-int4-ov"
        assert model.fallback.provider == "openai"
    for role in ("object_detector", "hopper", "video_analyzer"):
        assert cfg.get_utils(role).provider == "openai"
    runtime = load_agent_config(CONFIG)
    assert runtime.flash.step_summarizer.model == cfg.summarizer.model
    assert runtime.memory.chunking.model == cfg.summarizer.model
    assert runtime.memory.runtime.max_concurrency == 1
    assert runtime.video_analyzer.enabled is False


def test_non_google_memory_model_uses_configured_provider(monkeypatch):
    monkeypatch.setenv("ARTEMIS_ARTEMIS_JSONC", str(CONFIG))
    cfg = parse_llm_config()
    create = Mock(return_value=object())
    google = Mock(side_effect=AssertionError("Local memory must not use Google"))
    monkeypatch.setattr(llm_service.ModelFactory, "create_model", create)
    monkeypatch.setattr(llm_service, "get_google_llm", google)
    model = llm_service.get_memory_llm(
        SimpleNamespace(llm_config=cfg),
        cfg.summarizer.model,
    )
    assert model is create.return_value
    endpoint = create.call_args.args[0]
    assert endpoint.provider.value == "openai"
    assert endpoint.model_name == cfg.summarizer.model
    assert endpoint.temperature == 0.0


def test_google_memory_keeps_explicit_model_override(monkeypatch):
    google = Mock(return_value=object())
    monkeypatch.setattr(llm_service, "get_google_llm", google)
    monkeypatch.setattr(
        llm_service,
        "_resolve_endpoint",
        Mock(
            return_value=llm_service.ModelEndpoint(
                provider=llm_service.ModelProvider.GOOGLE,
                model_name="gemini-3.8-flash",
            )
        ),
    )
    ctx = SimpleNamespace()
    model = llm_service.get_memory_llm(ctx, "gemini-2.5-flash-lite")
    assert model is google.return_value
    google.assert_called_once_with(model_name="gemini-2.5-flash-lite", temperature=0.0)


def test_local_visual_summary_and_chunk_use_memory_factory(monkeypatch):
    from artemis.agents.flash import summarizer
    from artemis.memory.chunking import StepCapsuleLens

    monkeypatch.setenv("ARTEMIS_ARTEMIS_JSONC", str(CONFIG))
    cfg = parse_llm_config()
    ctx = SimpleNamespace(llm_config=cfg, data_engine=None)
    local_model = Mock(model=cfg.summarizer.model)
    factory = Mock(return_value=local_model)
    monkeypatch.setattr(summarizer, "get_memory_llm", factory)
    monkeypatch.setattr(llm_service, "get_memory_llm", factory)
    monkeypatch.setattr(summarizer, "get_google_llm", Mock(side_effect=AssertionError("Google")))
    monkeypatch.setattr(llm_service, "get_google_llm", Mock(side_effect=AssertionError("Google")))
    visual = summarizer.VisualStepSummarizer(ctx, model_name=cfg.summarizer.model)
    capsule = StepCapsuleLens(cfg.summarizer.model, ctx=ctx)
    assert visual._llm is local_model
    assert capsule._get_llm() is local_model
    assert factory.call_count == 2
