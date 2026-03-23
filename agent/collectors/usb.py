"""
NEF Agent — USB Device Collector
Detects connected USB devices.
Windows: WMI / Linux: /sys/bus/usb/devices
"""

import platform
import os
from datetime import datetime


def _collect_linux() -> list:
    devices = []
    usb_path = "/sys/bus/usb/devices"
    if not os.path.exists(usb_path):
        return devices
    for dev in os.listdir(usb_path):
        dev_path = os.path.join(usb_path, dev)
        def read(attr):
            try:
                with open(os.path.join(dev_path, attr)) as f:
                    return f.read().strip()
            except Exception:
                return None
        product  = read("product")
        manufacturer = read("manufacturer")
        id_vendor  = read("idVendor")
        id_product = read("idProduct")
        if product or manufacturer:
            devices.append({
                "device": dev,
                "product":      product,
                "manufacturer": manufacturer,
                "vendor_id":    id_vendor,
                "product_id":   id_product,
            })
    return devices


def _collect_windows() -> list:
    devices = []
    try:
        import wmi
        c = wmi.WMI()
        for usb in c.Win32_USBControllerDevice():
            try:
                dep = usb.Dependent
                devices.append({
                    "device":       dep.DeviceID,
                    "product":      dep.Name,
                    "manufacturer": dep.Manufacturer,
                    "vendor_id":    None,
                    "product_id":   None,
                })
            except Exception:
                continue
    except Exception:
        pass
    return devices


def collect() -> dict:
    system = platform.system()
    devices = _collect_windows() if system == "Windows" else _collect_linux()
    return {
        "type": "usb_devices",
        "devices": devices,
        "count": len(devices),
        "collected_at": datetime.utcnow().isoformat(),
    }
