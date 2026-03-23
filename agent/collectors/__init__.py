"""NEF Agent collectors package."""
# Original collectors
from . import sysinfo, processes, idle, usb, screenshot, files

# Enhanced collectors (v2)
from . import window       # app session duration tracking
from . import input_metrics  # keyboard/mouse rate (privacy-safe)
from . import websites     # DNS packet capture + categorisation

# Standalone domain categorizer (no DB required)
from . import categorizer
