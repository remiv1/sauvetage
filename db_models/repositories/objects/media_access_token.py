"""Repository pour les jetons d'accès temporaires aux images WooCommerce."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import MediaAccessToken

_TOKEN_LIFETIME_HOURS = 1


class MediaAccessTokenRepository(BaseRepository):
    """Gestion des jetons d'accès temporaires (usage unique, durée 1h)."""

    def create(self, token: str) -> MediaAccessToken:
        """Crée un jeton pour le fichier ``token`` valable 1 heure."""
        now = datetime.now(timezone.utc)
        record = MediaAccessToken(
            token=token,
            valid_from=now,
            valid_until=now + timedelta(hours=_TOKEN_LIFETIME_HOURS),
            used_at=None,
        )
        try:
            self.session.add(record)
            self.session.commit()
            return record
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création du jeton : {exc}") from exc

    def renew(self, record: MediaAccessToken) -> MediaAccessToken:
        """Renouvelle la validité d'un jeton expiré ou consommé."""
        now = datetime.now(timezone.utc)
        record.valid_from = now
        record.valid_until = now + timedelta(hours=_TOKEN_LIFETIME_HOURS)
        record.used_at = None
        try:
            self.session.commit()
            return record
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ValueError(f"Erreur lors du renouvellement du jeton : {exc}") from exc

    def get(self, token: str) -> Optional[MediaAccessToken]:
        """Retourne le jeton ou None s'il est inexistant."""
        return self.session.get(MediaAccessToken, token)

    def consume(self, record: MediaAccessToken) -> None:
        """Marque le jeton comme consommé."""
        record.used_at = datetime.now(timezone.utc)
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la consommation du jeton : {exc}") from exc
