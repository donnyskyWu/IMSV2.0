# app/core/masking.py - Export uses the same mask as the API (FP-C03)
"""Mask sensitive values unless the caller holds the plaintext permission."""


def mask_id_card(value: str) -> str:
    """证件号前 3 后 4，中间打星。"""
    if not value:
        return ""
    if len(value) <= 7:
        return "******"
    return value[:3] + ("*" * (len(value) - 7)) + value[-4:]


def mask_mobile(value: str) -> str:
    """手机号显示为 138****5678。"""
    if not value:
        return ""
    if len(value) < 7:
        return "******"
    return value[:3] + "****" + value[-4:]


def export_mobile(value: str, allow_plain: bool) -> str:
    if allow_plain or not value:
        return value
    if len(value) <= 4:
        return "******"
    return "*******" + value[-4:]
