"""
Gunicorn configuration for TBAPS production deployment.
Run with: gunicorn app.main:app -c gunicorn.conf.py
"""

import multiprocessing
import os

# ── Server socket ──────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"
backlog = 2048

# ── Worker processes ───────────────────────────────────────────────────────────
# Use uvicorn workers for ASGI (FastAPI)
worker_class = "uvicorn.workers.UvicornWorker"
# (2 * CPU cores) + 1 is the recommended formula for I/O-bound apps
workers = (multiprocessing.cpu_count() * 2) + 1
threads = 1          # uvicorn workers are single-threaded
worker_connections = 1000

# ── Timeouts ───────────────────────────────────────────────────────────────────
timeout = 60          # Worker silent for >60s is killed and restarted
graceful_timeout = 30 # Time to finish in-flight requests on SIGTERM
keepalive = 5         # Keep-alive connections

# ── Logging ────────────────────────────────────────────────────────────────────
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "/var/log/tbaps/access.log"
errorlog  = "/var/log/tbaps/error.log"
access_log_format = (
    '{"time":"%(t)s","remote_ip":"%(h)s","method":"%(m)s",'
    '"path":"%(U)s","status":%(s)s,"bytes":%(b)s,"duration_ms":%(D)s}'
)

# ── Process naming ─────────────────────────────────────────────────────────────
proc_name = "tbaps-api"

# ── Security ───────────────────────────────────────────────────────────────────
limit_request_line   = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# ── Hooks ──────────────────────────────────────────────────────────────────────
def on_starting(server):
    server.log.info("TBAPS API starting up")

def on_exit(server):
    server.log.info("TBAPS API shutting down")

def worker_exit(server, worker):
    server.log.info(f"Worker {worker.pid} exited")
