"""Service d'authentification et de gestion des sessions."""

from typing import Any, MutableMapping

from db_models.objects.users import Users
from db_models.repositories.user import UsersRepository

class AuthService:
    """Service d'authentification et de sécurité des comptes."""

    def __init__(self, session: Any, *, lockout_threshold: int = 3) -> None:
        self.session = session
        self.user_repo = UsersRepository(session)
        self.lockout_threshold = lockout_threshold

    def login(self, username: str, password: str, *,
              session_data: MutableMapping[str, Any] | None = None,) -> tuple[bool, Users | None]:
        """Valide les identifiants et initialise la session si valide."""
        user = self.user_repo.get_by_username(username)
        if not user or not user.is_active or user.is_locked:
            return False, None

        if not self.user_repo.validate_password(user, password):
            self._record_failed_login(user)
            return False, user

        self.user_repo.reset_failed_logins(user)
        if session_data is not None:
            session_data["user_id"] = user.id
            session_data["permissions"] = user.permissions
            session_data["username"] = user.username
        return True, user

    def logout(self, *, session_data: MutableMapping[str, Any]) -> None:
        """Invalide une session utilisateur."""
        session_data.clear()

    def validate_session(self, *, session_data: MutableMapping[str, Any]) -> Users | None:
        """Retourne l'utilisateur si la session est valide, sinon None."""
        user_id = session_data.get("user_id")
        if not user_id:
            return None
        user = self.session.get(Users, user_id)
        if not user or not user.is_active or user.is_locked:
            return None
        return user

    def change_password(self, user: Users, new_password: str) -> Users:
        """Change le mot de passe d'un utilisateur."""
        return self.user_repo.new_password(user=user, password=new_password)

    def lock_user(self, user: Users) -> None:
        """Verrouille un utilisateur."""
        user.is_locked = True
        self.session.commit()

    def unlock_user(self, user: Users) -> None:
        """Deverrouille un utilisateur et reinitialise les echecs."""
        user.is_locked = False
        user.nb_failed_logins = 0
        self.session.commit()

    def reset_failed_logins(self, user: Users) -> bool:
        """Reinitialise les tentatives ratees."""
        return self.user_repo.reset_failed_logins(user)

    def _record_failed_login(self, user: Users) -> None:
        if user.nb_failed_logins >= self.lockout_threshold - 1:
            user.is_locked = True
        user.nb_failed_logins += 1
        self.session.commit()
