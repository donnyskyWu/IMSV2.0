# tests/unit/test_org_sync_callback.py - DingTalk callback cryptography tests
"""
Unit tests for DingTalk callback signature verification and AES encryption.

Tests:
- SHA1 signature verification
- AES-256-CBC encryption/decryption with PKCS#7 (block=32)
- Replay protection (timestamp window, nonce dedup)
"""

import base64
import secrets
import struct
from datetime import datetime

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.api.org_sync_callback import (
    BLOCK_SIZE,
    _check_replay,
    _pkcs7_pad,
    _pkcs7_unpad,
    decrypt_callback,
    encrypt_callback,
    encrypt_response,
    sign_callback,
    verify_callback_signature,
)
from app.core.clock import reset_clock, set_clock


class TestPKCS7Padding:
    """Test PKCS#7 padding with block size 32."""

    def test_pad_exact_block(self):
        """Data that is exactly block size gets full padding block."""
        data = b"a" * 32
        padded = _pkcs7_pad(data, BLOCK_SIZE)
        assert len(padded) == 64
        assert padded[-32:] == bytes([32] * 32)

    def test_pad_partial_block(self):
        """Partial block data gets padding to next block."""
        data = b"hello"
        padded = _pkcs7_pad(data, BLOCK_SIZE)
        assert len(padded) == 32
        pad_len = 32 - len(data)
        assert padded[-pad_len:] == bytes([pad_len] * pad_len)

    def test_unpad(self):
        """Unpad correctly removes padding."""
        data = b"hello"
        padded = _pkcs7_pad(data, BLOCK_SIZE)
        unpadded = _pkcs7_unpad(padded)
        assert unpadded == data

    def test_roundtrip(self):
        """Pad then unpad returns original data."""
        for length in [0, 1, 15, 16, 31, 32, 64, 100]:
            original = secrets.token_bytes(length)
            padded = _pkcs7_pad(original, BLOCK_SIZE)
            assert len(padded) % BLOCK_SIZE == 0
            unpadded = _pkcs7_unpad(padded)
            assert unpadded == original


class TestSignatureVerification:
    """Test SHA1 signature verification."""

    def test_valid_signature(self):
        """Valid signature passes verification."""
        token = "testtoken"
        timestamp = "1700000000"
        nonce = "randomnonce"
        encrypt = "encrypted_data_base64"
        signature = sign_callback(token, timestamp, nonce, encrypt)
        assert verify_callback_signature(token, timestamp, nonce, encrypt, signature)

    def test_invalid_signature(self):
        """Invalid signature fails verification."""
        token = "testtoken"
        timestamp = "1700000000"
        nonce = "randomnonce"
        encrypt = "encrypted_data_base64"
        wrong_sig = "0" * 40
        assert not verify_callback_signature(token, timestamp, nonce, encrypt, wrong_sig)

    def test_signature_ordering(self):
        """Signature uses sorted concatenation."""
        import hashlib

        token = "bbb"
        timestamp = "aaa"
        nonce = "ccc"
        encrypt = "ddd"
        sorted_str = "".join(sorted([token, timestamp, nonce, encrypt]))
        expected = hashlib.sha1(sorted_str.encode()).hexdigest()
        actual = sign_callback(token, timestamp, nonce, encrypt)
        assert actual == expected

    def test_signature_case_sensitive(self):
        """Signature verification is case-sensitive."""
        token = "Token"
        timestamp = "1700000000"
        nonce = "Nonce"
        encrypt = "Data"
        sig = sign_callback(token, timestamp, nonce, encrypt)
        assert not verify_callback_signature(token.lower(), timestamp, nonce, encrypt, sig)


class TestAESEncryption:
    """Test AES-256-CBC encryption/decryption."""

    @pytest.fixture
    def aes_key(self):
        """Generate a valid 43-char Base64 AES key (32 bytes when decoded with =)."""
        raw_key = secrets.token_bytes(32)
        return base64.b64encode(raw_key).decode().rstrip("=")

    def test_encrypt_decrypt_roundtrip(self, aes_key):
        """Encrypt then decrypt returns original message."""
        msg = "hello world"
        receiveid = "testappkey"
        encrypted = encrypt_callback(aes_key, msg, receiveid)
        decrypted = decrypt_callback(aes_key, encrypted, receiveid)
        assert decrypted == msg

    def test_decrypt_with_wrong_receiveid(self, aes_key):
        """Decrypt with wrong receiveid raises ValueError."""
        msg = "test message"
        receiveid = "correct_appkey"
        encrypted = encrypt_callback(aes_key, msg, receiveid)
        with pytest.raises(ValueError, match="receiveid mismatch"):
            decrypt_callback(aes_key, encrypted, "wrong_appkey")

    def test_encrypt_produces_different_ciphertext(self, aes_key):
        """Same message produces different ciphertext due to random prefix."""
        msg = "same message"
        receiveid = "appkey"
        c1 = encrypt_callback(aes_key, msg, receiveid)
        c2 = encrypt_callback(aes_key, msg, receiveid)
        assert c1 != c2
        assert decrypt_callback(aes_key, c1, receiveid) == msg
        assert decrypt_callback(aes_key, c2, receiveid) == msg

    def test_unicode_message(self, aes_key):
        """Unicode messages encrypt/decrypt correctly."""
        msg = "你好世界🎉"
        receiveid = "dingtalkapp"
        encrypted = encrypt_callback(aes_key, msg, receiveid)
        decrypted = decrypt_callback(aes_key, encrypted, receiveid)
        assert decrypted == msg

    def test_empty_message(self, aes_key):
        """Empty message encrypts/decrypts correctly."""
        msg = ""
        receiveid = "appkey"
        encrypted = encrypt_callback(aes_key, msg, receiveid)
        decrypted = decrypt_callback(aes_key, encrypted, receiveid)
        assert decrypted == msg

    def test_long_message(self, aes_key):
        """Long messages encrypt/decrypt correctly."""
        msg = "x" * 10000
        receiveid = "appkey"
        encrypted = encrypt_callback(aes_key, msg, receiveid)
        decrypted = decrypt_callback(aes_key, encrypted, receiveid)
        assert decrypted == msg


class TestOfficialSdkVectors:
    """Test vectors compatible with DingTalk official SDK."""

    def test_known_aes_key_format(self):
        """AES key format: 43 chars Base64, appending = gives 32 bytes."""
        raw_key = b"abcdefghijklmnopqrstuvwxyz012345"
        aes_key_43 = base64.b64encode(raw_key).decode().rstrip("=")
        assert len(aes_key_43) == 43
        raw = base64.b64decode(aes_key_43 + "=")
        assert raw == raw_key
        assert len(raw) == 32

    def test_plaintext_structure(self):
        """Plaintext structure: random(16) + msg_len(4) + msg + receiveid."""
        aes_key = base64.b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        msg = "test"
        receiveid = "app"
        encrypted = encrypt_callback(aes_key, msg, receiveid)

        key = base64.b64decode(aes_key + "=")
        iv = key[:16]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(base64.b64decode(encrypted)) + decryptor.finalize()
        decrypted = _pkcs7_unpad(decrypted)

        assert len(decrypted[:16]) == 16
        msg_len = struct.unpack(">I", decrypted[16:20])[0]
        assert msg_len == len(msg.encode())
        assert decrypted[20 : 20 + msg_len].decode() == msg
        assert decrypted[20 + msg_len :].decode() == receiveid


class TestReplayProtection:
    """Test replay protection mechanisms."""

    @pytest.fixture(autouse=True)
    def setup_clock(self, db_session):
        """Set up fixed clock for tests."""
        set_clock(lambda: datetime(2026, 10, 13, 10, 0, 0))
        yield
        reset_clock()

    def test_timestamp_out_of_range(self):
        """Timestamp outside 5 minute window triggers replay."""
        old_ts = str(int(datetime(2026, 10, 13, 9, 54, 0).timestamp()))
        nonce = secrets.token_hex(8)
        assert _check_replay(old_ts, nonce) is True

        future_ts = str(int(datetime(2026, 10, 13, 10, 6, 0).timestamp()))
        assert _check_replay(future_ts, secrets.token_hex(8)) is True

    def test_timestamp_within_range(self):
        """Timestamp within 5 minute window passes."""
        valid_ts = str(int(datetime(2026, 10, 13, 10, 0, 0).timestamp()))
        nonce = secrets.token_hex(8)
        assert _check_replay(valid_ts, nonce) is False

    def test_nonce_reuse_blocked(self):
        """Same nonce used twice triggers replay."""
        valid_ts = str(int(datetime(2026, 10, 13, 10, 0, 0).timestamp()))
        nonce = "test_nonce_123"
        assert _check_replay(valid_ts, nonce) is False
        assert _check_replay(valid_ts, nonce) is True

    def test_invalid_timestamp_format(self):
        """Invalid timestamp format triggers replay."""
        assert _check_replay("not_a_number", "nonce") is True
        assert _check_replay("", "nonce") is True


class TestEncryptResponse:
    """Test encrypt_response function."""

    def test_encrypt_response_structure(self):
        """Response has required fields."""
        aes_key = base64.b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        token = "test_token"
        app_key = "test_app_key"

        response = encrypt_response(token, aes_key, app_key)

        assert "msg_signature" in response
        assert "timeStamp" in response
        assert "nonce" in response
        assert "encrypt" in response
        assert len(response["msg_signature"]) == 40
        assert response["timeStamp"].isdigit()

    def test_encrypt_response_decrypts_to_success(self):
        """Response encrypts 'success' message."""
        aes_key = base64.b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        token = "test_token"
        app_key = "test_app_key"

        response = encrypt_response(token, aes_key, app_key)
        decrypted = decrypt_callback(aes_key, response["encrypt"], app_key)

        assert decrypted == "success"

    def test_encrypt_response_signature_valid(self):
        """Response signature is valid."""
        aes_key = base64.b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        token = "test_token"
        app_key = "test_app_key"

        response = encrypt_response(token, aes_key, app_key)

        assert verify_callback_signature(
            token,
            response["timeStamp"],
            response["nonce"],
            response["encrypt"],
            response["msg_signature"],
        )
