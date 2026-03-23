"""
NEF Agent — .deb and .exe Package Generator
Called by the FastAPI backend to build installer packages on-the-fly.
"""

import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

# Root of the agent source code
_HERE     = Path(__file__).resolve()
_AGENT_DIR = _HERE.parents[4] / "agent"   # /home/kali/Desktop/MACHINE/agent

# Package version — bump on every release
PACKAGE_VERSION = "1.0.0"


def _agent_dir() -> Path:
    """Return agent source dir, checking common locations."""
    candidates = [
        _AGENT_DIR,
        Path("/opt/tbaps/agent"),
        Path("/home/kali/Desktop/MACHINE/agent"),
    ]
    for p in candidates:
        if (p / "main.py").exists():
            return p
    raise FileNotFoundError("Agent source directory not found")


# ── .deb builder ─────────────────────────────────────────────────────────────

def build_deb(employee_name: str, server_url: str) -> bytes:
    """
    Dynamically build a .deb package for the NEF agent.
    Returns raw bytes of the .deb file.

    The package:
      - Installs to /opt/nef-agent/
      - Pre-fills /opt/nef-agent/config.json with server_url + employee_name
      - Creates a systemd service (/etc/systemd/system/nef-agent.service)
      - postinst: enables and starts the service
      - prerm: stops and disables the service

    Employee install:
      sudo dpkg -i nef-agent-<name>.deb
    """
    agent_src = _agent_dir()
    safe_name = employee_name.lower().replace(" ", "-").replace("_", "-")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # ── Package tree structure ───────────────────────────────────────────
        pkg     = tmp / f"nef-agent_{safe_name}"
        debian  = pkg / "DEBIAN"
        opt     = pkg / "opt" / "nef-agent"
        systemd = pkg / "etc" / "systemd" / "system"
        run_dir = pkg / "var" / "run" / "nef-agent"  # PID file location

        for d in [debian, opt, systemd, run_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # ── Copy agent source files ──────────────────────────────────────────
        for item in agent_src.iterdir():
            if item.name in ("__pycache__", "dist", "build", ".git", "*.pyc"):
                continue
            dest = opt / item.name
            if item.is_dir():
                shutil.copytree(item, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(item, dest)

        # ── Pre-filled config.json ───────────────────────────────────────────
        config = {
            "server_url":              server_url.rstrip("/"),
            "employee_name":           employee_name,
            "agent_id":                None,
            "api_key":                 None,
            "screenshot_interval":     300,
            "heartbeat_interval":      60,
            "upload_interval":         30,
            "collect_screenshots":     True,
            "collect_files":           True,
            "collect_browser_history": True,
        }
        (opt / "config.json").write_text(json.dumps(config, indent=2))

        # ── requirements.txt — use full pinned version from agent source ──────
        # FIX #5: Always copy the full pinned requirements.txt from source.
        req_src = agent_src / "requirements.txt"
        req_dst = opt / "requirements.txt"
        if req_src.exists():
            shutil.copy2(req_src, req_dst)
        elif not req_dst.exists():
            # Fallback with pinned versions — never bare package names
            req_dst.write_text(
                "requests>=2.31.0\n"
                "psutil>=5.9.0\n"
                "Pillow>=10.0.0\n"
                "watchdog>=3.0.0\n"
                "pynput>=1.7.7\n"
                "cryptography>=42.0.0\n"
            )

        # ── Launcher script (/usr/local/bin/nef-agent) ───────────────────────
        bin_dir = pkg / "usr" / "local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        launcher = bin_dir / "nef-agent"
        launcher.write_text(
            "#!/bin/bash\nexec python3 /opt/nef-agent/main.py \"$@\"\n"
        )
        launcher.chmod(0o755)

        # ── systemd service ──────────────────────────────────────────────────
        # NOTE: PrivateTmp / ProtectSystem / NoNewPrivileges removed — they cause
        # status=226/NAMESPACE on many Linux kernels (Kali, WSL, containers).
        (systemd / "nef-agent.service").write_text(f"""\
[Unit]
Description=NEF Monitoring Agent ({employee_name})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/nef-agent/main.py
WorkingDirectory=/opt/nef-agent
Restart=on-failure
RestartSec=30
StartLimitIntervalSec=300
StartLimitBurst=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nef-agent
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
""")

        # ── DEBIAN/control ────────────────────────────────────────────────────
        # Calculate installed size
        size_kb = sum(
            f.stat().st_size for f in opt.rglob("*") if f.is_file()
        ) // 1024 or 1

        (debian / "control").write_text(f"""\
Package: nef-agent
Version: {PACKAGE_VERSION}
Architecture: all
Maintainer: TBAPS Admin <admin@tbaps.local>
Installed-Size: {size_kb}
Depends: python3 (>= 3.8), python3-pip
Description: NEF Monitoring Agent for {employee_name}
 Pragyantri employee monitoring agent. Reports system activity
 to the TBAPS server at {server_url}.
""")

        # ── DEBIAN/postinst (runs after install) ─────────────────────────────
        (debian / "postinst").write_text("""\
#!/bin/bash
set -e

NEF_DIR="/opt/nef-agent"
NEF_HOME_CFG="$HOME/.nef/config.json"

echo ""
echo "  NEF Agent — Post-Install Setup"
echo "  ================================"

# Install Python dependencies (non-blocking failure)
echo "  [1/3] Installing Python dependencies..."
pip3 install -r "$NEF_DIR/requirements.txt" -q --break-system-packages 2>/dev/null || \
pip3 install -r "$NEF_DIR/requirements.txt" -q 2>/dev/null || \
echo "  [warn] pip3 install partially failed — agent may still work"

# CRITICAL FIX: Seed ~/.nef/config.json from the pre-filled package config
# so the agent always has server_url even if registration fails.
mkdir -p "$HOME/.nef"
if [ ! -f "$NEF_HOME_CFG" ]; then
    cp "$NEF_DIR/config.json" "$NEF_HOME_CFG"
    echo "  [info] Seeded ~/.nef/config.json from package config"
fi

# Attempt registration with retry (up to 3 attempts, 5s delay)
echo "  [2/3] Registering with TBAPS server..."
SERVER_URL=$(python3 -c "import json; print(json.load(open('$NEF_DIR/config.json'))['server_url'])" 2>/dev/null || echo "")
REGISTERED=0

if [ -n "$SERVER_URL" ]; then
    for attempt in 1 2 3; do
        if python3 "$NEF_DIR/main.py" --server "$SERVER_URL" --install 2>/dev/null; then
            REGISTERED=1
            break
        fi
        echo "  [warn] Registration attempt $attempt/3 failed — retrying in 5s..."
        sleep 5
    done
fi

if [ "$REGISTERED" -eq 0 ]; then
    echo "  [warn] Could not register with server now."
    echo "         The agent will retry automatically when the service starts."
fi

# Enable and start systemd service
echo "  [3/3] Starting NEF Agent service..."
systemctl daemon-reload
systemctl enable nef-agent.service 2>/dev/null || true
systemctl start  nef-agent.service 2>/dev/null || true

echo ""
echo "  ✅ NEF Agent installed successfully!"
echo "     Check status: systemctl status nef-agent"
echo ""

exit 0
""")
        (debian / "postinst").chmod(0o755)

        # ── DEBIAN/prerm (runs before uninstall) ─────────────────────────────
        # FIX #4: Stop service cleanly; do NOT kill by process name (would
        #         kill other Python processes). Systemd handles PID tracking.
        (debian / "prerm").write_text("""\
#!/bin/bash
systemctl stop    nef-agent.service 2>/dev/null || true
systemctl disable nef-agent.service 2>/dev/null || true
exit 0
""")
        (debian / "prerm").chmod(0o755)

        # ── DEBIAN/postrm (cleanup after uninstall) ───────────────────────────
        (debian / "postrm").write_text("""\
#!/bin/bash
if [ "$1" = "purge" ]; then
    rm -rf  /root/.nef  2>/dev/null || true
    # Remove home dir config for all users (best-effort)
    for home in /home/*; do
        rm -rf "$home/.nef" 2>/dev/null || true
    done
fi
exit 0
""")
        (debian / "postrm").chmod(0o755)

        # ── Build .deb ────────────────────────────────────────────────────────
        deb_path = tmp / f"nef-agent_{safe_name}_{PACKAGE_VERSION}_all.deb"
        result = subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(pkg), str(deb_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"dpkg-deb failed: {result.stderr}")

        return deb_path.read_bytes()


# ── Windows .exe package builder ──────────────────────────────────────────────

def build_exe_zip(employee_name: str, server_url: str) -> bytes:
    """
    Build a Windows ZIP package containing:
      - nef-agent.exe  (pre-built PyInstaller binary, if available)
      - config.json    (pre-filled)
      - install.bat    (double-click installer)
      - README.txt
    Returns raw ZIP bytes.
    """
    import zipfile

    agent_src = _agent_dir()
    dist_dir = agent_src / "dist"
    exe_path = dist_dir / "nef-agent.exe"

    config = {
        "server_url":              server_url.rstrip("/"),
        "employee_name":           employee_name,
        "agent_id":                None,
        "api_key":                 None,
        "screenshot_interval":     300,
        "heartbeat_interval":      60,
        "upload_interval":         30,
        "collect_screenshots":     True,
        "collect_files":           True,
        "collect_browser_history": True,
    }

    safe = employee_name.replace(" ", "_")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # config.json
        zf.writestr("config.json", json.dumps(config, indent=2))

        # .exe binary (if pre-built)
        if exe_path.exists():
            zf.write(exe_path, "nef-agent.exe")
            has_exe = True
        else:
            # Include Python source as fallback
            for item in agent_src.rglob("*.py"):
                rel = item.relative_to(agent_src)
                zf.write(item, str(rel))
            has_exe = False

        # install.bat
        if has_exe:
            bat = """\
@echo off
title NEF Agent Installer
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   NEF Agent — Installing...          ║
echo  ╚══════════════════════════════════════╝
echo.

:: Copy config
if not exist "%APPDATA%\\nef" mkdir "%APPDATA%\\nef"
copy /Y config.json "%APPDATA%\\nef\\config.json" >nul

:: Copy exe to ProgramData
if not exist "C:\\ProgramData\\nef-agent" mkdir "C:\\ProgramData\\nef-agent"
copy /Y nef-agent.exe "C:\\ProgramData\\nef-agent\\nef-agent.exe" >nul

:: Add to startup (runs on login)
reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "NEFAgent" /t REG_SZ /d "C:\\ProgramData\\nef-agent\\nef-agent.exe" /f >nul

:: Run now in background — store PID to PID file for clean uninstall
start "" /B "C:\\ProgramData\\nef-agent\\nef-agent.exe"
for /f "tokens=1 delims=," %%a in ('wmic process where "name='nef-agent.exe'" get processid /format:csv 2^>nul ^| findstr /v "ProcessId" ^| findstr /v "^$"') do (
    echo %%a
)

echo  ✅ NEF Agent installed and running!
echo  It will auto-start on login.
echo.
pause
"""
        else:
            bat = """\
@echo off
title NEF Agent Installer
echo.
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Downloading...
    powershell -Command "Start-Process 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -Wait"
)

echo Installing dependencies...
pip install requests>=2.31 psutil>=5.9 Pillow>=10 watchdog>=3 pynput>=1.7 cryptography>=42 -q

echo Copying config...
if not exist "%APPDATA%\\nef" mkdir "%APPDATA%\\nef"
copy /Y config.json "%APPDATA%\\nef\\config.json" >nul

echo Starting agent...
start "" /B pythonw.exe main.py

echo ✅ NEF Agent is running!
pause
"""

        zf.writestr("install.bat", bat)

        # README
        readme = f"""NEF Agent for {employee_name} (v{PACKAGE_VERSION})
==================================
Server: {server_url}

WINDOWS INSTALL:
  1. Extract this ZIP
  2. Double-click install.bat
  3. Done! Agent runs silently in background.

To check it's running:
  Task Manager → Details → look for nef-agent.exe

To uninstall:
  Run uninstall.bat (or remove from Windows startup)
"""
        zf.writestr("README.txt", readme)

        # FIX #4: Uninstall by stopping the registered service/exe path only
        zf.writestr("uninstall.bat", """\
@echo off
taskkill /F /FI "IMAGENAME eq nef-agent.exe" >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "NEFAgent" /f >nul 2>&1
rmdir /S /Q "C:\\ProgramData\\nef-agent" >nul 2>&1
echo NEF Agent uninstalled.
pause
""")

    buf.seek(0)
    return buf.read()
