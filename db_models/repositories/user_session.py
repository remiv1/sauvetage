"""Dépôt de données pour les sessions utilisateur révocables."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from os import getenv
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from db_models.objects import Users, UserSession
from db_models.repositories.base_repo import BaseRepository


SESSION_LIFETIME_MINUTES = int(getenv("AUTH_SESSION_LIFETIME_MINUTES", "480"))
SESSION_IDLE_TIMEOUT_MINUTES = int(getenv("AUTH_SESSION_IDLE_TIMEOUT_MINUTES", "30"))


class UserSessionsRepository(BaseRepository):
    """Gère la création, la validation et la révocation des sessions utilisateur."""

    @staticmethod
    def _hash_token(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()

    def create(self, user: Users) -> str:
        """Crée une session pour un utilisateur et retourne son jeton non persisté."""
        token = token_urlsafe(32)
        now = datetime.now(timezone.utc)
        session = UserSession(
            token_hash=self._hash_token(token),
            user_id=user.id,
            expires_at=now + timedelta(minutes=SESSION_LIFETIME_MINUTES),
            last_seen_at=now,
        )
        self.session.add(session)
        self.session.commit()
        return token

    def validate(self, token: str) -> UserSession | None:
        """Retourne la session valide associée au jeton, sinon ``None``."""
        if not token:
            return None

        statement = (
            select(UserSession)
            .options(joinedload(UserSession.user))
            .where(UserSession.token_hash == self._hash_token(token))
        )
        session = self.session.execute(statement).scalar_one_or_none()
        if session is None or session.revoked_at is not None:
            return None

        now = datetime.now(timezone.utc)
        idle_deadline = session.last_seen_at + timedelta(
            minutes=SESSION_IDLE_TIMEOUT_MINUTES
        )
        if (
            session.expires_at <= now
            or idle_deadline <= now
            or not session.user.is_active
            or session.user.is_locked
        ):
            return None

        session.last_seen_at = now
        self.session.commit()
        return session

    def revoke(self, token: str) -> bool:
        """Révoque la session désignée par son jeton."""
        if not token:
            return False

        statement = select(UserSession).where(
            UserSession.token_hash == self._hash_token(token)
        )
        session = self.session.execute(statement).scalar_one_or_none()
        if session is None or session.revoked_at is not None:
            return False

        session.revoked_at = datetime.now(timezone.utc)
        self.session.commit()
        return True

    def revoke_for_user(self, user: Users) -> None:
        """Révoque toutes les sessions actives d'un utilisateur."""
        now = datetime.now(timezone.utc)
        for session in user.sessions:
            if session.revoked_at is None:
                session.revoked_at = now
        self.session.commit()
