# 证件文件校验与图片水印。版本 v1.0 · 2026-10-13
"""扩展名、MIME、文件头三者不一致即 5005。PDF 不改字节。"""

from __future__ import annotations

import io

from app.core.errors import BizError
from app.core.file_scenes import CERT_SCENE

_RULES = {
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG"),
    ".pdf": ("application/pdf", b"%PDF"),
}


def validate_cert_file(filename: str, content_type: str, content: bytes) -> str:
    """落盘前校验。返回规范化扩展名。"""
    name = (filename or "").lower()
    ext = ""
    for candidate in _RULES:
        if name.endswith(candidate):
            ext = candidate
            break
    if not ext:
        raise BizError(5005, msg="仅支持 jpg、jpeg、png、pdf 格式")
    expect_mime, magic = _RULES[ext]
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime != expect_mime:
        raise BizError(5005, msg="文件内容与格式不符")
    if not content or not content.startswith(magic):
        raise BizError(5005, msg="文件内容与格式不符")
    if len(content) > CERT_SCENE["max_bytes"]:
        raise BizError(5005, msg="文件不能超过 20 MB")
    return ext


def apply_watermark(content: bytes, text: str) -> bytes:
    """图片打水印。PDF 原样返回，查看层禁止右键和拖拽。"""
    if content.startswith(b"%PDF"):
        return content
    from PIL import Image, ImageDraw

    image = Image.open(io.BytesIO(content)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.text((8, 8), text or "", fill=(180, 0, 0, 180))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
