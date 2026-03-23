"""
NEF Agent — Backend API Routes
Handles agent registration, heartbeat, event upload, admin queries,
and agent package generation (download pre-configured agent zip).
"""

import base64
import io
import json
import os
import secrets
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


# ── Request / Response Models ──────────────────────────────────────────────────

class AgentRegisterRequest(BaseModel):
    hostname:    str
    username:    Optional[str] = None
    os:          Optional[str] = None
    os_version:  Optional[str] = None
    ip_address:  Optional[str] = None
    mac_address: Optional[str] = None


class AgentHeartbeatRequest(BaseModel):
    agent_id:  str
    timestamp: Optional[str] = None


class AgentEventsRequest(BaseModel):
    agent_id: str
    events:   list
    sent_at:  Optional[str] = None


class AgentPackageRequest(BaseModel):
    employee_name: str
    os_target:     str = "linux"   # "linux", "windows", or "both"


# ── Auth helper ────────────────────────────────────────────────────────────────

async def get_agent(
    db: AsyncSession,
    x_agent_id: str,
    x_api_key: str,
) -> dict:
    result = await db.execute(
        text("SELECT id, api_key FROM agent_machines WHERE id = :id"),
        {"id": x_agent_id}
    )
    row = result.fetchone()
    if not row or row.api_key != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    return {"id": row.id}


# ── Agent Endpoints ────────────────────────────────────────────────────────────

@router.post("/agent/register")
async def register_agent(
    body: AgentRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """First-time registration. Returns agent_id + api_key."""
    api_key = secrets.token_urlsafe(32)

    result = await db.execute(
        text("""
            INSERT INTO agent_machines
                (hostname, username, os, os_version, ip_address, mac_address, api_key, status)
            VALUES
                (:hostname, :username, :os, :os_version, :ip, :mac, :api_key, 'online')
            RETURNING id
        """),
        {
            "hostname":   body.hostname,
            "username":   body.username,
            "os":         body.os,
            "os_version": body.os_version,
            "ip":         body.ip_address,
            "mac":        body.mac_address,
            "api_key":    api_key,
        }
    )
    agent_id = str(result.scalar())
    await db.commit()

    return {"agent_id": agent_id, "api_key": api_key}


@router.post("/agent/heartbeat")
async def heartbeat(
    body: AgentHeartbeatRequest,
    x_agent_id: str = Header(...),
    x_api_key:  str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    await get_agent(db, x_agent_id, x_api_key)
    await db.execute(
        text("UPDATE agent_machines SET last_seen = NOW(), status = 'online' WHERE id = :id"),
        {"id": x_agent_id}
    )
    await db.commit()
    return {"ok": True}


@router.post("/agent/events")
async def receive_events(
    body: AgentEventsRequest,
    x_agent_id: str = Header(...),
    x_api_key:  str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Bulk receive events from an agent."""
    await get_agent(db, x_agent_id, x_api_key)

    inserted = 0
    for event in body.events:
        event_type  = event.get("type", "unknown")
        try:
            collected_at = datetime.fromisoformat(event.get("collected_at")) if event.get("collected_at") else datetime.now(timezone.utc)
        except Exception:
            collected_at = datetime.now(timezone.utc)

        # Screenshots stored separately
        if event_type == "screenshot" and event.get("image_b64"):
            try:
                img_data = base64.b64decode(event["image_b64"])
                await db.execute(
                    text("""
                        INSERT INTO agent_screenshots (agent_id, image_data, width, height, size_bytes, taken_at)
                        VALUES (:agent_id, :img, :w, :h, :sz, :taken_at)
                    """),
                    {
                        "agent_id": x_agent_id,
                        "img":      img_data,
                        "w":        event.get("width"),
                        "h":        event.get("height"),
                        "sz":       event.get("size_bytes"),
                        "taken_at": collected_at,
                    }
                )
            except Exception:
                pass
        else:
            # Strip image data from payload if present to keep events table lean
            clean_event = {k: v for k, v in event.items() if k != "image_b64"}
            await db.execute(
                text("""
                    INSERT INTO agent_events (agent_id, event_type, payload, collected_at)
                    VALUES (:agent_id, :type, CAST(:payload AS jsonb), :collected_at)
                """),
                {
                    "agent_id":     x_agent_id,
                    "type":         event_type,
                    "payload":      json.dumps(clean_event),
                    "collected_at": collected_at,
                }
            )
        inserted += 1

    # Update last_seen
    await db.execute(
        text("UPDATE agent_machines SET last_seen = NOW(), status = 'online' WHERE id = :id"),
        {"id": x_agent_id}
    )
    await db.commit()
    return {"received": inserted}


# ── Agent Package Generator ────────────────────────────────────────────────────

# Find the agent source directory (relative to this file)
_HERE = Path(__file__).resolve()
_AGENT_DIR = _HERE.parents[4] / "agent"   # /opt/tbaps/agent  or  /home/.../MACHINE/agent


@router.post("/agent/generate-package")
async def generate_agent_package(body: AgentPackageRequest):
    """
    Generate a pre-configured agent ZIP for a new employee.
    The zip contains all agent sources + a config.json pre-filled with
    the server URL and employee name. Employee extracts and runs install.sh.
    """
    # Determine the server URL from environment
    server_url = os.environ.get("SERVER_URL", "http://localhost:80")

    # Pre-filled config (no agent_id/api_key yet — those come after first run)
    config = {
        "server_url":          server_url,
        "employee_name":       body.employee_name,
        "screenshot_interval": 300,
        "heartbeat_interval":  60,
        "upload_interval":     120,
        "collect_processes":   True,
        "collect_window":      True,
        "collect_idle":        True,
        "collect_usb":         True,
        "collect_files":       True,
        "collect_websites":    True,
        "collect_screenshots": True,
    }

    # Build install scripts
    install_sh = f"""#!/usr/bin/env bash
# NEF Agent installer for {body.employee_name}
# Generated by TBAPS Admin Dashboard

set -e
echo "[NEF] Installing agent for {body.employee_name}..."

# Install Python deps
pip3 install psutil Pillow watchdog requests --break-system-packages -q 2>/dev/null || \\
pip3 install psutil Pillow watchdog requests -q

# Start the agent (reads config.json automatically)
echo "[NEF] Starting agent..."
nohup python3 main.py > ~/.nef/agent.log 2>&1 &
echo "[NEF] Agent started (PID $!). Check ~/.nef/agent.log for status."
echo "[NEF] It will appear in the dashboard at: {server_url}"
"""

    install_bat = f"""@echo off
REM NEF Agent installer for {body.employee_name}
REM Generated by TBAPS Admin Dashboard

echo [NEF] Installing agent for {body.employee_name}...

REM Install Python deps
pip install psutil Pillow watchdog requests -q

REM Start the agent
echo [NEF] Starting agent...
start /B python main.py
echo [NEF] Agent started. It will appear in the dashboard at: {server_url}
pause
"""

    readme = f"""# NEF Monitoring Agent
Employee: {body.employee_name}
Server:   {server_url}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Quick Start

### Linux / Mac
    bash install.sh

### Windows
    Double-click install.bat
    (or: python main.py)

## Requirements
- Python 3.8+
- Internet access to {server_url}

The agent will appear in the admin dashboard automatically on first run.
"""

    # Build the ZIP in memory
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # 1. config.json (pre-filled)
        zf.writestr("nef-agent/config.json", json.dumps(config, indent=2))

        # 2. Install scripts
        zf.writestr("nef-agent/install.sh",  install_sh)
        zf.writestr("nef-agent/install.bat", install_bat)
        zf.writestr("nef-agent/README.txt",  readme)

        # 3. All agent Python source files
        if _AGENT_DIR.exists():
            for src_file in sorted(_AGENT_DIR.rglob("*.py")):
                # Skip build artefacts
                if any(p in src_file.parts for p in ("__pycache__", "dist", "build")):
                    continue
                rel = src_file.relative_to(_AGENT_DIR)
                zf.write(src_file, f"nef-agent/{rel}")

            # requirements.txt
            req_file = _AGENT_DIR / "requirements.txt"
            if req_file.exists():
                zf.write(req_file, "nef-agent/requirements.txt")
        else:
            # Fallback: embed a minimal main.py stub if source dir not found
            zf.writestr("nef-agent/README.txt",
                readme + "\n\n[!] Agent source not found on server — contact admin.")

    zip_buf.seek(0)
    safe_name = body.employee_name.replace(" ", "_").lower()
    filename  = f"nef-agent-{safe_name}.zip"

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Admin Endpoints ────────────────────────────────────────────────────────────

@router.get("/admin/agents")
async def list_agents(
    db: AsyncSession = Depends(get_db),
):
    """List all registered agents with online/offline status."""
    # Mark agents offline if not seen in last 2 minutes
    await db.execute(text("""
        UPDATE agent_machines
        SET status = 'offline'
        WHERE last_seen < NOW() - INTERVAL '2 minutes' AND status = 'online'
    """))
    await db.commit()

    result = await db.execute(text("""
        SELECT id, hostname, username, os, ip_address, mac_address,
               status, first_seen, last_seen
        FROM agent_machines
        ORDER BY last_seen DESC
    """))
    rows = result.fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/admin/agents/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return agent detail + latest event of each type."""
    result = await db.execute(
        text("SELECT * FROM agent_machines WHERE id = :id"),
        {"id": agent_id}
    )
    agent = result.fetchone()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Latest event per type
    events_result = await db.execute(
        text("""
            SELECT DISTINCT ON (event_type)
                   id, event_type, payload, collected_at, received_at
            FROM agent_events
            WHERE agent_id = :id
            ORDER BY event_type, received_at DESC
        """),
        {"id": agent_id}
    )
    events = {r.event_type: dict(r._mapping) for r in events_result.fetchall()}

    return {
        "agent": dict(agent._mapping),
        "latest_events": events,
    }


@router.get("/admin/agents/{agent_id}/screenshots")
async def get_screenshots(
    agent_id: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return screenshot timeline for an agent (URLs, not raw data)."""
    result = await db.execute(
        text("""
            SELECT id, width, height, size_bytes, taken_at
            FROM agent_screenshots
            WHERE agent_id = :id
            ORDER BY taken_at DESC
            LIMIT :limit
        """),
        {"id": agent_id, "limit": limit}
    )
    rows = result.fetchall()
    return [
        {**dict(r._mapping), "url": f"/api/v1/admin/screenshots/{r.id}"}
        for r in rows
    ]


@router.get("/admin/screenshots/{screenshot_id}")
async def serve_screenshot(
    screenshot_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Serve a raw screenshot image."""
    result = await db.execute(
        text("SELECT image_data FROM agent_screenshots WHERE id = :id"),
        {"id": screenshot_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return Response(content=bytes(row.image_data), media_type="image/jpeg")


@router.get("/admin/events")
async def list_events(
    agent_id:   Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    limit:      int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Filterable event feed across all agents."""
    filters = []
    params: dict = {"limit": limit}
    if agent_id:
        filters.append("agent_id = :agent_id")
        params["agent_id"] = agent_id
    if event_type:
        filters.append("event_type = :event_type")
        params["event_type"] = event_type

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    result = await db.execute(
        text(f"""
            SELECT e.id, e.agent_id, m.hostname, e.event_type,
                   e.payload, e.collected_at, e.received_at
            FROM agent_events e
            JOIN agent_machines m ON e.agent_id = m.id
            {where}
            ORDER BY e.received_at DESC
            LIMIT :limit
        """),
        params
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── Agent Installer Package Endpoints ─────────────────────────────────────────

class InstallerRequest(BaseModel):
    employee_name: str
    server_url:    str = ""   # defaults to auto-detected from request


from fastapi import Request

@router.post("/agent/download-deb")
async def download_deb(body: InstallerRequest, request: Request):
    """
    Build and download a .deb installer for Linux/Ubuntu/Debian employees.
    Employee just runs:  sudo dpkg -i nef-agent-<name>.deb
    """
    from app.services.package_builder import build_deb

    server_url = body.server_url or str(request.base_url).rstrip("/")
    safe_name = body.employee_name.lower().replace(" ", "-").replace("_", "-")

    try:
        deb_bytes = build_deb(
            employee_name=body.employee_name,
            server_url=server_url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build .deb: {e}")

    return Response(
        content=deb_bytes,
        media_type="application/vnd.debian.binary-package",
        headers={
            "Content-Disposition": f'attachment; filename="nef-agent-{safe_name}.deb"',
            "Content-Length": str(len(deb_bytes)),
        },
    )

@router.get("/agent/download-deb")
async def download_deb_get(
    request: Request,
    employee_name: str = Query(...), 
    server_url: str = Query(default="")
):
    """GET wrapper for direct email links."""
    return await download_deb(InstallerRequest(employee_name=employee_name, server_url=server_url), request)


@router.post("/agent/download-exe")
async def download_exe(body: InstallerRequest, request: Request):
    """
    Build and download a real Windows .exe installer via NSIS (makensis).
    The .exe installs silently — employees just double-click it.
    No Python or technical knowledge needed.
    """
    server_url = body.server_url or str(request.base_url).rstrip("/")
    safe_name  = body.employee_name.lower().replace(" ", "-").replace("_", "-")

    try:
        from app.services.nsis_builder import build_windows_exe
        exe_bytes = build_windows_exe(
            employee_name=body.employee_name,
            server_url=server_url,
        )
        return Response(
            content=exe_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="nef-agent-{safe_name}.exe"',
                "Content-Length": str(len(exe_bytes)),
            },
        )
    except Exception as e:
        # Fallback: ZIP with install.bat
        try:
            from app.services.package_builder import build_exe_zip
            zip_bytes = build_exe_zip(
                employee_name=body.employee_name,
                server_url=server_url,
            )
            return Response(
                content=zip_bytes,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="nef-agent-{safe_name}-windows.zip"',
                    "Content-Length": str(len(zip_bytes)),
                },
            )
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to build Windows package: {e} | Fallback error: {e2}"
            )

@router.get("/agent/download-exe")
async def download_exe_get(
    request: Request,
    employee_name: str = Query(...), 
    server_url: str = Query(default="")
):
    """GET wrapper for direct email links."""
    return await download_exe(InstallerRequest(employee_name=employee_name, server_url=server_url), request)


# ── SHA256 Integrity Check Endpoints ──────────────────────────────────────────

import hashlib

@router.get("/agent/checksum-deb")
async def checksum_deb(
    request: Request,
    employee_name: str = Query(..., description="Employee name embedded in the package"),
    server_url: str = Query(default="", description="Server URL embedded in the package"),
):
    """
    Build a .deb package and return its SHA256 hash.
    Callers can verify a downloaded file with:
      sha256sum nef-agent.deb
    """
    from app.services.package_builder import build_deb
    try:
        resolved_url = server_url or str(request.base_url).rstrip("/")
        deb_bytes = build_deb(employee_name=employee_name, server_url=resolved_url)
        sha256 = hashlib.sha256(deb_bytes).hexdigest()
        safe_name = employee_name.lower().replace(" ", "-").replace("_", "-")
        return {
            "filename":     f"nef-agent-{safe_name}.deb",
            "sha256":       sha256,
            "size_bytes":   len(deb_bytes),
            "version":      "1.0.0",
            "employee":     employee_name,
            "server_url":   resolved_url,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not build .deb for checksum: {e}")


@router.get("/agent/checksum-exe")
async def checksum_exe(
    request: Request,
    employee_name: str = Query(..., description="Employee name embedded in the package"),
    server_url: str = Query(default="", description="Server URL embedded in the package"),
):
    """
    Build a Windows .exe installer and return its SHA256 hash.
    Callers verify with:  Get-FileHash nef-agent.exe -Algorithm SHA256
    """
    resolved_url = server_url or str(request.base_url).rstrip("/")
    safe_name = employee_name.lower().replace(" ", "-").replace("_", "-")
    try:
        from app.services.nsis_builder import build_windows_exe
        exe_bytes = build_windows_exe(employee_name=employee_name, server_url=resolved_url)
    except Exception:
        try:
            from app.services.package_builder import build_exe_zip
            exe_bytes = build_exe_zip(employee_name=employee_name, server_url=resolved_url)
            safe_name += "-windows-zip"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not build .exe for checksum: {e}")

    sha256 = hashlib.sha256(exe_bytes).hexdigest()
    return {
        "filename":   f"nef-agent-{safe_name}.exe",
        "sha256":     sha256,
        "size_bytes": len(exe_bytes),
        "version":    "1.0.0",
        "employee":   employee_name,
        "server_url": resolved_url,
    }
