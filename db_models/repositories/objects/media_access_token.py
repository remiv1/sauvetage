"""Repository pour les jetons d'accès temporaires aux images WooCommerce."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import MediaAccessToken

_TOKEN_LIFETIME_HOURS = 1


class MediaAccessTokenRepository(BaseRepository):
    """Gestion des jetons d'accès temporaires (usage unique, durée 1h)."""

    def create(self, media_id: int) -> MediaAccessToken:
        """Crée un jeton pour un média donné et le valide 1 heure."""
        now = datetime.now(timezone.utc)
        record = MediaAccessToken(
            token=str(uuid.uuid4()),
            media_file_id=media_id,
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

    def get_last_by_media_id(self, media_id: int) -> Optional[MediaAccessToken]:
        """Retourne le dernier jeton créé pour un média donné."""
        stmt = (
            select(MediaAccessToken)
            .where(MediaAccessToken.media_file_id == media_id)
            .order_by(MediaAccessToken.valid_from.desc())
        )
        return self.session.execute(stmt).scalars().first()

    def consume(self, record: MediaAccessToken) -> None:
        """Marque le jeton comme consommé."""
        record.used_at = datetime.now(timezone.utc)
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la consommation du jeton : {exc}") from exc
