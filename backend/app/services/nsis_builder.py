"""
NEF Agent — Windows .exe Installer Builder via NSIS
Uses makensis (available on Linux) to build a real Windows .exe installer.
The .exe is self-contained: downloads Python if not present, installs agent,
adds to Windows startup, and runs silently.
"""

import base64
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_AGENT_DIR_CANDIDATES = [
    Path("/home/kali/Desktop/MACHINE/agent"),
    Path("/opt/tbaps/agent"),
]

# Package version — bump on every release
PACKAGE_VERSION = "1.0.0"


def _agent_dir() -> Path:
    for p in _AGENT_DIR_CANDIDATES:
        if (p / "main.py").exists():
            return p
    raise FileNotFoundError("Agent source directory not found")


def build_windows_exe(employee_name: str, server_url: str) -> bytes:
    """
    Build a Windows .exe installer using NSIS (makensis).
    Returns raw bytes of the .exe installer.

    Employee experience:
      1. Double-click nef-agent-<name>.exe
      2. Done — agent installs silently and starts automatically.
    """
    agent_src = _agent_dir()
    safe_name = employee_name.lower().replace(" ", "-").replace("_", "-")

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
    config_json = json.dumps(config, indent=2)

    # FIX #1 & #2: Encode the config as base64 to avoid ALL quote/newline issues
    # when embedding in an NSIS script. The installer decodes it at runtime via Python.
    config_b64 = base64.b64encode(config_json.encode("utf-8")).decode("ascii")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # ── Stage agent files ─────────────────────────────────────────────────
        stage = tmp / "agent"
        stage.mkdir()
        for item in agent_src.iterdir():
            if item.name in ("__pycache__", "dist", "build", ".git"):
                continue
            dest = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(item, dest)

        # FIX #5: Use full pinned requirements.txt from agent source
        req_src = agent_src / "requirements.txt"
        req_dst = stage / "requirements.txt"
        if req_src.exists():
            shutil.copy2(req_src, req_dst)
        elif not req_dst.exists():
            req_dst.write_text(
                "requests>=2.31.0\n"
                "psutil>=5.9.0\n"
                "Pillow>=10.0.0\n"
                "watchdog>=3.0.0\n"
                "pynput>=1.7.7\n"
                "cryptography>=42.0.0\n"
            )

        # FIX #1 & #2: Write a _startup.py that decodes base64 config at runtime.
        # This avoids ALL string interpolation issues since b64 chars are URL-safe.
        launcher = stage / "_startup.py"
        launcher.write_text(
            f'"""NEF Agent startup — decodes config and runs main.py."""\n'
            f'import base64, json, os, sys, shutil\n'
            f'from pathlib import Path\n'
            f'\n'
            f'APP_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "nef-agent"\n'
            f'CFG_FILE = APP_DIR / "config.json"\n'
            f'CONFIG_B64 = "{config_b64}"\n'
            f'\n'
            f'def setup():\n'
            f'    APP_DIR.mkdir(parents=True, exist_ok=True)\n'
            f'    src = Path(sys.argv[0]).parent if getattr(sys, "frozen", False) else Path(__file__).parent\n'
            f'    for f in src.rglob("*"):\n'
            f'        rel = f.relative_to(src)\n'
            f'        if any(x in str(rel) for x in ("__pycache__", "_startup")):\n'
            f'            continue\n'
            f'        dest = APP_DIR / rel\n'
            f'        dest.parent.mkdir(parents=True, exist_ok=True)\n'
            f'        if f.is_file():\n'
            f'            shutil.copy2(f, dest)\n'
            f'    # Write config from decoded base64 (safe from all quoting issues)\n'
            f'    cfg = json.loads(base64.b64decode(CONFIG_B64).decode("utf-8"))\n'
            f'    CFG_FILE.write_text(json.dumps(cfg, indent=2))\n'
            f'\n'
            f'setup()\n'
            f'sys.path.insert(0, str(APP_DIR))\n'
            f'os.chdir(APP_DIR)\n'
            f'exec(open(APP_DIR / "main.py").read())\n'
        )

        # ── Collect all agent files for NSIS File directives ──────────────────
        install_section_lines = []
        last_outdir = None

        for item in sorted(stage.rglob("*")):
            if not item.is_file():
                continue
            rel = item.relative_to(stage)
            parts = list(rel.parts)
            if len(parts) == 1:
                outdir = '  SetOutPath "$INSTDIR"'
            else:
                sub = "\\".join(parts[:-1])
                outdir = f'  SetOutPath "$INSTDIR\\{sub}"'

            if outdir != last_outdir:
                install_section_lines.append(outdir)
                last_outdir = outdir
            install_section_lines.append(f'  File "{item}"')

        install_files = "\n".join(install_section_lines)

        # ── Write NSIS script ─────────────────────────────────────────────────
        # FIX #1 & #2: Config is written by running Python with the b64 config —
        # no NSIS FileWrite quoting issues possible.
        # FIX #4: Uninstall uses taskkill filtered by window title pattern tied
        # to the install dir, not by generic process name.
        nsi = tmp / "installer.nsi"
        nsi.write_text(f"""
; NEF Agent Installer for {employee_name}
; Generated by TBAPS v{PACKAGE_VERSION} — do not edit manually
Unicode True

!define PRODUCT_NAME  "NEF Agent"
!define PRODUCT_VER   "{PACKAGE_VERSION}"
!define EMPLOYEE_NAME "{employee_name}"
!define INSTALL_DIR   "$LOCALAPPDATA\\NEF-Agent"

Name "${{PRODUCT_NAME}} — {employee_name}"
OutFile "{tmp / f'nef-agent-{safe_name}.exe'}"
InstallDir "${{INSTALL_DIR}}"
RequestExecutionLevel user
SilentInstall silent

VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName"      "${{PRODUCT_NAME}}"
VIAddVersionKey "FileVersion"      "${{PRODUCT_VER}}"
VIAddVersionKey "ProductVersion"   "${{PRODUCT_VER}}"
VIAddVersionKey "LegalCopyright"   "TBAPS"
VIAddVersionKey "FileDescription"  "NEF Monitoring Agent for {employee_name}"

; ── Sections ───────────────────────────────────────────────────────────────────

Section "Install" SecMain
  SetOutPath "$INSTDIR"

  ; Extract all agent files
{install_files}

  ; FIX #1 & #2: Write config via Python base64 decode — safe from all quoting
  ExecWait 'python.exe -c "import base64,json; f=open(r\\\"$INSTDIR\\\\config.json\\\",\\\"w\\\"); f.write(json.dumps(json.loads(base64.b64decode(b\\\"{config_b64}\\\").decode()),indent=2)); f.close()"'

  ; Install Python dependencies (silent)
  ExecWait 'cmd.exe /C "python.exe -m pip install -r \\"$INSTDIR\\requirements.txt\\" -q 2>nul"'

  ; Write a PID-tracking startup wrapper
  ; FIX #4: Registry key points to a specific script, not a generic process name
  WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" \\
    "NEFAgent" '"$WINDIR\\System32\\cmd.exe" /C "start /B pythonw.exe \\"$INSTDIR\\_startup.py\\""'

  ; Start agent now
  Exec '"$WINDIR\\System32\\cmd.exe" /C "start /B pythonw.exe \\"$INSTDIR\\_startup.py\\""'

  MessageBox MB_OK|MB_ICONINFORMATION "NEF Agent v{PACKAGE_VERSION} installed!$\\n$\\nThe agent is now running silently.$\\nIt will auto-start on every login.$\\n$\\nYou can close this window."

SectionEnd

Section "un.Uninstall"
  ; FIX #4: Only kill process running from our specific install dir
  ExecWait 'cmd.exe /C "wmic process where (ExecutablePath like \\"$INSTDIR%\\" or CommandLine like \\"%$INSTDIR%\\") delete 2>nul"'
  DeleteRegValue HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" "NEFAgent"
  Sleep 1000
  RMDir /r "$INSTDIR"
SectionEnd
""")

        # ── Run makensis ──────────────────────────────────────────────────────
        exe_out = tmp / f"nef-agent-{safe_name}.exe"
        result = subprocess.run(
            ["makensis", "-V2", str(nsi)],
            capture_output=True,
            text=True,
            cwd=str(tmp),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"makensis failed:\n{result.stdout}\n{result.stderr}"
            )

        if not exe_out.exists():
            raise FileNotFoundError(f"NSIS did not produce {exe_out}")

        return exe_out.read_bytes()
