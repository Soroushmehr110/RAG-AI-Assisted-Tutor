# backend/app/utils.py
from PIL import Image
import os
import tempfile
from io import BytesIO

def is_password_valid(pw: str) -> bool:
    if len(pw) < 10:
        return False
    if not any(c.isdigit() for c in pw):
        return False
    if not any(not c.isalnum() for c in pw):
        return False
    return True

def reduce_image_to_max_bytes(input_path: str, max_bytes: int = 1_000_000) -> str:
    """
    If input file <= max_bytes returns original path.
    Otherwise creates a compressed/resized JPEG temp file <= max_bytes (best-effort).
    Returns path to file to use (temp or original).
    """
    size = os.path.getsize(input_path)
    if size <= max_bytes:
        return input_path

    img = Image.open(input_path).convert("RGB")
    orig_w, orig_h = img.size

    # initial scale estimate
    scale = (max_bytes / float(size)) ** 0.5
    scale = max(0.2, min(0.98, scale))
    new_w = max(200, int(orig_w * scale))
    new_h = max(200, int(orig_h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)

    quality = 90
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    data = buf.getvalue()

    # iteratively reduce quality
    while len(data) > max_bytes and quality >= 30:
        quality -= 10
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()

    # if still large, further downscale
    while len(data) > max_bytes and (new_w > 300 and new_h > 300):
        new_w = max(200, int(new_w * 0.9))
        new_h = max(200, int(new_h * 0.9))
        img = img.resize((new_w, new_h), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=max(40, quality), optimize=True)
        data = buf.getvalue()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    tmp.write(data)
    tmp.flush()
    tmp.close()
    return tmp.name
