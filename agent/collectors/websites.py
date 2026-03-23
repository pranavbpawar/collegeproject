"""
NEF Agent — Website Activity & DNS Monitor (v2)
Privacy-safe domain-level tracking. NEVER captures full URLs or page content.

Capture methods (configured by dns_capture_method in config.json):
  "packet"  — Real-time Scapy DNS sniffer (needs CAP_NET_RAW / admin)
  "cache"   — DNS cache snapshot (ipconfig/resolvectl) — safe, no privileges
  "browser" — Browser SQLite history — extracts domain only, drops full URLs

All methods:
  - Extract domain names only
  - Tag with category via categorizer.py
  - Deduplicate: emit domain + category + visit_count, not individual URLs
  - Aggregate over a configurable window (default 5 min)
"""

import logging
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .categorizer import categorize

logger = logging.getLogger(__name__)


# ── Packet-level DNS sniffer (Scapy) ──────────────────────────────────────────

class _DNSPacketSniffer:
    """
    Background thread that sniffs UDP port 53 DNS responses
    and stores unique queried domain names.
    Requires Scapy and elevated privileges (CAP_NET_RAW or admin).
    """

    def __init__(self):
        self._domains: dict[str, int] = defaultdict(int)  # domain → count
        self._lock = threading.Lock()
        self._sniffer = None
        self._available = False

    def start(self) -> bool:
        """Start the async sniffer. Returns True if successful."""
        try:
            from scapy.all import AsyncSniffer, DNS, DNSQR

            def _process(pkt):
                try:
                    if pkt.haslayer(DNSQR) and pkt[DNS].qr == 1:  # DNS response
                        qname = pkt[DNSQR].qname.decode("utf-8", errors="ignore").rstrip(".")
                        if qname and not qname.startswith("_"):  # skip mDNS meta
                            with self._lock:
                                self._domains[qname.lower()] += 1
                except Exception:
                    pass

            self._sniffer = AsyncSniffer(
                filter="udp port 53",
                prn=_process,
                store=False,
            )
            self._sniffer.start()
            self._available = True
            logger.info("[dns] Scapy packet sniffer started")
            return True
        except Exception as e:
            logger.debug(f"[dns] Scapy sniffer unavailable: {e} — using fallback")
            self._available = False
            return False

    def stop(self):
        if self._sniffer and self._available:
            try:
                self._sniffer.stop()
            except Exception:
                pass

    def drain(self) -> dict:
        """Return and clear captured domains."""
        with self._lock:
            domains = dict(self._domains)
            self._domains.clear()
        return domains

    @property
    def is_available(self) -> bool:
        return self._available


# Module-level sniffer instance (started once by start_packet_sniffer())
_sniffer: Optional[_DNSPacketSniffer] = None
_sniffer_lock = threading.Lock()


def start_packet_sniffer() -> bool:
    """Call once during agent startup to start the background DNS sniffer."""
    global _sniffer
    with _sniffer_lock:
        if _sniffer is not None:
            return _sniffer.is_available
        _sniffer = _DNSPacketSniffer()
        return _sniffer.start()


def stop_packet_sniffer():
    global _sniffer
    with _sniffer_lock:
        if _sniffer:
            _sniffer.stop()


# ── DNS cache collection ───────────────────────────────────────────────────────

def _collect_dns_cache_windows() -> dict[str, int]:
    try:
        out = subprocess.check_output(
            ["ipconfig", "/displaydns"], stderr=subprocess.DEVNULL, timeout=10
        ).decode(errors="ignore")
        domains = re.findall(r"Record Name[. ]+: (.+)", out)
        result: dict[str, int] = defaultdict(int)
        for d in domains:
            d = d.strip().rstrip(".").lower()
            if d:
                result[d] += 1
        return dict(result)
    except Exception:
        return {}


def _collect_dns_cache_linux() -> dict[str, int]:
    result: dict[str, int] = defaultdict(int)
    try:
        # journalctl DNS answer lines
        out = subprocess.check_output(
            ["journalctl", "-u", "systemd-resolved", "--since", "5 minutes ago",
             "--no-pager", "-o", "short"],
            stderr=subprocess.DEVNULL, timeout=10
        ).decode(errors="ignore")
        for d in re.findall(r"IN\s+(?:A|AAAA)\s+([a-zA-Z0-9._-]+)", out):
            if d and not d.startswith("_"):
                result[d.lower()] += 1
    except Exception:
        pass
    return dict(result)


def _collect_dns_cache() -> dict[str, int]:
    if platform.system() == "Windows":
        return _collect_dns_cache_windows()
    return _collect_dns_cache_linux()


# ── Browser history collection ─────────────────────────────────────────────────

def _extract_domain(url: str) -> Optional[str]:
    """Extract and return domain from URL. Returns None if parsing fails."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        # Remove port number
        host = host.split(":")[0]
        # Strip leading www.
        if host.startswith("www."):
            host = host[4:]
        return host if host else None
    except Exception:
        return None


def _read_sqlite_history(db_path: Path, query: str, params=()) -> list[str]:
    """Copy and read a locked browser SQLite DB. Returns list of URLs."""
    if not db_path.exists():
        return []
    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.close()
        shutil.copy2(str(db_path), tmp.name)
        conn = sqlite3.connect(tmp.name)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [r[0] for r in rows if r[0]]
    except Exception:
        return []
    finally:
        if tmp:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass


def _collect_browser_domains() -> dict[str, int]:
    """
    Read Chrome + Firefox history. Extract domains only (never full URLs).
    """
    cutoff_dt = datetime.utcnow() - timedelta(hours=1)
    result: dict[str, int] = defaultdict(int)
    home = Path.home()
    system = platform.system()

    # ── Chrome / Chromium ──────────────────────────────────────────────────────
    chrome_bases = []
    if system == "Windows":
        chrome_bases = [
            home / "AppData/Local/Google/Chrome/User Data",
            home / "AppData/Local/Chromium/User Data",
        ]
    elif system == "Linux":
        chrome_bases = [
            home / ".config/google-chrome",
            home / ".config/chromium",
        ]
    elif system == "Darwin":
        chrome_bases = [home / "Library/Application Support/Google/Chrome"]

    chrome_cutoff = int((cutoff_dt - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    chrome_query = (
        "SELECT url FROM urls WHERE last_visit_time > ? ORDER BY last_visit_time DESC LIMIT 200"
    )
    for base in chrome_bases:
        if base.exists():
            for hist_path in base.glob("*/History"):
                for url in _read_sqlite_history(hist_path, chrome_query, (chrome_cutoff,)):
                    domain = _extract_domain(url)
                    if domain:
                        result[domain] += 1

    # ── Firefox ────────────────────────────────────────────────────────────────
    if system == "Windows":
        ff_base = home / "AppData/Roaming/Mozilla/Firefox/Profiles"
    elif system == "Darwin":
        ff_base = home / "Library/Application Support/Firefox/Profiles"
    else:
        ff_base = home / ".mozilla/firefox"

    ff_cutoff_us = cutoff_dt.timestamp() * 1_000_000
    ff_query = (
        "SELECT p.url FROM moz_places p "
        "JOIN moz_historyvisits h ON p.id = h.place_id "
        "WHERE h.visit_date > ? ORDER BY h.visit_date DESC LIMIT 200"
    )
    if ff_base.exists():
        for hist_path in list(ff_base.glob("*.default*/places.sqlite")) + \
                         list(ff_base.glob("*.default/places.sqlite")):
            for url in _read_sqlite_history(hist_path, ff_query, (ff_cutoff_us,)):
                domain = _extract_domain(url)
                if domain:
                    result[domain] += 1

    return dict(result)


# ── Main collect function ──────────────────────────────────────────────────────

def collect(dns_method: str = "cache") -> dict:
    """
    Collect DNS / website activity.

    Args:
        dns_method: "packet" | "cache" | "browser"
                    (read from config; passed in by main.py)

    Returns:
        Event dict of type "dns_activity" with categorized domains.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Gather raw domain counts from selected method
    raw_domains: dict[str, int] = {}

    if dns_method == "packet" and _sniffer and _sniffer.is_available:
        raw_domains = _sniffer.drain()
        if not raw_domains:
            # Sniffer may have nothing yet — supplement with cache
            raw_domains.update(_collect_dns_cache())
        capture_method = "packet"

    elif dns_method == "browser":
        raw_domains = _collect_browser_domains()
        capture_method = "browser"

    else:
        # Default: DNS cache
        raw_domains = _collect_dns_cache()
        raw_domains.update(_collect_browser_domains())  # merge both
        capture_method = "cache"

    # Categorize and build payload
    # Skip internal / mDNS / localhost domains
    _SKIP = re.compile(
        r"(localhost|\.local$|\.internal$|\.arpa$|^[0-9.]+$|^_)"
    )
    categorized = []
    for domain, count in sorted(raw_domains.items(), key=lambda x: -x[1])[:200]:
        if _SKIP.search(domain):
            continue
        cat, score = categorize(domain)
        categorized.append({
            "domain":             domain,
            "category":           cat,
            "productivity_score": score,
            "visits":             count,
        })

    return {
        "type":           "dns_activity",
        "domains":        categorized,
        "domain_count":   len(categorized),
        "capture_method": capture_method,
        "window_minutes": 5,
        "collected_at":   now_iso,
    }
