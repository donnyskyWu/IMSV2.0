# app/core/masking.py - Export uses the same mask as the API (FP-C03)
"""Mask sensitive values unless the caller holds the plaintext permission."""


def export_mobile(value: str, allow_plain: bool) -> str:
    if allow_plain or not value:
        return value
    if len(value) <= 4:
        return "******"
    return "*******" + value[-4:]
