# 字段加密与等值哈希（B0a FP-C03-01）。
"""AES-256-GCM 加密，HMAC-SHA256 用独立密钥。业务代码只调这里。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings
from app.core.errors import BizError


def _aes_key(raw: str) -> bytes:
    """把配置里的密钥收成 32 字节。"""
    if not raw:
        raise BizError(1001, msg="加密密钥未配置")
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _key_for_version(version: str) -> bytes:
    security = get_settings().security
    if version == "1":
        return _aes_key(security.field_key)
    raw = (security.field_key_versions or {}).get(version, "")
    return _aes_key(raw)


def encrypt_field(plain: str, *, version: str = "1") -> str:
    """加密。同一明文两次结果不同。密文带版本前缀。"""
    if plain is None:
        raise BizError(1001, msg="加密内容为空")
    nonce = os.urandom(12)
    token = AESGCM(_key_for_version(version)).encrypt(nonce, plain.encode("utf-8"), None)
    blob = base64.urlsafe_b64encode(nonce + token).decode("ascii")
    return f"v{version}.{blob}"


def decrypt_field(stored: str) -> str:
    """按版本前缀解密。"""
    if not stored or "." not in stored or not stored.startswith("v"):
        raise BizError(1001, msg="密文格式不正确")
    version, blob = stored[1:].split(".", 1)
    raw = base64.urlsafe_b64decode(blob.encode("ascii"))
    nonce, token = raw[:12], raw[12:]
    plain = AESGCM(_key_for_version(version)).decrypt(nonce, token, None)
    return plain.decode("utf-8")


def hash_field(plain: str) -> str:
    """HMAC-SHA256。密钥是 security.hash_key，不复用 field_key。"""
    secret = get_settings().security.hash_key
    if not secret:
        raise BizError(1001, msg="哈希密钥未配置")
    if secret == get_settings().security.field_key:
        raise BizError(1001, msg="哈希密钥必须独立")
    digest = hmac.new(secret.encode("utf-8"), plain.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()
