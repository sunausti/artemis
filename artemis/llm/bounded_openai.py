# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0.

"""Bound inline image resolution at the provider boundary, not the device layer."""

import base64
import time
from copy import deepcopy
from io import BytesIO

from artemis.llm.request_timing import TimedChatOpenAI
from PIL import Image
from pydantic import Field


class BoundedImageChatOpenAI(TimedChatOpenAI):
    image_max_edge: int = Field(default=640, ge=64, le=4096, exclude=True)

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        started = time.perf_counter()
        payload = deepcopy(super()._get_request_payload(input_, stop=stop, **kwargs))
        for message in payload.get("messages", []):
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "image_url":
                    continue
                image = block.get("image_url")
                if not isinstance(image, dict):
                    continue
                url = image.get("url", "")
                if not isinstance(url, str) or not url.startswith("data:image/"):
                    continue
                header, encoded = url.split(",", 1)
                if ";base64" not in header:
                    raise ValueError("Bounded image requests require base64 inline images")
                with Image.open(BytesIO(base64.b64decode(encoded, validate=True))) as source:
                    if max(source.size) <= self.image_max_edge:
                        continue
                    resized = source.convert("RGB")
                    resized.thumbnail(
                        (self.image_max_edge, self.image_max_edge), Image.Resampling.LANCZOS
                    )
                    output = BytesIO()
                    resized.save(output, format="JPEG", quality=85)
                image["url"] = "data:image/jpeg;base64," + base64.b64encode(
                    output.getvalue()
                ).decode("ascii")
        from artemis.llm.request_timing import active_timing

        timer = active_timing.get()
        if timer is not None:
            timer.values["request_prepare_s"] = time.perf_counter() - started
        return payload
