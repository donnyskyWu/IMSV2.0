# 上传场景注册表。版本 v1.0 · 2026-10-13
"""证件场景自己校验扩展名、MIME、文件头和大小。"""

CERT_SCENE = {
    "scene": "cert",
    "extensions": [".jpg", ".jpeg", ".png", ".pdf"],
    "mime": ["image/jpeg", "image/png", "application/pdf"],
    "max_bytes": 20 * 1024 * 1024,
    "watermark": True,
}

SCENES = {
    "cert": CERT_SCENE,
}
