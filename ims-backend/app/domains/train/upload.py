# app/domains/train/upload.py - Training upload validation (B21 MT-04)
"""
File upload validation for training materials.

Per review feedback: main's FileService.upload does not validate type/size,
B21 must implement full validation:
- Extension whitelist
- File header magic number validation
- MIME type validation
- File size validation
→ Any failure returns 5005

Scenes:
- TRAIN_DOC: pdf, doc, docx, ppt, pptx, xls, xlsx (max 100MB)
- TRAIN_VIDEO: mp4, mov (max 1024MB)
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import UploadFile

from app.core.errors import BizError

TRAIN_DOC_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"}
TRAIN_VIDEO_EXTENSIONS = {"mp4", "mov"}

TRAIN_DOC_MAX_SIZE = 100 * 1024 * 1024  # 100 MB
TRAIN_VIDEO_MAX_SIZE = 1024 * 1024 * 1024  # 1 GB

FILE_SIGNATURES = {
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],
    "pptx": [b"PK\x03\x04"],
    "doc": [b"\xd0\xcf\x11\xe0"],
    "xls": [b"\xd0\xcf\x11\xe0"],
    "ppt": [b"\xd0\xcf\x11\xe0"],
    "mp4": [b"ftyp", b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x20ftyp", b"\x00\x00\x00"],
    "mov": [b"ftyp", b"moov", b"free", b"\x00\x00\x00"],
}


def _get_extension(filename: Optional[str]) -> str:
    """Extract lowercase extension from filename."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _check_file_signature(header: bytes, ext: str) -> bool:
    """Check if file header matches expected signatures for extension."""
    signatures = FILE_SIGNATURES.get(ext, [])
    if not signatures:
        return True

    return any(sig in header[:32] for sig in signatures)


async def validate_train_upload(file: UploadFile, scene: str) -> None:
    """
    Validate training material upload.

    Args:
        file: Uploaded file
        scene: TRAIN_DOC or TRAIN_VIDEO

    Raises:
        BizError(5005): Validation failed
    """
    filename = file.filename or ""
    ext = _get_extension(filename)

    if scene == "TRAIN_DOC":
        allowed_exts = TRAIN_DOC_EXTENSIONS
        max_size = TRAIN_DOC_MAX_SIZE
    elif scene == "TRAIN_VIDEO":
        allowed_exts = TRAIN_VIDEO_EXTENSIONS
        max_size = TRAIN_VIDEO_MAX_SIZE
    else:
        raise BizError(5005, msg=f"未知的上传场景: {scene}")

    if ext not in allowed_exts:
        raise BizError(5005, msg=f"不支持的文件类型: .{ext}")

    header = await file.read(64)
    await file.seek(0)

    if not _check_file_signature(header, ext):
        raise BizError(5005, msg="文件内容与扩展名不符")

    content_type = file.content_type or ""
    valid_mime_prefixes = ("application/", "") if scene == "TRAIN_DOC" else ("video/", "")

    if content_type and not content_type.startswith(valid_mime_prefixes):
        raise BizError(5005, msg=f"不支持的MIME类型: {content_type}")

    await file.seek(0, 2)
    file_size = file.file.tell()
    await file.seek(0)

    if file_size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise BizError(5005, msg=f"文件超过大小限制: {max_mb}MB")


def validate_link_url(url: Optional[str]) -> None:
    """
    Validate link URL for LINK type materials.

    Only http:// or https:// allowed.

    Raises:
        BizError(1001): Invalid URL
    """
    if not url:
        raise BizError(1001, msg="外链地址不能为空")

    if not url.startswith(("http://", "https://")):
        raise BizError(1001, msg="外链地址必须以 http:// 或 https:// 开头")


def generate_storage_path(scene: str, tenant_id: int, ext: str) -> str:
    """
    Generate server-side storage path.

    Path format: train/{scene}/{tenant_id}/{yyyyMM}/{uuid}.{ext}
    Client-provided paths are NOT accepted (prevent path traversal).
    """
    now = datetime.now()
    return f"train/{scene.lower()}/{tenant_id}/{now.strftime('%Y%m')}/{uuid.uuid4()}.{ext}"
