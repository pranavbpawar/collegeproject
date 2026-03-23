"""
NEF Agent — Windows Service Wrapper (pywin32)
Allows the agent to run as a proper Windows Service (not just a startup key).

Install:  python service/win_service.py install
Start:    python service/win_service.py start
Remove:   python service/win_service.py remove
"""

import os
import sys
import time
import threading

# Add parent directory to path so we can import agent modules
_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    class NEFWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_         = "NEFAgent"
        _svc_display_name_ = "NEF Monitoring Agent"
        _svc_description_  = (
            "Trust-Based Adaptive Productivity System monitoring agent. "
            "Collects behavioral telemetry and streams to the TBAPS backend."
        )

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._daemon_thread = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            # Signal the agent daemon's shutdown event
            try:
                import main as agent_main
                agent_main._shutdown.set()
            except Exception:
                pass
            win32event.SetEvent(self._stop_event)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            self._run_agent()

        def _run_agent(self):
            """Run the NEF daemon in a thread, wait for stop event."""
            import main as agent_main

            self._daemon_thread = threading.Thread(
                target=agent_main.run_daemon,
                daemon=True,
                name="nef-daemon",
            )
            self._daemon_thread.start()

            # Wait for stop signal
            win32event.WaitForSingleObject(
                self._stop_event, win32event.INFINITE
            )

    if __name__ == "__main__":
        if len(sys.argv) == 1:
            # Running as a service — called by Windows SCM
            servicemanager.Initialize()
            servicemanager.PrepareToHostMultiple()
            servicemanager.StartServiceCtrlDispatcher()
        else:
            # CLI: install / start / stop / remove
            win32serviceutil.HandleCommandLine(NEFWindowsService)

except ImportError:
    # pywin32 not available (e.g. on Linux CI)
    class NEFWindowsService:  # type: ignore
        """Stub — pywin32 not available on this platform."""
        pass

    if __name__ == "__main__":
        print("pywin32 is required for Windows Service support.")
        print("Install with: pip install pywin32")
        sys.exit(1)
