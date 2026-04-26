"""
TBAPS — One-Command Install Script Endpoints
=============================================
Serves dynamically-generated install scripts that embed the correct
backend URL and employee_id so a single curl/iwr command bootstraps
the KBT client on the employee's machine.

GET /api/v1/install/install.sh?employee_id=<id>    → Linux/macOS bash script
GET /api/v1/install/install.ps1?employee_id=<id>   → Windows PowerShell script

Security:
  - employee_id is validated: must be an active employee with a provisioned KBT token
  - Scripts are served as plain text (not executed server-side)
  - In production the SERVER_URL must be HTTPS; scripts abort if http:// is detected
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/install", tags=["install"])


# ── Validation helper ──────────────────────────────────────────────────────────

async def _validate_employee(employee_id: str, db: AsyncSession) -> dict:
    """
    Ensure the employee exists, is active, and has a KBT token provisioned.
    Returns employee name for embedding in the script.
    """
    result = await db.execute(
        text("""
            SELECT id::text AS id, name, email, status, kbt_token_hash, activation_status
            FROM employees
            WHERE id::text = :id AND deleted_at IS NULL
        """),
        {"id": employee_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if row.status != "active":
        raise HTTPException(status_code=403, detail="Employee account is not active.")
    if not row.kbt_token_hash:
        raise HTTPException(
            status_code=404,
            detail="KBT not provisioned for this employee. Contact your administrator.",
        )
    return {"id": row.id, "name": row.name, "email": row.email,
            "activation_status": row.activation_status}


# ── Linux / macOS install script ───────────────────────────────────────────────

@router.get("/install.sh", response_class=PlainTextResponse)
async def install_sh(
    employee_id: str = Query(..., description="Employee UUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Serve a bash install script for Linux/macOS.

    Usage (sent in onboarding email):
        curl -s https://<server>/api/v1/install/install.sh?employee_id=<id> | bash
    """
    emp = await _validate_employee(employee_id, db)

    server_url = settings.SERVER_URL.rstrip("/")
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    name_safe = emp["name"].replace("'", "")
    already_activated = emp["activation_status"] == "activated"

    script = f"""#!/usr/bin/env bash
# ============================================================
# TBAPS / Pragyantri — KBT Client Installer
# Employee: {name_safe} ({emp['email']})
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# ============================================================
set -euo pipefail

SERVER_URL="{server_url}"
EMPLOYEE_ID="{employee_id}"
FRONTEND_URL="{frontend_url}"
INSTALL_DIR="$HOME/.tbaps"
KBT_BIN="$INSTALL_DIR/kbt"
SYSTEMD_SERVICE="$HOME/.config/systemd/user/kbt.service"

# ── Colours ────────────────────────────────────────────────
RED='\\033[0;31m'; GREEN='\\033[0;32m'; YELLOW='\\033[1;33m'
CYAN='\\033[0;36m'; BOLD='\\033[1m'; NC='\\033[0m'

info()    {{ echo -e "${{CYAN}}[TBAPS]${{NC}} $*"; }}
success() {{ echo -e "${{GREEN}}[✓]${{NC}} $*"; }}
warn()    {{ echo -e "${{YELLOW}}[!]${{NC}} $*"; }}
die()     {{ echo -e "${{RED}}[✗]${{NC}} $*"; exit 1; }}

# ── Safety check (HTTPS in production, LAN IPs allowed) ───────────────────
if [[ "$SERVER_URL" == http://* && "$SERVER_URL" != *"localhost"* && "$SERVER_URL" != *"127.0.0.1"* && "$SERVER_URL" != *"192.168."* && "$SERVER_URL" != *"10."* ]]; then
    die "Aborting: SERVER_URL must use HTTPS in production. Got: $SERVER_URL"
fi

echo ""
echo -e "${{BOLD}}╔══════════════════════════════════════════════════════╗${{NC}}"
echo -e "${{BOLD}}║     TBAPS / Pragyantri — KBT Client Installer        ║${{NC}}"
echo -e "${{BOLD}}╚══════════════════════════════════════════════════════╝${{NC}}"
echo ""
info "Installing for: {name_safe}"
info "Server:         $SERVER_URL"
info "Install path:   $KBT_BIN"
echo ""

# ── Step 1: Create install directory ──────────────────────
mkdir -p "$INSTALL_DIR"
success "Created install directory: $INSTALL_DIR"

# ── Step 2: Download KBT identity bundle ──────────────────
info "Downloading your KBT identity bundle..."
BUNDLE_FILE="$INSTALL_DIR/kbt_identity.json"

# Get a fresh signed download URL from the server
BUNDLE_RESP=$(curl -sf --max-time 30 \\
    "$SERVER_URL/api/v1/kbt/download/$EMPLOYEE_ID" 2>&1) || true

# Try to parse the download URL from the onboarding info
if echo "$BUNDLE_RESP" | grep -q "kbt_provisioned"; then
    success "KBT identity confirmed as provisioned."
else
    warn "Could not reach identity bundle (expected if binary pre-packaged). Continuing..."
fi

# ── Step 3: Download the KBT binary ───────────────────────
info "Downloading KBT binary..."
KBT_DL_URL="$SERVER_URL/api/v1/kbt/binary/$EMPLOYEE_ID"

HTTP_CODE=$(curl -sf --max-time 120 -w "%{{http_code}}" \\
    -o "$KBT_BIN.tmp" \\
    "$KBT_DL_URL" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    mv "$KBT_BIN.tmp" "$KBT_BIN"
    chmod +x "$KBT_BIN"
    success "KBT binary downloaded and saved to $KBT_BIN"
elif [[ -f "$KBT_BIN" ]]; then
    warn "Binary server unavailable (HTTP $HTTP_CODE). Using existing binary at $KBT_BIN."
    rm -f "$KBT_BIN.tmp"
else
    rm -f "$KBT_BIN.tmp"
    die "Failed to download KBT binary (HTTP $HTTP_CODE). Please contact your administrator."
fi

# ── Step 4: Write config file ──────────────────────────────
CONFIG_FILE="$INSTALL_DIR/kbt_config.json"
cat > "$CONFIG_FILE" <<CFGEOF
{{
  "employee_id": "$EMPLOYEE_ID",
  "server_url": "$SERVER_URL",
  "portal_url": "$FRONTEND_URL/employee",
  "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}}
CFGEOF
success "Config written to $CONFIG_FILE"

# ── Step 5: (Optional) Install as systemd user service ────
if command -v systemctl &>/dev/null && systemctl --user status &>/dev/null 2>&1; then
    mkdir -p "$(dirname "$SYSTEMD_SERVICE")"
    cat > "$SYSTEMD_SERVICE" <<SVCEOF
[Unit]
Description=TBAPS KBT Agent
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=$KBT_BIN --employee-id $EMPLOYEE_ID --config $CONFIG_FILE
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=TBAPS_SERVER=$SERVER_URL

[Install]
WantedBy=default.target
SVCEOF
    systemctl --user daemon-reload
    systemctl --user enable kbt.service 2>/dev/null || true
    success "Systemd user service installed (auto-starts on login)"
fi

# ── Step 6: Run KBT ───────────────────────────────────────
echo ""
info "Starting KBT Agent..."
echo ""

{"" if already_activated else '''# First-time activation required
warn "This is your first run. You will be prompted for your ACTIVATION CODE."
warn "Check your onboarding email for the 6-character code."
echo ""'''}

"$KBT_BIN" --employee-id "$EMPLOYEE_ID" --config "$CONFIG_FILE" {"--background" if already_activated else "--activate"}

echo ""
success "KBT Agent is running!"
echo ""
echo -e "${{CYAN}}Your web portal:${{NC}} $FRONTEND_URL/employee"
echo -e "${{CYAN}}To stop KBT:${{NC}}   systemctl --user stop kbt"
echo -e "${{CYAN}}To view logs:${{NC}}  journalctl --user -u kbt -f"
echo ""
"""
    logger.info(f"[install] Served install.sh for employee: {employee_id}")
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8",
                              headers={"Content-Disposition": "inline; filename=install.sh"})


# ── Windows / PowerShell install script ───────────────────────────────────────

@router.get("/install.ps1", response_class=PlainTextResponse)
async def install_ps1(
    employee_id: str = Query(..., description="Employee UUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Serve a PowerShell install script for Windows.

    Usage (sent in onboarding email):
        iwr -useb https://<server>/api/v1/install/install.ps1?employee_id=<id> | iex
    """
    emp = await _validate_employee(employee_id, db)

    server_url = settings.SERVER_URL.rstrip("/")
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    name_safe = emp["name"].replace("'", "")
    already_activated = emp["activation_status"] == "activated"

    script = f"""# ============================================================
# TBAPS / Pragyantri — KBT Client Installer (Windows)
# Employee: {name_safe} ({emp['email']})
# ============================================================
$ErrorActionPreference = "Stop"

$ServerUrl   = "{server_url}"
$EmployeeId  = "{employee_id}"
$FrontendUrl = "{frontend_url}"
$InstallDir  = "$env:APPDATA\\TBAPS"
$KbtBin      = "$InstallDir\\kbt.exe"
$ConfigFile  = "$InstallDir\\kbt_config.json"

function Write-Info    {{ param($m) Write-Host "[TBAPS] $m" -ForegroundColor Cyan }}
function Write-Success {{ param($m) Write-Host "[✓] $m"    -ForegroundColor Green }}
function Write-Warn    {{ param($m) Write-Host "[!] $m"    -ForegroundColor Yellow }}

# HTTPS safety check
if ($ServerUrl -notmatch "^https://" -and $ServerUrl -notmatch "localhost" -and $ServerUrl -notmatch "127.0.0.1") {{
    Write-Error "Aborting: SERVER_URL must use HTTPS in production."
    exit 1
}}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║     TBAPS / Pragyantri — KBT Client Installer        ║" -ForegroundColor Blue
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Blue
Write-Host ""
Write-Info "Installing for: {name_safe}"
Write-Info "Server:         $ServerUrl"
Write-Info "Install path:   $KbtBin"
Write-Host ""

# Step 1: Create install directory
if (-not (Test-Path $InstallDir)) {{
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}}
Write-Success "Install directory ready: $InstallDir"

# Step 2: Download KBT binary
Write-Info "Downloading KBT binary..."
$KbtDlUrl  = "$ServerUrl/api/v1/kbt/binary/$EmployeeId"

try {{
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($KbtDlUrl, "$KbtBin.tmp")
    Move-Item -Force "$KbtBin.tmp" $KbtBin
    Write-Success "KBT binary downloaded to $KbtBin"
}} catch {{
    if (Test-Path $KbtBin) {{
        Write-Warn "Binary server unavailable. Using existing binary."
    }} else {{
        Write-Error "Failed to download KBT binary. Contact your administrator."
        exit 1
    }}
}}

# Step 3: Write config file
$config = @{{
    employee_id  = $EmployeeId
    server_url   = $ServerUrl
    portal_url   = "$FrontendUrl/employee"
    installed_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}} | ConvertTo-Json
$config | Out-File -Encoding utf8 $ConfigFile
Write-Success "Config written to $ConfigFile"

# Step 4: Register as a scheduled task (auto-start on login)
$Action   = New-ScheduledTaskAction -Execute $KbtBin -Argument "--employee-id $EmployeeId --config `"$ConfigFile`""
$Trigger  = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
try {{
    Register-ScheduledTask -TaskName "TBAPS-KBT" -Action $Action -Trigger $Trigger `
        -Settings $Settings -RunLevel Highest -Force | Out-Null
    Write-Success "Scheduled task registered (auto-starts on login)"
}} catch {{
    Write-Warn "Could not register scheduled task (requires elevated permissions). Run manually if needed."
}}

# Step 5: Start KBT
Write-Host ""
Write-Info "Starting KBT Agent..."
Write-Host ""

{"" if already_activated else '''Write-Warn "First run: you will be prompted for your ACTIVATION CODE."
Write-Warn "Check your onboarding email for the 6-character code."
Write-Host ""'''}

$kbtArgs = "--employee-id $EmployeeId --config `"$ConfigFile`" {"--background" if already_activated else "--activate"}"
Start-Process -FilePath $KbtBin -ArgumentList $kbtArgs -NoNewWindow

Write-Host ""
Write-Success "KBT Agent is running!"
Write-Host ""
Write-Host "Your web portal: $FrontendUrl/employee" -ForegroundColor Cyan
Write-Host "To stop KBT:     Stop-ScheduledTask -TaskName TBAPS-KBT" -ForegroundColor Cyan
Write-Host ""
"""
    logger.info(f"[install] Served install.ps1 for employee: {employee_id}")
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8",
                              headers={"Content-Disposition": "inline; filename=install.ps1"})
