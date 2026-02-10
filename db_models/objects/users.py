"""Modèle de données pour les utilisateurs."""

from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import mapped_column, Mapped
from db_models import SecureBase
from db_models.objects import QueryMixin

class Users(SecureBase, QueryMixin):
    """Modèle pour les utilisateurs."""
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique de l'utilisateur")

    # Données de base de l'utilisateur
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False,
                                          comment="Nom d'utilisateur")
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False,
                                       comment="Adresse email de l'utilisateur")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True,
                                            comment="Indique si l'utilisateur est actif")
    # La gestion des droits se fait par une chaine de caractères avec des nombres accolés
    # Par exemple "1" admin, "2" comptable, "3" commercial, "4" logistique, "5" support,
    # "6" informatique, "7" RH, "8" direction, "9" super admin
    # Exemple : "13" pour un utilisateur qui est à la fois admin et commercial
    permissions: Mapped[str] = mapped_column(String, comment="Permissions de l'utilisateur")

    # Méta-données de suivi
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                        default=lambda: datetime.now(timezone.utc),
                                        comment="Date de création de l'utilisateur")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière MàJ de l'utilisateur")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email}, " \
               f"is_active={self.is_active})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet User en dictionnaire."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Users":
        """Crée un objet User à partir d'un dictionnaire."""
        return cls(
            username=data.get("username", ""),
            email=data.get("email", ""),
            is_active=data.get("is_active", True),
            permissions=data.get("permissions", "")
        )

class UsersPasswords(SecureBase):
    """Modèle pour les mots de passe des utilisateurs."""
    __tablename__ = 'users_passwords'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique du mot de passe")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False,
                                         comment="Identifiant de l'utilisateur associé")
    password_hash: Mapped[str] = mapped_column(String, nullable=False,
                                               comment="Hash du mot de passe de l'utilisateur")
    from_date: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                              default=lambda: datetime.now(timezone.utc),
                                              comment="Date de début de validité du mot de passe")
    to_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True,
                                                     comment="Date fin de validité du mot de passe")

    def __repr__(self) -> str:
        return f"<UserPassword(id={self.id}, user_id={self.user_id})>"

class UsersSessions(SecureBase):
    """Modèle pour les sessions des utilisateurs."""
    __tablename__ = 'users_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique de la session")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False,
                                         comment="Identifiant de l'utilisateur associé")
    session_token: Mapped[str] = mapped_column(String, nullable=False,
                                               comment="Token de session de l'utilisateur")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création de la session")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 comment="Date d'expiration de la session")

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"
