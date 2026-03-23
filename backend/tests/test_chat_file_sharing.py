"""
Backend tests: Secure File Sharing System
Tests for file validation, upload endpoint, download access control, and audit logging.
"""

import hashlib
import hmac
import time
import pytest

# ── Unit Tests: file_service ────────────────────────────────────────────────────

def test_validate_allowed_extension():
    """PDF, DOCX, TXT should pass validation."""
    from app.services.file_service import validate_file
    # Should not raise
    validate_file("report.pdf", "application/pdf", 1024 * 1024)
    validate_file("notes.txt", "text/plain", 512)
    validate_file("spreadsheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 10_000)


def test_validate_blocked_extension():
    """Executables should be rejected with 400."""
    from app.services.file_service import validate_file
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_file("malware.exe", "application/octet-stream", 1024)
    assert exc_info.value.status_code == 400
    assert "not allowed" in exc_info.value.detail.lower()


def test_validate_shell_script():
    """Shell scripts should be blocked."""
    from app.services.file_service import validate_file
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_file("deploy.sh", "text/x-sh", 256)
    assert exc_info.value.status_code == 400


def test_validate_python_blocked():
    """Python scripts should be blocked."""
    from app.services.file_service import validate_file
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        validate_file("backdoor.py", "text/x-python", 512)


def test_validate_unknown_extension():
    """Unknown/unlisted extension should be rejected."""
    from app.services.file_service import validate_file
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_file("data.xyz", "application/octet-stream", 100)
    assert exc_info.value.status_code == 400
    assert "unsupported" in exc_info.value.detail.lower()


def test_validate_size_limit():
    """Files over the configured limit should raise 413."""
    from app.services.file_service import validate_file
    from fastapi import HTTPException
    max_bytes = 20 * 1024 * 1024  # 20 MB
    with pytest.raises(HTTPException) as exc_info:
        validate_file("big.pdf", "application/pdf", max_bytes + 1)
    assert exc_info.value.status_code == 413


def test_validate_size_at_limit():
    """A file exactly at the limit should pass."""
    from app.services.file_service import validate_file
    max_bytes = 20 * 1024 * 1024
    validate_file("edge.pdf", "application/pdf", max_bytes)  # should not raise


# ── Unit Tests: download token ─────────────────────────────────────────────────

def test_download_token_roundtrip():
    """Generated token should verify correctly for same file + user."""
    from app.services.file_service import generate_download_token, verify_download_token
    file_id = "abc123"
    user_id = "user456"
    token = generate_download_token(file_id, user_id)
    # Should not raise
    result = verify_download_token(token, file_id, user_id)
    assert result is True


def test_download_token_wrong_user():
    """Token should be rejected for a different user_id."""
    from app.services.file_service import generate_download_token, verify_download_token
    from fastapi import HTTPException
    token = generate_download_token("file1", "userA")
    with pytest.raises(HTTPException) as exc_info:
        verify_download_token(token, "file1", "userB")
    assert exc_info.value.status_code == 401


def test_download_token_wrong_file():
    """Token should be rejected for a different file_id."""
    from app.services.file_service import generate_download_token, verify_download_token
    from fastapi import HTTPException
    token = generate_download_token("file1", "user1")
    with pytest.raises(HTTPException) as exc_info:
        verify_download_token(token, "file2", "user1")
    assert exc_info.value.status_code == 401


def test_download_token_tampered():
    """Tampered signature should be rejected."""
    from app.services.file_service import generate_download_token, verify_download_token
    from fastapi import HTTPException
    token = generate_download_token("file1", "user1")
    parts = token.split(".")
    parts[-1] = "deadbeef" * 8   # replace signature
    bad_token = ".".join(parts)
    with pytest.raises(HTTPException) as exc_info:
        verify_download_token(bad_token, "file1", "user1")
    assert exc_info.value.status_code == 401


def test_download_token_malformed():
    """A malformed token should raise 400."""
    from app.services.file_service import verify_download_token
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        verify_download_token("not-a-valid-token", "file1", "user1")
    assert exc_info.value.status_code == 400


# ── Unit Tests: file storage helpers ──────────────────────────────────────────

def test_human_readable_size():
    from app.services.file_service import human_readable_size
    assert "KB" in human_readable_size(2048)
    assert "MB" in human_readable_size(2 * 1024 * 1024)
    assert "B" in human_readable_size(500)


def test_get_extension():
    from app.services.file_service import get_extension
    assert get_extension("report.pdf") == "pdf"
    assert get_extension("NOTES.TXT") == "txt"
    assert get_extension("no_extension") == ""


def test_allowed_extensions_set():
    """Verify the allowed set includes expected types."""
    from app.services.file_service import ALLOWED_EXTENSIONS, BLOCKED_EXTENSIONS
    assert "pdf" in ALLOWED_EXTENSIONS
    assert "docx" in ALLOWED_EXTENSIONS
    assert "xlsx" in ALLOWED_EXTENSIONS
    assert "png" in ALLOWED_EXTENSIONS
    assert "exe" in BLOCKED_EXTENSIONS
    assert "sh" in BLOCKED_EXTENSIONS
    assert "py" in BLOCKED_EXTENSIONS
    assert "bat" in BLOCKED_EXTENSIONS


def test_save_and_read_file(tmp_path):
    """Files written to disk should be readable back."""
    from app.services.file_service import save_file_to_disk, read_file_from_disk
    content = b"Hello, TBAPS file service!"
    dest    = tmp_path / "test_file.pdf"
    checksum = save_file_to_disk(content, dest)
    # Verify checksum
    assert checksum == hashlib.sha256(content).hexdigest()
    # Read back
    read_back = read_file_from_disk(str(dest))
    assert read_back == content


def test_read_missing_file_raises_404(tmp_path):
    from app.services.file_service import read_file_from_disk
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        read_file_from_disk(str(tmp_path / "nonexistent.pdf"))
    assert exc_info.value.status_code == 404
