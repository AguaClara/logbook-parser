"""Image loading and encoding helpers."""

import base64
import io
import os

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def image_data_url(path: str) -> str:
    """Read an image and return a base64 data URL. Nemotron accepts JPEG/PNG/WEBP;
    HEIC is converted on the fly if pillow-heif is installed."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".heic":
        try:
            from PIL import Image
            import pillow_heif
            pillow_heif.register_heif_opener()
            buf = io.BytesIO()
            Image.open(path).convert("RGB").save(buf, format="JPEG", quality=92)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            raise RuntimeError(
                f"{os.path.basename(path)} is HEIC and couldn't be converted "
                f"(pip install pillow pillow-heif, or convert to JPG first): {e}"
            )
    mime = MIME.get(ext)
    if not mime:
        raise RuntimeError(f"Unsupported image type '{ext}' for {os.path.basename(path)}")
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
