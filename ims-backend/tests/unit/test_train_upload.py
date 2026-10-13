# tests/unit/test_train_upload.py - Upload validation tests (B21)
"""
Unit tests for training material upload validation.

Per review feedback: main's FileService.upload does not validate,
B21 must implement full validation → 5005.
"""

import io
from unittest.mock import MagicMock

import pytest

from app.core.errors import BizError
from app.domains.train.upload import (
    TRAIN_DOC_EXTENSIONS,
    TRAIN_DOC_MAX_SIZE,
    TRAIN_VIDEO_EXTENSIONS,
    TRAIN_VIDEO_MAX_SIZE,
    generate_storage_path,
    validate_link_url,
    validate_train_upload,
)


def make_mock_file(
    filename: str,
    content: bytes,
    content_type: str = "",
) -> MagicMock:
    """Create a mock UploadFile."""
    mock = MagicMock()
    mock.filename = filename
    mock.content_type = content_type
    
    buffer = io.BytesIO(content)
    mock.read = lambda n=None: buffer.read(n) if n else buffer.read()
    mock.seek = lambda pos, whence=0: buffer.seek(pos, whence)
    mock.file = buffer
    
    async def async_read(n=None):
        return buffer.read(n) if n else buffer.read()
    
    async def async_seek(pos, whence=0):
        return buffer.seek(pos, whence)
    
    mock.read = MagicMock(side_effect=async_read)
    mock.seek = MagicMock(side_effect=async_seek)
    
    return mock


class TestValidateLinkUrl:
    """Tests for link URL validation."""

    def test_valid_http(self):
        """Valid http:// URL passes."""
        validate_link_url("http://example.com")

    def test_valid_https(self):
        """Valid https:// URL passes."""
        validate_link_url("https://example.com/path?query=1")

    def test_empty_url(self):
        """UT-B21-UPLOAD-07: Empty URL rejected."""
        with pytest.raises(BizError) as exc:
            validate_link_url("")
        assert exc.value.code == 1001

    def test_none_url(self):
        """UT-B21-UPLOAD-07: None URL rejected."""
        with pytest.raises(BizError) as exc:
            validate_link_url(None)
        assert exc.value.code == 1001

    def test_file_protocol(self):
        """UT-B21-UPLOAD-06: file:// URL rejected."""
        with pytest.raises(BizError) as exc:
            validate_link_url("file:///etc/passwd")
        assert exc.value.code == 1001

    def test_javascript_protocol(self):
        """UT-B21-UPLOAD-06: javascript: URL rejected."""
        with pytest.raises(BizError) as exc:
            validate_link_url("javascript:alert(1)")
        assert exc.value.code == 1001

    def test_ftp_protocol(self):
        """ftp:// URL rejected."""
        with pytest.raises(BizError) as exc:
            validate_link_url("ftp://example.com")
        assert exc.value.code == 1001

    def test_no_protocol(self):
        """URL without protocol rejected."""
        with pytest.raises(BizError) as exc:
            validate_link_url("example.com")
        assert exc.value.code == 1001


class TestGenerateStoragePath:
    """Tests for storage path generation."""

    def test_path_format(self):
        """Path follows expected format."""
        path = generate_storage_path("TRAIN_DOC", 123, "pdf")
        
        assert path.startswith("train/train_doc/123/")
        assert path.endswith(".pdf")
        parts = path.split("/")
        assert len(parts) == 5

    def test_different_scenes(self):
        """Different scenes produce different paths."""
        doc_path = generate_storage_path("TRAIN_DOC", 1, "pdf")
        video_path = generate_storage_path("TRAIN_VIDEO", 1, "mp4")
        
        assert "train_doc" in doc_path
        assert "train_video" in video_path

    def test_unique_paths(self):
        """Multiple calls produce unique paths."""
        path1 = generate_storage_path("TRAIN_DOC", 1, "pdf")
        path2 = generate_storage_path("TRAIN_DOC", 1, "pdf")
        
        assert path1 != path2


class TestExtensions:
    """Tests for extension whitelist constants."""

    def test_doc_extensions(self):
        """Document extensions include expected types."""
        expected = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"}
        assert TRAIN_DOC_EXTENSIONS == expected

    def test_video_extensions(self):
        """Video extensions include expected types."""
        expected = {"mp4", "mov"}
        assert TRAIN_VIDEO_EXTENSIONS == expected

    def test_doc_max_size(self):
        """Document max size is 100MB."""
        assert TRAIN_DOC_MAX_SIZE == 100 * 1024 * 1024

    def test_video_max_size(self):
        """Video max size is 1GB."""
        assert TRAIN_VIDEO_MAX_SIZE == 1024 * 1024 * 1024


class TestValidateTrainUploadExtension:
    """Tests for extension validation in upload."""

    @pytest.mark.asyncio
    async def test_valid_pdf(self):
        """UT-B21-UPLOAD-08: Valid PDF passes."""
        content = b"%PDF-1.4 valid pdf content"
        mock_file = make_mock_file("test.pdf", content, "application/pdf")
        
        await validate_train_upload(mock_file, "TRAIN_DOC")

    @pytest.mark.asyncio
    async def test_reject_exe(self):
        """UT-B21-UPLOAD-01: .exe rejected."""
        content = b"MZ executable content"
        mock_file = make_mock_file("test.exe", content)
        
        with pytest.raises(BizError) as exc:
            await validate_train_upload(mock_file, "TRAIN_DOC")
        assert exc.value.code == 5005
        assert ".exe" in exc.value.msg

    @pytest.mark.asyncio
    async def test_reject_js(self):
        """UT-B21-UPLOAD-02: .js rejected."""
        content = b"console.log('hello')"
        mock_file = make_mock_file("script.js", content, "application/javascript")
        
        with pytest.raises(BizError) as exc:
            await validate_train_upload(mock_file, "TRAIN_DOC")
        assert exc.value.code == 5005

    @pytest.mark.asyncio
    async def test_unknown_scene(self):
        """Unknown scene rejected."""
        content = b"%PDF-1.4"
        mock_file = make_mock_file("test.pdf", content)
        
        with pytest.raises(BizError) as exc:
            await validate_train_upload(mock_file, "UNKNOWN")
        assert exc.value.code == 5005
