"""Modèles de services pour Henrri."""

import logging
from collections.abc import Callable

import httpx
from henrri_connect import SyncHenrriClient
from .monthly_credits import (
    HenrriMonthlyCredits,
    MonthlyCreditsUnavailable,
    get_monthly_credits,
)
from .rate_limiting import get_rate_limiter
from .utils import HenrriConfig

logger = logging.getLogger(__name__)


class HenrriCreditTransport(httpx.BaseTransport):
    """Réserve les crédits des écritures métier et traite leur issue HTTP."""

    def __init__(
        self,
        transport: httpx.BaseTransport,
        budget_factory: Callable[[], HenrriMonthlyCredits],    # pylint: disable=W0622
    ) -> None:
        self._transport = transport
        self._budget_factory = budget_factory

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Envoie une requête en protégeant le budget des écritures métier.

        Args:
            request: Requête HTTP à transmettre.

        Returns:
            Réponse HTTP, conservée même si sa confirmation MongoDB échoue.

        Raises:
            RuntimeError: Si aucun crédit ne peut être réservé.
            httpx.TransportError: Si l'envoi ou la réception échoue.
        """
        if not self._is_business_write(request):
            return self._transport.handle_request(request)

        monthly_budget = self._budget_factory()
        reservation = monthly_budget.reserve()
        try:
            response = self._transport.handle_request(request)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            try:
                monthly_budget.cancel(reservation)
            except MonthlyCreditsUnavailable:
                logger.error(
                    "Réservation Henrri à vérifier après échec de connexion : %s / %s.",
                    reservation.document_id, reservation.token,
                )
            raise
        except Exception:
            logger.warning(
                "Écriture Henrri incertaine %s %s : réservation conservée %s / %s.",
                request.method, request.url.path, reservation.document_id, reservation.token,
            )
            raise

        try:
            if response.is_success:
                monthly_budget.confirm(reservation)
            else:
                monthly_budget.cancel(reservation)
        except MonthlyCreditsUnavailable:
            logger.error(
                "Réservation Henrri à vérifier après réponse HTTP %s : %s / %s.",
                response.status_code, reservation.document_id, reservation.token,
            )
        return response

    def close(self) -> None:
        """Ferme le transport HTTP délégué."""
        self._transport.close()

    @staticmethod
    def _is_business_write(request: httpx.Request) -> bool:
        return request.method in {"POST", "PUT", "PATCH", "DELETE"} and (
            request.url.path.rstrip("/") not in {
                "/v1/users/authenticate", "/v1/users/refresh-token",
            }
        )


class HenrriService:
    """Service de base pour les échanges avec Henrri."""

    READ_TIMEOUT_SECONDS = 60.0

    def __init__(self) -> None:
        key = HenrriConfig().api_key
        secret = HenrriConfig().api_secret
        url = HenrriConfig().api_url
        if url:
            self.client: SyncHenrriClient = SyncHenrriClient(key, secret, base_url=url)
        else:
            self.client: SyncHenrriClient = SyncHenrriClient(key, secret)

        self.client._http = httpx.Client(
            transport=HenrriCreditTransport(httpx.HTTPTransport(), self._monthly_credits),
            timeout=httpx.Timeout(
                connect=15.0,
                read=self.READ_TIMEOUT_SECONDS,
                write=30.0,
                pool=10.0,
            ),
            event_hooks={"request": [self._limit_request]},
        )

    def _limit_request(self, _request: httpx.Request) -> None:
        get_rate_limiter(self.client._client_id, self.client._base_url).acquire()   # pylint: disable=W0212

    def ensure_monthly_credit(self) -> None:
        """Vérifie le budget partagé avant de commencer une facturation.

        Raises:
            RuntimeError: Si le budget est épuisé ou indisponible.
        """
        self._monthly_credits().ensure_available()

    def _monthly_credits(self) -> HenrriMonthlyCredits:
        return get_monthly_credits(self.client._client_id, self.client._base_url)  # pylint: disable=W0212
