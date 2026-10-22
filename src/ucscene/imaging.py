"""Local PNG/JPEG/WebP inspection. Pillow is an optional 'ui' extra."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .core import SceneError

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000


def _pillow():
    try:
        from PIL import Image, ImageOps, ImageDraw, ImageChops
    except ImportError as exc:
        raise SceneError("Image operations require Pillow: python -m pip install -e '.[ui]'") from exc
    return Image, ImageOps, ImageDraw, ImageChops


def inspect_image(path: str | Path) -> dict[str, Any]:
    image, _, _, _ = _pillow()
    file_path = Path(path)
    raw = file_path.read_bytes()
    if not raw or len(raw) > MAX_FILE_BYTES:
        raise SceneError('Image is empty or exceeds 20 MiB')
    try:
        with image.open(file_path) as opened:
            if opened.format not in {'PNG', 'JPEG', 'WEBP'}:
                raise SceneError('Only PNG/JPEG/WebP inputs are supported')
            width, height = opened.size
            if width < 16 or height < 16 or width * height > MAX_IMAGE_PIXELS:
                raise SceneError('Image dimensions outside supported range')
            opened.verify()
    except (OSError, ValueError, SyntaxError) as exc:
        raise SceneError('Invalid or unreadable image file') from exc
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'width': width, 'height': height, 'bytes': len(raw)}
