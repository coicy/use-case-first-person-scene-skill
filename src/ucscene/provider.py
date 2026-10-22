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


def edit_openai_image(
    prompt: str, reference_image: str | Path, output: str | Path, *,
    model: str = "gpt-image-1.5", size: str = "1536x1024", quality: str = "medium",
    api_key: str | None = None, endpoint: str = "https://api.openai.com/v1/images/edits",
) -> dict[str, Any]:
    """Edit one scene from a supplied visual anchor using image multipart upload.

    Reference mode is a best-effort continuity aid, not a pixel-perfect guarantee.
    """
    import uuid
    from .responses import image_data_url

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ProviderError("OPENAI_API_KEY is not set for image editing")
    if not endpoint.startswith("https://"):
        raise ProviderError("Image editing endpoint must use HTTPS")
    if quality not in {"low", "medium", "high", "auto"}:
        raise ProviderError("Unsupported quality")
    ref = Path(reference_image)
    # Validate signature and enforce the same size limits as vision input.
    uri = image_data_url(ref)
    mime = uri[5:].split(";", 1)[0]
    img = ref.read_bytes()
    boundary = "ucscene-" + uuid.uuid4().hex
    pieces: list[bytes] = []
    for name, value in (("model", model), ("prompt", prompt), ("size", size), ("quality", quality)):
        pieces.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
    filename = {'image/png': 'reference.png', 'image/jpeg': 'reference.jpg', 'image/webp': 'reference.webp'}[mime]
    pieces.append((
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f'Content-Type: {mime}\r\n\r\n'
    ).encode("utf-8") + img + b"\r\n")
    pieces.append(f"--{boundary}--\r\n".encode("ascii"))
    req = urllib.request.Request(endpoint, data=b"".join(pieces), headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "multipart/form-data; boundary=" + boundary,
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"Image edits API rejected request (HTTP {exc.code})") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError(f"Image edits API transport error: {type(exc).__name__}") from exc
    try:
        encoded = result["data"][0]["b64_json"]
        image = base64.b64decode(encoded, validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("Image edits response missing usable b64_json") from exc
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image)
    return {
        "path": str(destination), "bytes": len(image), "model": model,
        "size": size, "quality": quality, "reference_image": str(ref),
        "continuity_verified": False, "verified_image_content": False,
    }
