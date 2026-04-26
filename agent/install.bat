@echo off
REM ============================================================================
REM  NEF Agent — Windows VM One-Click Installer
REM  Run as Administrator for best results.
REM  Usage: install.bat [SERVER_URL]
REM  Example: install.bat http://192.168.1.100:8000
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   NEF Agent Installer — TBAPS Monitoring System  ║
echo  ╚══════════════════════════════════════════════════╝
echo.

REM ── 1. Determine Server URL ────────────────────────────────────────────────
set PRODUCTION_URL=https://tbaps-backend.onrender.com

if "%~1"=="" (
    set /p SERVER_URL="Enter the TBAPS backend URL [default: https://tbaps-backend.onrender.com]: "
    if "!SERVER_URL!"=="" set SERVER_URL=!PRODUCTION_URL!
) else (
    set SERVER_URL=%~1
)

if "!SERVER_URL!"=="" (
    echo [ERROR] Server URL is required. Exiting.
    pause
    exit /b 1
)

echo [KBT] Server URL: !SERVER_URL!
echo.

REM ── 2. Verify Python is available ─────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [NEF] Python found.

REM ── 3. Install Python dependencies ────────────────────────────────────────
echo [NEF] Installing Python dependencies...
pip install psutil Pillow watchdog requests pynput --quiet
if errorlevel 1 (
    echo [WARN] pip install had warnings (may be OK if packages already installed)
)

REM ── 4. Write initial config.json ──────────────────────────────────────────
set CONFIG_DIR=%USERPROFILE%\.nef
if not exist "!CONFIG_DIR!" mkdir "!CONFIG_DIR!"

set CONFIG_FILE=!CONFIG_DIR!\config.json

echo [NEF] Writing config to !CONFIG_FILE!

REM Write config using Python to avoid JSON encoding issues
python -c "import json,os; cfg={'server_url':'!SERVER_URL!','upload_interval':10,'heartbeat_interval':60,'screenshot_interval':300,'collect_screenshots':True,'collect_files':True,'collect_usb':True,'collect_input_metrics':True,'dns_capture_method':'cache','max_buffer_events':10000,'batch_size':50,'enable_tray_icon':True}; os.makedirs(os.path.expanduser('~/.nef'),exist_ok=True); open(os.path.expanduser('~/.nef/config.json'),'w').write(json.dumps(cfg,indent=2)); print('[NEF] Config written.')"

REM ── 5. Get the script's directory (agent root) ─────────────────────────────
set AGENT_DIR=%~dp0
if "%AGENT_DIR:~-1%"=="\" set AGENT_DIR=%AGENT_DIR:~0,-1%

echo [NEF] Agent directory: !AGENT_DIR!

REM ── 6. Register the agent with the server ─────────────────────────────────
echo [NEF] Registering with server (requires network connection)...
python "!AGENT_DIR!\main.py" --server "!SERVER_URL!" --install
if errorlevel 1 (
    echo [WARN] Registration failed — agent will retry on startup.
    echo        Make sure the backend at !SERVER_URL! is reachable.
)

REM ── 7. Create Windows Task Scheduler entry for autostart ──────────────────
echo [NEF] Creating Windows Task Scheduler entry...
schtasks /create /tn "NEF Monitoring Agent" ^
    /tr "python \"!AGENT_DIR!\main.py\"" ^
    /sc ONLOGON ^
    /rl HIGHEST ^
    /f >nul 2>&1

if errorlevel 1 (
    echo [WARN] Task Scheduler entry failed (may need Administrator rights)
    echo        The agent will NOT autostart. Run manually: python main.py
) else (
    echo [NEF] Task Scheduler entry created — agent will start on next login.
)

REM ── 8. Start the agent now ──────────────────────────────────────────────────
echo [NEF] Starting agent in background...
start "NEF Agent" /B python "!AGENT_DIR!\main.py"
ping -n 3 127.0.0.1 >nul 2>&1

echo.
echo  ✅ NEF Agent installed and started!
echo.
echo     Server:  !SERVER_URL!
echo     Logs:    %USERPROFILE%\.nef\agent.log
echo     Status:  python main.py --status
echo.
echo     The agent will appear in the TBAPS dashboard automatically.
echo.
pause
endlocal
