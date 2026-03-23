"""
TBAPS Celery Application
Async task queue with retry strategy and timeout configuration.
"""

from celery import Celery
from celery.utils.log import get_task_logger
from kombu import Queue, Exchange
import os

from app.core.config import settings

logger = get_task_logger(__name__)

# ── Define exchanges and queues ────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")
trust_exchange   = Exchange("trust", type="direct")
traffic_exchange = Exchange("traffic", type="direct")

QUEUES = (
    Queue("default",            default_exchange, routing_key="default"),
    Queue("trust_calculation",  trust_exchange,   routing_key="trust"),
    Queue("traffic_analysis",   traffic_exchange, routing_key="traffic"),
)

# ── Create Celery app ──────────────────────────────────────────────────────────
celery_app = Celery(
    "tbaps",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.trust_tasks",
        "app.workers.traffic_tasks",
        "app.workers.sync_tasks",
    ],
)

# ── Configuration ──────────────────────────────────────────────────────────────
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Queues
    task_queues=QUEUES,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Task routing
    task_routes={
        "app.workers.trust_tasks.*":   {"queue": "trust_calculation", "routing_key": "trust"},
        "app.workers.traffic_tasks.*": {"queue": "traffic_analysis",  "routing_key": "traffic"},
        "app.workers.sync_tasks.*":    {"queue": "default",           "routing_key": "default"},
    },

    # Timeouts (from settings)
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,  # SoftTimeLimitExceeded raised
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,             # Hard kill after this

    # Retry strategy
    task_acks_late=True,                  # Ack only after task completes (safer)
    task_reject_on_worker_lost=True,      # Re-queue if worker dies mid-task
    task_max_retries=settings.CELERY_MAX_RETRIES,

    # Result backend
    result_expires=3600,                  # Results expire after 1 hour
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0,
        }
    },

    # Worker
    worker_prefetch_multiplier=1,         # One task at a time per worker (fair dispatch)
    worker_max_tasks_per_child=1000,      # Restart worker after 1000 tasks (memory leak guard)
    worker_disable_rate_limits=False,

    # Broker connection retry
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_heartbeat=10,
    broker_pool_limit=10,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "calculate-trust-scores-hourly": {
            "task": "app.workers.trust_tasks.calculate_all_trust_scores",
            "schedule": 3600.0,  # Every hour
            "options": {"queue": "trust_calculation"},
        },
        "aggregate-traffic-stats-minutely": {
            "task": "app.workers.traffic_tasks.aggregate_traffic_statistics",
            "schedule": 60.0,   # Every minute
            "options": {"queue": "traffic_analysis"},
        },
        "cleanup-expired-results-daily": {
            "task": "app.workers.sync_tasks.cleanup_expired_data",
            "schedule": 86400.0,  # Every 24 hours
            "options": {"queue": "default"},
        },
    },
)


# ── Base task class with retry logic ───────────────────────────────────────────
class BaseTask(celery_app.Task):
    """Base task with automatic exponential backoff retry."""

    abstract = True
    max_retries = settings.CELERY_MAX_RETRIES

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            exc_info=True,
            extra={"task_id": task_id, "args": args},
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            f"Task {self.name}[{task_id}] retrying due to: {exc}",
            extra={"task_id": task_id, "retry_count": self.request.retries},
        )

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            f"Task {self.name}[{task_id}] succeeded",
            extra={"task_id": task_id},
        )


celery_app.Task = BaseTask
