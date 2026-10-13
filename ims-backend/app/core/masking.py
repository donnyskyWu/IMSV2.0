# app/core/masking.py - Export uses the same mask as the API (FP-C03)
"""Mask sensitive values unless the caller holds the plaintext permission."""


def export_mobile(value: str, allow_plain: bool) -> str:
    if allow_plain or not value:
        return value
    if len(value) <= 4:
        return "******"
    return "*******" + value[-4:]


def _fernet():
    """手机号对称加密。密钥由 JWT secret 派生，不把明文密钥写进代码。"""
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    from app.core.config import get_settings

    digest = hashlib.sha256(get_settings().jwt.secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_mobile(plain: str) -> str:
    """加密手机号。空串原样返回。"""
    if not plain:
        return plain
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_mobile(stored: str | None) -> str:
    """解密手机号。历史明文或坏密文按原值返回，避免列表打不开。"""
    if not stored:
        return ""
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(stored.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return stored


def mask_mobile_display(stored: str | None) -> str | None:
    """展示口径：138****5678。不足 11 位不展示。"""
    plain = decrypt_mobile(stored)
    if len(plain) >= 11:
        return plain[:3] + "****" + plain[-4:]
    return None
