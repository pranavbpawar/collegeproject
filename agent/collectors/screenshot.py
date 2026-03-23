"""
NEF Agent — Screenshot Collector
Takes a screenshot, compresses to JPEG, returns as base64.
Uses Pillow — cross-platform.
"""

import base64
import io
from datetime import datetime

try:
    from PIL import ImageGrab, Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def collect(quality: int = 60) -> dict:
    """
    Capture the screen and return compressed JPEG as base64.
    quality: JPEG compression 1-95 (lower = smaller file)
    """
    if not _PIL_AVAILABLE:
        return {
            "type": "screenshot",
            "error": "Pillow not installed",
            "image_b64": None,
            "collected_at": datetime.utcnow().isoformat(),
        }

    try:
        # ImageGrab works on Windows; on Linux requires scrot or X11
        img = ImageGrab.grab()

        # Downscale to max 1280px wide to reduce payload
        max_width = 1280
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize(
                (max_width, int(img.height * ratio)),
                Image.LANCZOS
            )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()

        return {
            "type": "screenshot",
            "width": img.width,
            "height": img.height,
            "size_bytes": len(buf.getvalue()),
            "image_b64": b64,
            "collected_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "type": "screenshot",
            "error": str(e),
            "image_b64": None,
            "collected_at": datetime.utcnow().isoformat(),
        }
