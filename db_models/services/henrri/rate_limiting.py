"""Quota Henrri partagé entre processus avec une fenêtre glissante MongoDB."""

import hashlib
import logging
import os
import time
from collections.abc import Callable
from functools import lru_cache
from urllib.parse import quote_plus

from limits import RateLimitItemPerMinute
from limits.storage import MongoDBStorage
from limits.strategies import MovingWindowRateLimiter
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


def get_requests_per_minute() -> int:
    """Lit le quota Henrri configuré dans l'environnement.

    Returns:
        Nombre maximal de requêtes pendant une fenêtre de 60 secondes.

    Raises:
        ValueError: Si HENRRI_RATE_LIMITING n'est pas un entier strictement positif.
    """
    try:
        limit = int(os.getenv("HENRRI_RATE_LIMITING", "20"))
    except ValueError as exc:
        raise ValueError("HENRRI_RATE_LIMITING doit être un entier strictement positif.") from exc
    if limit <= 0:
        raise ValueError("HENRRI_RATE_LIMITING doit être un entier strictement positif.")
    return limit


class HenrriRateLimiter:
    """Réserve atomiquement un appel Henrri avant son envoi HTTP."""

    def __init__(
        self,
        limit: int,
        identifier: str,
        strategy: MovingWindowRateLimiter,
        clock: Callable[[], float] = time.time,
        wait: Callable[[float], None] = time.sleep,
    ) -> None:
        if limit <= 0:
            raise ValueError("Le quota Henrri doit être strictement positif.")
        self._limit = RateLimitItemPerMinute(limit)
        self._identifier = identifier
        self._strategy = strategy
        self._clock = clock
        self._wait = wait

    def acquire(self) -> None:
        """Attend puis réserve un créneau dans le quota partagé.

        Raises:
            RuntimeError: Si MongoDB ne permet pas de vérifier le quota.
        """
        try:
            while not self._strategy.hit(self._limit, self._identifier):
                stats = self._strategy.get_window_stats(self._limit, self._identifier)
                delay = max(0.01, stats.reset_time - self._clock())
                logger.info("Quota Henrri atteint : attente de %.2f secondes.", delay)
                self._wait(delay)
        except PyMongoError as exc:
            raise RuntimeError(
                "Quota Henrri indisponible : requête bloquée, vérifiez MongoDB."
            ) from exc


def get_rate_limiter(api_key: str, base_url: str) -> HenrriRateLimiter:
    """Retourne le limiteur partagé correspondant au compte Henrri.

    Args:
        api_key: Identifiant du compte Henrri, jamais journalisé.
        base_url: URL de l'environnement Henrri.

    Returns:
        Limiteur utilisant le stockage MongoDB commun au front et au back.
    """
    identifier = get_account_identifier(api_key, base_url)
    return _cached_rate_limiter(identifier, get_requests_per_minute())


def get_account_identifier(api_key: str, base_url: str) -> str:
    """Retourne une empreinte du compte et de l'environnement, sans exposer la clé.

    Args:
        api_key: Identifiant du compte Henrri.
        base_url: URL de l'environnement Henrri.

    Returns:
        Empreinte commune aux quotas minute et mensuel.
    """
    return hashlib.sha256(f"{base_url.rstrip('/')}:{api_key}".encode()).hexdigest()


def get_mongo_settings() -> tuple[str, str]:
    """Retourne la connexion MongoDB partagée des quotas Henrri.

    Returns:
        URI de connexion et nom de la base, à ne jamais journaliser.
    """
    database = os.getenv("MONGO_DB_LOGS", "sauvetage_logs")
    username = quote_plus(os.getenv("MONGO_USER_APP", "app_user"))
    password = quote_plus(os.getenv("MONGO_PASSWORD_APP", "app_password"))
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    uri = f"mongodb://{username}:{password}@{host}:{port}/?authSource={quote_plus(database)}"
    return uri, database


@lru_cache(maxsize=16)
def _cached_rate_limiter(identifier: str, limit: int) -> HenrriRateLimiter:
    uri, database = get_mongo_settings()
    storage = MongoDBStorage(
        uri,
        database_name=database,
        counter_collection_name="henrri_rate_limit_counters",
        window_collection_name="henrri_rate_limit_windows",
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000,
    )
    return HenrriRateLimiter(limit, identifier, MovingWindowRateLimiter(storage))