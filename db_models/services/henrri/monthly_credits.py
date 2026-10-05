"""Crédits mensuels Henrri, réservés atomiquement dans MongoDB."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from uuid import uuid4

from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from .rate_limiting import get_account_identifier, get_mongo_settings


class MonthlyCreditsUnavailable(RuntimeError):
    """Erreur empêchant de vérifier ou de mettre à jour les crédits partagés."""

    status_code = 503


class MonthlyCreditQuotaExceeded(RuntimeError):
    """Quota atteint, en incluant les réservations encore incertaines."""

    status_code = 429

    def __init__(self, limit: int, reset_at: datetime) -> None:
        self.body = {"limit": limit, "reset_at": reset_at.isoformat()}
        super().__init__(
            f"Quota mensuel Henrri atteint ({limit} crédits, réservations incluses). "
            f"Facturation bloquée jusqu'au {reset_at:%d/%m/%Y} à 00:00 UTC "
            "ou à la vérification des réservations incertaines."
        )


@dataclass(frozen=True)
class CreditReservation:
    """Identifie un crédit dans son mois d'origine, même après le changement de mois."""

    document_id: str
    token: str


@dataclass(frozen=True)
class MonthlyCreditStatus:
    """État du budget mensuel partagé et des réservations à vérifier."""

    limit: int
    consumed: int
    reservations: tuple[CreditReservation, ...]
    reset_at: datetime

    @property
    def available(self) -> int:
        """Retourne le nombre de crédits encore disponibles."""
        return max(0, self.limit - self.consumed - len(self.reservations))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_credit_limit() -> int:
    """Lit le plafond mensuel défini par HENRRI_CREDIT_LIMIT.

    Returns:
        Nombre maximal de crédits mensuels, 200 si la variable est absente.

    Raises:
        ValueError: Si HENRRI_CREDIT_LIMIT n'est pas un entier strictement positif.
    """
    try:
        limit = int(os.getenv("HENRRI_CREDIT_LIMIT", "200"))
    except ValueError as exc:
        raise ValueError("HENRRI_CREDIT_LIMIT doit être un entier strictement positif.") from exc
    if limit <= 0:
        raise ValueError("HENRRI_CREDIT_LIMIT doit être un entier strictement positif.")
    return limit


class HenrriMonthlyCredits:
    """Gère les réservations et la consommation pour un compte Henrri."""

    def __init__(
        self,
        collection: Collection[dict[str, Any]],
        identifier: str,
        limit: int | None = None,
        initial_period: str = "",
        initial_used: int = 0,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        limit = get_credit_limit() if limit is None else limit
        if limit <= 0 or not 0 <= initial_used <= limit:
            raise ValueError(
            "Le quota mensuel doit être strictement positif, avec une consommation initiale valide."
            )
        if initial_period:
            parsed = datetime.strptime(initial_period, "%Y-%m")
            if parsed.strftime("%Y-%m") != initial_period:
                raise ValueError("La période initiale Henrri doit respecter YYYY-MM.")
        elif initial_used:
            raise ValueError("Une consommation initiale Henrri nécessite une période YYYY-MM.")
        self._collection = collection
        self._identifier = identifier
        self._limit = limit
        self._initial_period = initial_period
        self._initial_used = initial_used
        self._clock = clock

    def get_status(self) -> MonthlyCreditStatus:
        """Lit le budget du mois UTC courant et les réservations à vérifier.

        Returns:
            État partagé du budget mensuel.

        Raises:
            MonthlyCreditsUnavailable: Si MongoDB est indisponible.
        """
        try:
            document_id, reset_at = self._ensure_month()
            document = self._collection.find_one({"_id": document_id})
        except PyMongoError as exc:
            raise MonthlyCreditsUnavailable(
                "Crédits Henrri indisponibles : vérifiez MongoDB."
            ) from exc
        if document is None:
            raise MonthlyCreditsUnavailable("Compteur mensuel Henrri introuvable.")
        return MonthlyCreditStatus(
            self._limit,
            document["consumed"],
            tuple(CreditReservation(document_id, token) for token in document["reservations"]),
            reset_at,
        )

    def ensure_available(self) -> None:
        """Bloque un nouveau traitement quand aucun crédit n'est disponible.

        Raises:
            MonthlyCreditQuotaExceeded: Si le budget est épuisé.
            MonthlyCreditsUnavailable: Si le budget ne peut pas être vérifié.
        """
        status = self.get_status()
        if not status.available:
            raise MonthlyCreditQuotaExceeded(status.limit, status.reset_at)

    def reserve(self) -> CreditReservation:
        """Réserve atomiquement un crédit avant une écriture métier HTTP.

        Returns:
            Réservation à confirmer, libérer ou conserver si l'issue est incertaine.

        Raises:
            MonthlyCreditQuotaExceeded: Si le budget est épuisé.
            MonthlyCreditsUnavailable: Si MongoDB est indisponible.
        """
        token = uuid4().hex
        try:
            document_id, reset_at = self._ensure_month()
            document = self._collection.find_one_and_update(
                {
                    "_id": document_id,
                    "$expr": {
                        "$lt": [
                            {"$add": ["$consumed", {"$size": "$reservations"}]},
                            self._limit,
                        ]
                    },
                },
                {"$push": {"reservations": token}},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as exc:
            raise MonthlyCreditsUnavailable(
                "Crédits Henrri indisponibles : écriture bloquée."
            ) from exc
        if document is None:
            raise MonthlyCreditQuotaExceeded(self._limit, reset_at)
        return CreditReservation(document_id, token)

    def confirm(self, reservation: CreditReservation) -> None:
        """Confirme un succès connu, une seule fois, dans le mois réservé.

        Args:
            reservation: Réservation dont le succès HTTP a été vérifié.

        Raises:
            MonthlyCreditsUnavailable: Si la confirmation ne peut pas être enregistrée.
        """
        self._settle(reservation, successful=True)

    def cancel(self, reservation: CreditReservation) -> None:
        """Libère un crédit uniquement après vérification d'un échec certain.

        Args:
            reservation: Réservation dont l'échec a été vérifié.

        Raises:
            MonthlyCreditsUnavailable: Si la libération ne peut pas être enregistrée.
        """
        self._settle(reservation, successful=False)

    def _ensure_month(self) -> tuple[str, datetime]:
        now = self._clock().astimezone(timezone.utc)
        period = now.strftime("%Y-%m")
        document_id = f"{self._identifier}:{period}"
        reset_at = datetime(
            now.year + (now.month == 12), now.month % 12 + 1, 1, tzinfo=timezone.utc,
        )
        initial_used = self._initial_used if period == self._initial_period else 0
        try:
            self._collection.update_one(
                {"_id": document_id},
                {"$setOnInsert": {"consumed": initial_used, "reservations": []}},
                upsert=True,
            )
        except DuplicateKeyError:
            pass
        return document_id, reset_at

    def _settle(self, reservation: CreditReservation, *, successful: bool) -> None:
        update: dict[str, Any] = {"$pull": {"reservations": reservation.token}}
        if successful:
            update["$inc"] = {"consumed": 1}
        try:
            self._collection.update_one(
                {"_id": reservation.document_id, "reservations": reservation.token},
                update,
            )
        except PyMongoError as exc:
            raise MonthlyCreditsUnavailable(
                "Réservation Henrri conservée : vérifiez MongoDB."
            ) from exc


def get_monthly_credits(api_key: str, base_url: str) -> HenrriMonthlyCredits:
    """Retourne le compteur mensuel commun au front et au back.

    Args:
        api_key: Identifiant du compte Henrri, jamais journalisé.
        base_url: URL de l'environnement Henrri.

    Returns:
        Compteur partagé utilisant HENRRI_CREDIT_LIMIT et HENRRI_MONTHLY_CREDIT_INITIAL_*.
    """
    limit = get_credit_limit()
    initial_period = os.getenv("HENRRI_MONTHLY_CREDIT_INITIAL_PERIOD", "")
    initial_used = int(os.getenv("HENRRI_MONTHLY_CREDIT_INITIAL_USED", "0"))
    return _cached_monthly_credits(
        get_account_identifier(api_key, base_url), limit, initial_period, initial_used,
    )


@lru_cache(maxsize=16)
def _cached_monthly_credits(
    identifier: str, limit: int, initial_period: str, initial_used: int,
) -> HenrriMonthlyCredits:
    uri, database = get_mongo_settings()
    client: MongoClient[dict[str, Any]] = MongoClient(
        uri, connect=False, connectTimeoutMS=5000, serverSelectionTimeoutMS=5000,
    )
    return HenrriMonthlyCredits(
        client[database]["henrri_monthly_credits"], identifier,
        limit=limit, initial_period=initial_period, initial_used=initial_used,
    )
