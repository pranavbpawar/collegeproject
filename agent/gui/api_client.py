"""
NEF Agent — API Client
Thin HTTP wrapper used by the GUI to communicate with the TBAPS backend.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Storage for JWT token (in-memory only, never written to disk in plaintext)
_session_token: Optional[str] = None
_server_url:    str = ""
_employee_id:   Optional[str] = None
_employee_name: Optional[str] = None


def configure(server_url: str):
    global _server_url
    _server_url = server_url.rstrip("/")


def get_employee_id() -> Optional[str]:
    return _employee_id


def get_employee_name() -> Optional[str]:
    return _employee_name


def _headers() -> dict:
    if _session_token:
        return {"Authorization": f"Bearer {_session_token}"}
    return {}


def _url(path: str) -> str:
    return f"{_server_url}/api/v1{path}"


# ── Auth ───────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict:
    """
    Authenticate the employee. Returns the full response dict on success.
    Raises requests.HTTPError on failure.
    """
    global _session_token, _employee_id, _employee_name

    resp = requests.post(
        _url("/employee/login"),
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _session_token  = data["access_token"]
    _employee_id    = data["employee_id"]
    _employee_name  = data.get("name", "Employee")
    return data


def logout():
    global _session_token, _employee_id, _employee_name
    _session_token = None
    _employee_id   = None
    _employee_name = None


def me() -> dict:
    resp = requests.get(_url("/employee/me"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── Chat ───────────────────────────────────────────────────────────────────────

def list_conversations() -> list:
    resp = requests.get(_url("/chat/conversations"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_messages(conv_id: str, limit: int = 50) -> list:
    resp = requests.get(
        _url(f"/chat/{conv_id}/messages"),
        params={"limit": limit},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def send_message(conv_id: str, content: str) -> dict:
    resp = requests.post(
        _url(f"/chat/{conv_id}/messages"),
        json={"content": content},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def upload_file(conv_id: str, file_path: str) -> dict:
    """Upload a file into a conversation."""
    path = Path(file_path)
    with open(path, "rb") as f:
        content = f.read()

    files = {
        "file": (path.name, content),
    }
    data = {"conversation_id": conv_id}
    resp = requests.post(
        _url("/chat/upload"),
        files=files,
        data=data,
        headers=_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def get_download_token(file_id: str) -> dict:
    resp = requests.get(
        _url(f"/chat/file/{file_id}/token"),
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def download_file(file_id: str, user_id: str, token: str, save_path: str) -> None:
    """Download a file to save_path."""
    resp = requests.get(
        _url(f"/chat/file/{file_id}"),
        params={"token": token, "user_id": user_id},
        headers=_headers(),
        timeout=60,
        stream=True,
    )
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


# ── Work Sessions ──────────────────────────────────────────────────────────────

def clock_in(notes: str = "") -> dict:
    resp = requests.post(
        _url("/work/clock-in"),
        json={"notes": notes},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def clock_out(notes: str = "") -> dict:
    resp = requests.post(
        _url("/work/clock-out"),
        json={"notes": notes},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def my_sessions(limit: int = 30) -> list:
    resp = requests.get(
        _url("/work/my-sessions"),
        params={"limit": limit},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def my_summary() -> dict:
    resp = requests.get(_url("/work/my-summary"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()
