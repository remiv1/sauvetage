"""
Dépôt de données pour les utilisateurs. Ceci ne contient que d'une classe :
    - UsersRepository : Contient les méthodes pour interagir avec les données des utilisateurs,
        notamment la validation des mots de passe, la création de nouveaux mots de passe, et la
        gestion des tentatives de connexion échouées.
"""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.users import Users, UsersPasswords
from db_models.security.secur_sauv import PwdHasher

class UsersRepository(BaseRepository):
    """
    Dépôt de données pour les utilisateurs.
    Contient les méthodes :
    - get_by_username : pour récupérer un utilisateur par son nom d'utilisateur.
    - validate_password : pour valider un mot de passe pour un utilisateur donné.
    - new_password : pour créer un nouveau mot de passe pour un utilisateur donné.
    - add_failed_login : pour incrémenter le nombre de tentatives de connexion échouées pour
                         un utilisateur donné.
    - reset_failed_logins : pour réinitialiser le nombre de tentatives de connexion échouées
                            pour un utilisateur donné.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialise le dépôt de données pour les utilisateurs."""
        super().__init__(*args, **kwargs)
        self._hasher = PwdHasher()

    def get_by_username(self, username: str) -> Users | None:
        """Récupère un utilisateur par son nom d'utilisateur.
        Args:
            username (str): Le nom d'utilisateur de l'utilisateur à récupérer.
        Returns:
            Users | None: L'utilisateur correspondant au nom d'utilisateur,
                          ou None s'il n'existe pas.
        """
        stmt = select(Users).where(Users.username == username).options(
            selectinload(Users.passwords)
        )
        user = self.session.execute(stmt).scalar_one_or_none()
        return user

    def hash_password(self, password: str) -> str:
        """Hash un mot de passe en utilisant bcrypt.
        Args:
            password (str): Le mot de passe en clair à hasher.
        Returns:
            str: Le mot de passe hashé.
        """
        return self._hasher.hash(password)

    def validate_password(self, user: Users, password: str) -> bool:
        """Valide un mot de passe pour un utilisateur donné.
        Args:
            user (Users): L'utilisateur pour lequel valider le mot de passe.
            password (str): Le mot de passe à valider.
        Returns:
            bool: True si le mot de passe est valide, False sinon.
        """
        active_pwd = next((pwd for pwd in user.passwords if pwd.to_date is None), None)
        if not active_pwd:
            return False
        return self._hasher.verify(password, active_pwd.password_hash)

    def new_password(self, *, user: Users, password: str) -> "Users":
        """Hash un mot de passe en utilisant bcrypt.
        Args:
            user (Users): L'utilisateur pour lequel créer un nouveau mot de passe.
            password (str): Le mot de passe en clair.
        Returns:
            Users: L'utilisateur avec le mot de passe hashé ajouté.
        """
        now = datetime.now(timezone.utc)
        active_pwd = next((pwd for pwd in user.passwords if pwd.to_date is None), None)
        if active_pwd:
            active_pwd.to_date = now
        new_pwd = UsersPasswords(
            user_id=user.id,
            password_hash=self._hasher.hash(password),
            from_date=now, to_date=None
        )
        user.passwords.append(new_pwd)
        self.session.commit()
        return user

    def add_failed_login(self, user: Users) -> None:
        """Incrémente le nombre de tentatives de connexion échouées pour un utilisateur donné.
        Args:
            user (Users): L'utilisateur pour lequel incrémenter le nombre de tentatives de
                          connexion échouées.
        Returns:
            None
        """
        if user.nb_failed_logins >= 3:
            user.is_locked = True
        user.nb_failed_logins += 1
        self.session.commit()

    def reset_failed_logins(self, user: Users) -> bool:
        """Réinitialise le nombre de tentatives de connexion échouées pour un utilisateur donné.
        Args:
            user (Users): L'utilisateur pour lequel réinitialiser le nombre de tentatives de
                          connexion échouées.
        Returns:
            bool: True si le nombre de tentatives de connexion échouées a été réinitialisé,
                  False si le compte de l'utilisateur est verrouillé.
        """
        if not user.is_locked:
            user.nb_failed_logins = 0
            self.session.commit()
            return True
        return False

    def no_users_exists(self) -> bool:
        """Vérifie s'il n'existe aucun utilisateur dans la base de données.
        Returns:
            bool: True s'il n'existe aucun utilisateur, False sinon.
        """
        stmt = select(Users)
        result = self.session.execute(stmt)
        return result is None
