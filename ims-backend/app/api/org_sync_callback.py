# app/api/org_sync_callback.py - DingTalk event callback (FP-B1-BG-01)
"""
DingTalk organization event callback endpoint.

Implements:
- SHA1 signature verification
- AES-256-CBC encryption/decryption
- Nonce-based replay protection
- Event reception and storage
"""

import base64
import contextlib
import hashlib
import hmac
import json
import logging
import secrets
import struct
from typing import Any, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.core.cache import Cache
from app.core.clock import get_now
from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.org_sync_event import OrgSyncEventService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/callback/dingtalk", tags=["DingTalk Callback"])

BLOCK_SIZE = 32
NONCE_TTL = 600
TIMESTAMP_WINDOW = 300


class CallbackBody(BaseModel):
    """DingTalk callback request body."""

    encrypt: str


def _pkcs7_pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    """PKCS#7 padding."""
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


def _pkcs7_unpad(data: bytes) -> bytes:
    """Remove PKCS#7 padding."""
    pad_len = data[-1]
    return data[:-pad_len]


def verify_callback_signature(
    token: str,
    timestamp: str,
    nonce: str,
    encrypt: str,
    msg_signature: str,
) -> bool:
    """
    Verify DingTalk callback signature.

    Algorithm:
    1. Sort [token, timestamp, nonce, encrypt]
    2. Concatenate and SHA1 hash
    3. Compare with msg_signature
    """
    to_sign = "".join(sorted([token, timestamp, nonce, encrypt]))
    expected = hashlib.sha1(to_sign.encode()).hexdigest()
    return hmac.compare_digest(expected, msg_signature)


def decrypt_callback(aes_key: str, encrypt: str, expected_receiveid: str) -> str:
    """
    AES-256-CBC decrypt DingTalk callback.

    Plaintext structure: random(16) + msg_len(4, big-endian) + msg + receiveid
    - key = Base64Decode(aes_key + '=')
    - IV = key[:16]
    - PKCS#7 block size = 32

    Args:
        aes_key: 43-char Base64 encoded AES key
        encrypt: Base64 encoded ciphertext
        expected_receiveid: AppKey for internal app

    Returns:
        Decrypted message string

    Raises:
        ValueError: If receiveid doesn't match
    """
    key = base64.b64decode(aes_key + "=")
    iv = key[:16]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(base64.b64decode(encrypt)) + decryptor.finalize()
    decrypted = _pkcs7_unpad(decrypted)
    msg_len = struct.unpack(">I", decrypted[16:20])[0]
    msg = decrypted[20 : 20 + msg_len].decode()
    receiveid = decrypted[20 + msg_len :].decode()
    if receiveid != expected_receiveid:
        raise ValueError("receiveid mismatch")
    return msg


def encrypt_callback(aes_key: str, msg: str, receiveid: str) -> str:
    """
    AES-256-CBC encrypt DingTalk callback response.

    Plaintext structure: random(16) + msg_len(4, big-endian) + msg + receiveid
    """
    key = base64.b64decode(aes_key + "=")
    iv = key[:16]
    random_bytes = secrets.token_bytes(16)
    msg_bytes = msg.encode()
    receiveid_bytes = receiveid.encode()
    plaintext = (
        random_bytes
        + struct.pack(">I", len(msg_bytes))
        + msg_bytes
        + receiveid_bytes
    )
    plaintext = _pkcs7_pad(plaintext, BLOCK_SIZE)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(plaintext) + encryptor.finalize()
    return base64.b64encode(encrypted).decode()


def sign_callback(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    """Generate callback response signature (SHA1)."""
    to_sign = "".join(sorted([token, timestamp, nonce, encrypt]))
    return hashlib.sha1(to_sign.encode()).hexdigest()


def encrypt_response(token: str, aes_key: str, app_key: str) -> dict[str, Any]:
    """
    Build encrypted success response.

    Args:
        token: callback_token for signing
        aes_key: callback_aes_key for encryption
        app_key: AppKey as receiveid
    """
    nonce = secrets.token_hex(8)
    timestamp = str(int(get_now().timestamp()))
    msg = "success"
    encrypt = encrypt_callback(aes_key, msg, app_key)
    signature = sign_callback(token, timestamp, nonce, encrypt)
    return {
        "msg_signature": signature,
        "timeStamp": timestamp,
        "nonce": nonce,
        "encrypt": encrypt,
    }


def _check_replay(timestamp: str, nonce: str) -> bool:
    """
    Check for replay attack.

    Rules:
    - timestamp must be within 5 minutes
    - nonce must not exist in Redis (TTL 10 minutes)

    Returns:
        True if replay detected, False otherwise
    """
    now = get_now()
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return True

    if abs(now.timestamp() - ts) > TIMESTAMP_WINDOW:
        logger.warning("Callback timestamp out of range ts=%s", timestamp)
        return True

    nonce_key = f"dingtalk:nonce:{nonce}"
    if Cache.get(nonce_key):
        logger.warning("Callback nonce already used nonce=%s", nonce)
        return True

    Cache.set(nonce_key, "1", ttl=NONCE_TTL)
    return False


def _get_tenant_by_corp_id(corp_id: str) -> Optional[int]:
    """Get tenant ID by DingTalk corp_id."""
    settings = get_settings()
    if corp_id == settings.dingtalk.corp_id:
        from app.domains.sys.models import Tenant

        session = get_db_session()
        tenant = session.query(Tenant).filter(
            Tenant.deleted == 0,
            Tenant.status == "ENABLED",
        ).first()
        if tenant:
            return tenant.id
    return None


def _parse_event(msg: str) -> dict[str, Any]:
    """Parse DingTalk event message."""
    try:
        return json.loads(msg)
    except json.JSONDecodeError:
        return {}


def _map_event_type(dingtalk_type: str) -> str:
    """Map DingTalk event type to IMS biz_type."""
    mapping = {
        "user_add_org": "HIRE",
        "user_modify_org": "USER_UPDATE",
        "user_leave_org": "RESIGN",
        "org_dept_create": "DEPT_CREATE",
        "org_dept_modify": "DEPT_UPDATE",
        "org_dept_remove": "DEPT_DELETE",
    }
    return mapping.get(dingtalk_type, dingtalk_type)


@router.post("/event")
async def handle_dingtalk_callback(
    request: Request,
    body: CallbackBody,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
) -> dict[str, Any]:
    """
    Handle DingTalk event callback.

    Processing order:
    1. Verify signature
    2. Check replay (timestamp + nonce)
    3. AES decrypt
    4. Validate receiveid
    5. Match tenant by CorpId
    6. Write event
    7. Return encrypted success

    Anonymous endpoint - authenticated by signature.
    """
    settings = get_settings()

    callback_token = settings.dingtalk.callback_token
    callback_aes_key = settings.dingtalk.callback_aes_key
    app_key = settings.dingtalk.app_key
    corp_id = settings.dingtalk.corp_id

    if not callback_token or not callback_aes_key or not app_key:
        logger.error("DingTalk callback not configured")
        return {"code": 1008, "msg": "暂无权限"}

    if not verify_callback_signature(
        callback_token, timestamp, nonce, body.encrypt, msg_signature
    ):
        logger.warning("Callback signature verification failed")
        return {"code": 1008, "msg": "暂无权限"}

    if _check_replay(timestamp, nonce):
        logger.warning("Callback replay detected")
        return {"code": 1008, "msg": "暂无权限"}

    try:
        msg = decrypt_callback(callback_aes_key, body.encrypt, app_key)
    except ValueError as exc:
        logger.warning("Callback decrypt failed: %s", exc)
        return {"code": 1008, "msg": "暂无权限"}
    except Exception as exc:
        logger.error("Callback decrypt error: %s", exc)
        return {"code": 1008, "msg": "暂无权限"}

    event_data = _parse_event(msg)

    if event_data.get("EventType") == "check_url":
        logger.info("DingTalk check_url request received")
        return encrypt_response(callback_token, callback_aes_key, app_key)

    event_corp_id = event_data.get("CorpId", "")
    if event_corp_id != corp_id:
        logger.info(
            "CorpId mismatch expected=%s got=%s",
            corp_id,
            event_corp_id,
        )
        return {"code": 0}

    tenant_id = _get_tenant_by_corp_id(event_corp_id)
    if tenant_id is None:
        logger.warning("No tenant found for corp_id=%s", event_corp_id)
        return {"code": 0}

    event_type = event_data.get("EventType", "")
    event_id = event_data.get("EventId") or f"{event_type}:{timestamp}:{nonce}"
    event_time = None
    if event_data.get("TimeStamp"):
        from datetime import datetime

        with contextlib.suppress(ValueError, TypeError):
            event_time = datetime.fromtimestamp(
                int(event_data["TimeStamp"]) / 1000
            )

    biz_type = _map_event_type(event_type)

    user_id_list = event_data.get("UserId", [])
    if isinstance(user_id_list, str):
        user_id_list = [user_id_list]

    dept_id_list = event_data.get("DeptId", [])
    if isinstance(dept_id_list, str):
        dept_id_list = [dept_id_list]

    service = OrgSyncEventService()

    for dingtalk_user_id in user_id_list:
        await service.receive_event(
            tenant_id=tenant_id,
            event_id=f"{event_id}:{dingtalk_user_id}",
            event_type=event_type,
            event_time=event_time,
            payload=msg,
            biz_type=biz_type,
        )

    for dingtalk_dept_id in dept_id_list:
        await service.receive_event(
            tenant_id=tenant_id,
            event_id=f"{event_id}:{dingtalk_dept_id}",
            event_type=event_type,
            event_time=event_time,
            payload=msg,
            biz_type=biz_type,
        )

    if not user_id_list and not dept_id_list:
        await service.receive_event(
            tenant_id=tenant_id,
            event_id=event_id,
            event_type=event_type,
            event_time=event_time,
            payload=msg,
            biz_type=biz_type,
        )

    logger.info(
        "Processed callback event_type=%s event_id=%s",
        event_type,
        event_id,
    )

    return encrypt_response(callback_token, callback_aes_key, app_key)
