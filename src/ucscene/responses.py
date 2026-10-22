"""Opt-in OpenAI Responses API client for extraction and visual review.

Network is called only by commands explicitly selecting AI features.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any

from .core import SceneError
from .provider import ProviderError

_MAX_IMAGE_BYTES = 20 * 1024 * 1024


def image_data_url(path: str | Path) -> str:
    image = Path(path).read_bytes()
    if not image or len(image) > _MAX_IMAGE_BYTES:
        raise SceneError("Image is empty or exceeds the 20 MiB limit")
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image/png"
    elif image.startswith(b"\xff\xd8\xff"):
        media_type = "image/jpeg"
    elif image.startswith(b"RIFF") and image[8:12] == b"WEBP":
        media_type = "image/webp"
    else:
        raise SceneError("Only PNG, JPEG and WebP images are supported")
    return f"data:{media_type};base64,{base64.b64encode(image).decode('ascii')}"


def structured_response(
    instructions: str, text: str, *, schema: dict[str, Any],
    schema_name: str, model: str = "gpt-4.1-mini", images: list[str | Path] | None = None,
    api_key: str | None = None, endpoint: str = "https://api.openai.com/v1/responses",
) -> dict[str, Any]:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ProviderError("OPENAI_API_KEY is required for AI extraction or visual review")
    if not endpoint.startswith("https://"):
        raise ProviderError("Responses API endpoint must use HTTPS")
    content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
    for image in images or []:
        content.append({"type": "input_image", "image_url": image_data_url(image), "detail": "high"})
    request_body = {
        "model": model,
        "instructions": instructions,
        "input": [{"role": "user", "content": content}],
        "text": {"format": {"type": "json_schema", "name": schema_name, "strict": True, "schema": schema}},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"Responses API rejected request (HTTP {exc.code})") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError(f"Responses API transport error: {type(exc).__name__}") from exc
    if body.get("status") not in (None, "completed"):
        raise ProviderError("Responses API did not complete normally")
    output_texts = [
        part.get("text")
        for message in body.get("output", []) if message.get("type") == "message"
        for part in message.get("content", []) if part.get("type") == "output_text"
    ]
    if not output_texts and isinstance(body.get("output_text"), str):
        output_texts.append(body["output_text"])
    if len(output_texts) != 1:
        raise ProviderError("Responses API did not provide one structured output")
    try:
        result = json.loads(output_texts[0])
    except (ValueError, TypeError) as exc:
        raise ProviderError("Structured output was not valid JSON") from exc
    if not isinstance(result, dict):
        raise ProviderError("Structured output must be an object")
    return result
