"""
TBAPS Traffic Analysis Tasks
Celery tasks for processing and aggregating network traffic data.
"""

from app.core.celery_app import celery_app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="app.workers.traffic_tasks.aggregate_traffic_statistics")
def aggregate_traffic_statistics(self):
    """
    Aggregate DNS query and website visit statistics.
    Runs every minute via Celery Beat.
    """
    logger.info("Aggregating traffic statistics")
    # TODO: implement traffic aggregation
    # from app.services.traffic_aggregator import TrafficAggregator
    # aggregator = TrafficAggregator()
    # aggregator.aggregate()
    return {"status": "ok"}


@celery_app.task(bind=True, name="app.workers.traffic_tasks.process_dns_batch")
def process_dns_batch(self, batch: list):
    """
    Process a batch of DNS query records.
    """
    logger.info(f"Processing DNS batch of {len(batch)} records")
    # TODO: implement DNS batch processing
    return {"status": "ok", "processed": len(batch)}
