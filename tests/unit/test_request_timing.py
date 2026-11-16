# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

import pytest
from langchain_core.messages import AIMessageChunk


@pytest.mark.asyncio
async def test_gateway_records_first_output_and_complete_tool_arguments(monkeypatch):
    from artemis.services import llm

    recorded = []
    monkeypatch.setattr(
        llm, "_record_llm_event", lambda name, payload, **kw: recorded.append((name, payload))
    )

    class Model:
        async def astream(self, *args, **kwargs):
            yield AIMessageChunk(content="")
            yield AIMessageChunk(content="启动应用")
            yield AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {
                        "name": "manage_app",
                        "args": '{"name":',
                        "id": "call1",
                        "index": 0,
                    }
                ],
            )
            yield AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {
                        "name": None,
                        "args": '"应用宝"}',
                        "id": None,
                        "index": 0,
                    }
                ],
            )

    await llm.RobustChatModelWrapper(Model()).complete([])
    timing = next(p for name, p in recorded if name == "llm_timing")
    assert (
        0 <= timing["first_chunk_s"] <= timing["first_output_s"] <= timing["first_tool_arguments_s"]
    )
    assert (
        timing["first_tool_arguments_s"] <= timing["tool_arguments_complete_s"] <= timing["total_s"]
    )
    assert timing["response_headers_s"] is None
    assert timing["server_prefill_s"] is None


@pytest.mark.asyncio
async def test_http_headers_and_payload_preparation_are_separate_from_first_token():
    import httpx
    from langchain_core.messages import HumanMessage
    from artemis.llm.request_timing import (
        active_timing,
        RequestTiming,
        TimedChatOpenAI,
        timing_http_client,
    )

    timer = RequestTiming()
    token = active_timing.set(timer)
    try:
        model = TimedChatOpenAI(model="qwen3-omni", api_key="local")
        model._get_request_payload([HumanMessage(content="hello")])
        async with timing_http_client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
        ) as client:
            await client.get("http://test/")
    finally:
        active_timing.reset(token)
    result = timer.result("success")
    assert result["request_prepare_s"] >= 0
    assert result["request_send_s"] <= result["response_headers_s"] <= result["total_s"]
    assert result["first_output_s"] is None
