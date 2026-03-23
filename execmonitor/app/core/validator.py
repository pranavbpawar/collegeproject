"""
validator.py – Security checks before executing an uploaded file.
"""
import os
import stat
import platform
from app.core.config import MAGIC_ELF, MAGIC_MZ, MAGIC_SHEBANG, UPLOAD_DIR


class ValidationError(Exception):
    """Raised when a file fails security validation."""


def _read_magic(path: str, n: int = 4) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError as e:
        raise ValidationError(f"Cannot read file: {e}") from e


def _is_valid_magic(magic: bytes) -> bool:
    return (
        magic[:4] == MAGIC_ELF
        or magic[:2] == MAGIC_MZ
        or magic[:2] == MAGIC_SHEBANG
    )


def validate_executable(path: str) -> str:
    """
    Validate *path* is a safe executable.

    Returns the validated absolute path on success.
    Raises ValidationError on any failure.
    """
    if not path or not isinstance(path, str):
        raise ValidationError("No file path provided.")

    abs_path = os.path.realpath(path)

    # 1. Must exist
    if not os.path.isfile(abs_path):
        raise ValidationError(f"File not found: {abs_path}")

    # 2. Must live inside UPLOAD_DIR (prevent path-traversal)
    real_upload = os.path.realpath(UPLOAD_DIR)
    if not abs_path.startswith(real_upload + os.sep):
        raise ValidationError(
            "Execution is restricted to files inside the application upload directory."
        )

    # 3. Magic-byte check (ELF / MZ PE / shebang)
    magic = _read_magic(abs_path)
    if not _is_valid_magic(magic):
        raise ValidationError(
            "File does not appear to be a valid executable "
            "(expected ELF, PE/MZ, or shebang header)."
        )

    # 4. Executable permission on POSIX
    if platform.system() != "Windows":
        if not os.access(abs_path, os.X_OK):
            # Attempt to fix permissions automatically
            try:
                current = os.stat(abs_path).st_mode
                os.chmod(abs_path, current | stat.S_IXUSR | stat.S_IXGRP)
            except OSError as e:
                raise ValidationError(
                    f"File is not executable and chmod failed: {e}"
                ) from e

    return abs_path
