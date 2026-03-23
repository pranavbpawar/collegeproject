"""
TBAPS — Secure File Service
Handles validation, storage, checksum, and time-limited download tokens
for files shared through the chat system.
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Allowed / blocked extensions ───────────────────────────────────────────────

ALLOWED_EXTENSIONS: set[str] = {
    "pdf", "doc", "docx", "xls", "xlsx",
    "ppt", "pptx", "txt", "csv", "rtf",
    "png", "jpg", "jpeg", "gif", "webp",
    "zip",                                  # archives allowed (not executables)
}

BLOCKED_EXTENSIONS: set[str] = {
    "exe", "msi", "dmg", "deb", "rpm", "pkg",   # installers
    "sh", "bash", "zsh", "fish",                  # shell scripts
    "bat", "cmd", "ps1", "psm1", "psd1",          # Windows scripts
    "py", "pyc", "pyw",                            # Python
    "js", "ts", "jsx", "tsx",                      # JavaScript / TS
    "php", "rb", "pl", "lua",                      # other scripts
    "dll", "so", "dylib",                          # shared libraries
    "bin", "elf",                                  # raw binaries
    "vbs", "wsf", "hta",                           # VBScript / HTA
    "jar", "class",                                # Java
    "scr", "com", "pif",                           # Windows malware vectors
}

# ── Constants ───────────────────────────────────────────────────────────────────

DEFAULT_MAX_MB     = 20
_TOKEN_SECRET_SALT = "chat_file_download_token"


def _get_max_bytes() -> int:
    """Return the configured max file size in bytes."""
    mb = getattr(settings, "CHAT_FILE_MAX_MB", DEFAULT_MAX_MB)
    return int(mb) * 1024 * 1024


def _get_storage_root() -> Path:
    root = getattr(settings, "CHAT_STORAGE_PATH", "/storage/chat_files")
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_token_expiry_hours() -> int:
    return int(getattr(settings, "CHAT_FILE_TOKEN_EXPIRY_HOURS", 24))


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_file(filename: str, content_type: str, size: int) -> None:
    """
    Raise HTTPException if the file fails validation:
    - blocked extension
    - not in allowed extension list
    - exceeds size limit
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '.{ext}' is not allowed for security reasons.",
        )

    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '.{ext}'. Allowed: {allowed}",
        )

    max_bytes = _get_max_bytes()
    if size > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({size // (1024*1024)} MB). Maximum allowed: {max_mb} MB.",
        )


def get_extension(filename: str) -> str:
    """Extract lowercase extension from filename."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


# ── Storage ────────────────────────────────────────────────────────────────────

def build_storage_path(file_id: str, employee_id: str, conversation_id: str, original_name: str) -> Path:
    """
    Return the on-disk path for a chat file.
    Layout: {storage_root}/{employee_id}/{conversation_id}/{file_id}.{ext}
    """
    ext = get_extension(original_name)
    root = _get_storage_root()
    folder = root / str(employee_id) / str(conversation_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{file_id}.{ext}"


def save_file_to_disk(content: bytes, storage_path: Path) -> str:
    """
    Write file bytes to disk. Returns SHA-256 hex digest.
    """
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = hashlib.sha256(content).hexdigest()
    with open(storage_path, "wb") as f:
        f.write(content)
    logger.info(f"[file_service] Saved {len(content)} bytes → {storage_path}")
    return sha256


def read_file_from_disk(storage_path: str) -> bytes:
    """Read file from disk. Raises 404 if missing."""
    path = Path(storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on server.")
    return path.read_bytes()


def delete_file_from_disk(storage_path: str) -> None:
    """Delete file from disk silently."""
    try:
        Path(storage_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"[file_service] Could not delete {storage_path}: {e}")


# ── Time-Limited Download Tokens ───────────────────────────────────────────────

def generate_download_token(file_id: str, user_id: str) -> str:
    """
    Generate a time-limited, HMAC-signed download token.
    Format: {expires_ts}.{hmac_hex}
    """
    expiry_hours = _get_token_expiry_hours()
    expires_at   = int(time.time()) + expiry_hours * 3600
    message      = f"{file_id}:{user_id}:{expires_at}:{_TOKEN_SECRET_SALT}"
    secret       = (settings.JWT_SECRET_KEY + _TOKEN_SECRET_SALT).encode()
    sig          = hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()
    raw          = f"{expires_at}.{file_id}.{user_id}.{sig}"
    return raw


def verify_download_token(token: str, file_id: str, user_id: str) -> bool:
    """
    Verify a download token. Returns True if valid and not expired.
    Raises 401/410 HTTPException on failure.
    """
    try:
        expires_at_str, t_file_id, t_user_id, received_sig = token.split(".", 3)
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed download token.")

    # Check file_id and user_id match
    if t_file_id != file_id or t_user_id != user_id:
        raise HTTPException(status_code=401, detail="Token does not match this file or user.")

    # Check expiry
    expires_at = int(expires_at_str)
    if time.time() > expires_at:
        raise HTTPException(status_code=410, detail="Download link has expired. Request a new link.")

    # Verify HMAC
    message = f"{file_id}:{user_id}:{expires_at_str}:{_TOKEN_SECRET_SALT}"
    secret  = (settings.JWT_SECRET_KEY + _TOKEN_SECRET_SALT).encode()
    expected_sig = hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, received_sig):
        raise HTTPException(status_code=401, detail="Invalid download token signature.")

    return True


def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
