# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

import base64
from copy import deepcopy
from io import BytesIO

from langchain_core.messages import HumanMessage
from PIL import Image


def image_url(size):
    output = BytesIO()
    Image.new("RGB", size, "white").save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()


def test_request_images_are_bounded_without_mutating_source_or_coordinates():
    from artemis.llm.bounded_openai import BoundedImageChatOpenAI

    content = [
        {"type": "text", "text": "screen=2560x1440; target=[1280,720]"},
        {"type": "image_url", "image_url": {"url": image_url((2560, 1440))}},
    ]
    original = deepcopy(content)
    model = BoundedImageChatOpenAI(model="qwen3-omni", api_key="local", image_max_edge=640)
    payload = model._get_request_payload([HumanMessage(content=content)])
    parts = payload["messages"][0]["content"]
    encoded = parts[1]["image_url"]["url"].split(",", 1)[1]
    assert Image.open(BytesIO(base64.b64decode(encoded))).size == (640, 360)
    assert parts[0]["text"] == original[0]["text"]
    assert content == original


def test_small_images_are_not_upscaled_and_tools_are_preserved():
    from artemis.llm.bounded_openai import BoundedImageChatOpenAI

    url = image_url((320, 180))
    model = BoundedImageChatOpenAI(model="qwen3-omni", api_key="local", image_max_edge=640)
    tools = [
        {"type": "function", "function": {"name": "inspect", "parameters": {"type": "object"}}}
    ]
    payload = model._get_request_payload(
        [HumanMessage(content=[{"type": "image_url", "image_url": {"url": url}}])],
        tools=tools,
    )
    assert payload["messages"][0]["content"][0]["image_url"]["url"] == url
    assert payload["tools"] == tools
