"""Scheduler pour les opérations Dilicom."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app_back.db_connection import config
from db_models.services.dilicom import DilicomService

logger = logging.getLogger("app_back.scheduler.dilicom")

def start_dilicom_scheduler():
    """
    Démarre le scheduler pour les opérations Dilicom.
    """
    session = config.get_main_session()
    service = DilicomService(session=session)
    scheduler = BackgroundScheduler(
        job_defaults={"coalesce": False, "max_instances": 1}
    )

    # Planification de l'envoie des référentiels à Dilicom tous les jours à 2h du matin
    scheduler.add_job(
        service.send_updates,
        "cron",
        hour=2,
        minute=0,
        id="dilicom_send_updates",
    )

    # Vérification des retours de Dilicom tous les jours à partir de 6h jusqu'à 12h,
    # toutes les heures sauf à avoir reçu des retours
    scheduler.add_job(
        service.fetch_returns,
        "cron",
        hour="6-12",
        minute=0,
        id="dilicom_fetch_returns",
    )

    # Démarrage du scheduler
    scheduler.start()

    # Logguer le démarrage du scheduler
    logger.info(
        "[SCHEDULER] Scheduler Dilicom démarré",
        extra={"jobs": [job.id for job in scheduler.get_jobs()]},
    )
