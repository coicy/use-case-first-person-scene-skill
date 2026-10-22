"""Optional online image generation provider. No API key is persisted."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any

class ProviderError(RuntimeError):
    pass

def generate_openai_image(prompt: str, output: str | Path, *, model: str = "gpt-image-1.5", size: str = "1536x1024", quality: str = "medium", api_key: str | None = None, endpoint: str = "https://api.openai.com/v1/images/generations") -> dict[str, Any]:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ProviderError("OPENAI_API_KEY is not set. Run 'plan' without a key, or set a key for 'generate'.")
    if not endpoint.startswith("https://"):
        raise ProviderError("Image generation endpoint must use HTTPS")
    if quality not in {"low", "medium", "high", "auto"}:
        raise ProviderError("Unsupported quality")
    payload = json.dumps({"model": model, "prompt": prompt, "size": size, "quality": quality}).encode("utf-8")
    request = urllib.request.Request(endpoint, data=payload, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.load(response)
    except urllib.error.HTTPError as e:
        # Do not echo raw server bodies, which can include request-specific information.
        raise ProviderError(f"Image API rejected request (HTTP {e.code})") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ProviderError(f"Image API transport error: {type(e).__name__}") from e
    try:
        encoded = result["data"][0]["b64_json"]
        image = base64.b64decode(encoded, validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ProviderError("Response does not contain a usable b64_json image") from e
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image)
    return {"path": str(destination), "bytes": len(image), "model": model, "size": size, "quality": quality, "verified_image_content": False}
