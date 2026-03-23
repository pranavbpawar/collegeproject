"""
TBAPS Trust Calculation Tasks
Celery tasks for computing employee trust scores.
"""

from app.core.celery_app import celery_app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="app.workers.trust_tasks.calculate_all_trust_scores")
def calculate_all_trust_scores(self):
    """
    Recalculate trust scores for all active employees.
    Runs hourly via Celery Beat.
    """
    logger.info("Starting trust score calculation for all employees")
    # TODO: implement full trust score calculation
    # from app.services.trust_calculator import TrustCalculator
    # calculator = TrustCalculator()
    # calculator.calculate_all()
    logger.info("Trust score calculation complete")
    return {"status": "ok"}


@celery_app.task(bind=True, name="app.workers.trust_tasks.calculate_employee_trust_score")
def calculate_employee_trust_score(self, employee_id: str):
    """
    Recalculate trust score for a single employee.
    """
    logger.info(f"Calculating trust score for employee {employee_id}")
    # TODO: implement per-employee trust score calculation
    return {"status": "ok", "employee_id": employee_id}
