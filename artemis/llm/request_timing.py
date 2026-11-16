# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

"""Per-attempt client timing. Never infer server stages from client timestamps."""

from contextvars import ContextVar
import json
import time

import httpx
from langchain_openai import ChatOpenAI

active_timing: ContextVar = ContextVar("llm_client_timing", default=None)


class RequestTiming:
    def __init__(self):
        self.started = time.perf_counter()
        self.values = {}
        self.tools = {}

    def mark(self, name):
        self.values.setdefault(name, time.perf_counter() - self.started)

    def chunk(self, chunk):
        self.mark("first_chunk_s")
        if getattr(chunk, "content", None) or getattr(chunk, "tool_call_chunks", None):
            self.mark("first_output_s")
        for tool in getattr(chunk, "tool_call_chunks", []) or []:
            args = tool.get("args")
            if not args:
                continue
            self.mark("first_tool_arguments_s")
            index = tool.get("index", 0)
            self.tools[index] = self.tools.get(index, "") + args

    def finish_tools(self):
        if self.tools:
            try:
                if all(isinstance(json.loads(args), dict) for args in self.tools.values()):
                    # Completion is measured when the stream closes, not when
                    # a possibly partial tool JSON first happens to parse.
                    self.mark("tool_arguments_complete_s")
            except ValueError:
                pass

    def result(self, status):
        return {
            **{
                name: None
                for name in (
                    "request_prepare_s",
                    "request_send_s",
                    "response_headers_s",
                    "first_chunk_s",
                    "first_output_s",
                    "first_tool_arguments_s",
                    "tool_arguments_complete_s",
                    "server_vision_s",
                    "server_prefill_s",
                    "server_decode_s",
                )
            },
            **self.values,
            "total_s": time.perf_counter() - self.started,
            "status": status,
            "clock": "client_monotonic",
        }


class TimedChatOpenAI(ChatOpenAI):
    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        started = time.perf_counter()
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        timer = active_timing.get()
        if timer is not None:
            timer.values["request_prepare_s"] = time.perf_counter() - started
        return payload


async def on_request(request):
    timer = active_timing.get()
    if timer is not None:
        timer.mark("request_send_s")


async def on_response(response):
    timer = active_timing.get()
    if timer is not None:
        timer.mark("response_headers_s")


def timing_http_client(**kwargs):
    return httpx.AsyncClient(
        event_hooks={"request": [on_request], "response": [on_response]}, **kwargs
    )
