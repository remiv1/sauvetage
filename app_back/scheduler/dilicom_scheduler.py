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
    scheduler = BackgroundScheduler(
        job_defaults={"coalesce": False, "max_instances": 1}
    )

    def _send_updates():
        with config.main_session_ctx() as session:
            DilicomService(session=session).send_updates()

    def _fetch_returns():
        with config.main_session_ctx() as session:
            DilicomService(session=session).fetch_returns()

    # Attention de ne pas embouteiller les schedulings.
    # 02:00 : Réception de la sauvegarde du site e-commerce.
    # 02:01 : Envoi de la sauvegarde locale sur le serveur du site e-commerce.
    # 22:00 : Envoi des référentiels à Dilicom.
    # 06:00-12:00 : Vérification des retours de Dilicom toutes les heures.

    # Planification de l'envoie des référentiels à Dilicom tous les jours à 2h du matin
    scheduler.add_job(
        _send_updates,
        "cron",
        hour=22,
        minute=00,
        id="dilicom_send_updates",
    )

    # Vérification des retours de Dilicom tous les jours à partir de 6h jusqu'à 12h,
    # toutes les heures sauf à avoir reçu des retours
    scheduler.add_job(
        _fetch_returns,
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
