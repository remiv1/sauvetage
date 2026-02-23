"""
Service de gestion des utilisateurs. Il comporte plusieurs méthodes :
    - create_user : pour créer un nouvel utilisateur avec un mot de passe initial.
    - deactivate_user : pour désactiver un utilisateur (soft delete).
    - activate_user : pour réactiver un utilisateur désactivé.
    - update_permissions : pour mettre à jour les permissions d'un utilisateur.
    - get_by_username : pour récupérer un utilisateur par son nom d'utilisateur.
"""

from typing import Any
from sqlalchemy.exc import IntegrityError
from db_models.objects.users import Users
from db_models.repositories.user import UsersRepository

class UserService:
    """
    Service de gestion des utilisateurs. Il comporte plusieurs méthodes :
    - create_user : pour créer un nouvel utilisateur avec un mot de passe initial.
    - deactivate_user : pour désactiver un utilisateur (soft delete).
    - activate_user : pour réactiver un utilisateur désactivé.
    - update_permissions : pour mettre à jour les permissions d'un utilisateur.
    - get_by_username : pour récupérer un utilisateur par son nom d'utilisateur.
    """
    def __init__(self, session: Any) -> None:
        """
        Initialise le service de gestion des utilisateurs.
        Args:
            session (Any): La session de base de données à utiliser pour les opérations.
        """
        self.session = session
        self.user_repo = UsersRepository(session)

    def create_user(self, *, username: str, email: str, password: str,
                    permissions: str) -> Users:
        """
        Cree un utilisateur et initialise son mot de passe.
        Args:
            username (str): Le nom d'utilisateur du nouvel utilisateur.
            email (str): L'adresse email du nouvel utilisateur.
            password (str): Le mot de passe du nouvel utilisateur.
            permissions (str): Les permissions du nouvel utilisateur.
        Returns:
            Users: L'utilisateur créé mais pas encore commité en base de données.
        Raises:
            ValueError: Si la création de l'utilisateur échoue (par exemple, en cas de conflit
                        de nom d'utilisateur ou d'email).
        """
        user = Users(
            username=username,
            email=email,
            permissions=permissions
        )
        try:
            self.session.add(user)
            self.session.flush()
            self.user_repo.new_password(user=user, password=password)
            self.session.commit()
            return user
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError("Erreur lors de la création de l'utilisateur : " + str(e)) from e

    def deactivate_user(self, user: Users) -> Users:
        """
        Desactive un utilisateur (Soft delete).
        Args:
            user (Users): L'utilisateur à désactiver.
        Returns:
            Users: L'utilisateur désactivé.
        """
        user.is_active = False
        self.session.commit()
        return user

    def activate_user(self, user: Users) -> Users:
        """
        Active un utilisateur.
        Args:
            user (Users): L'utilisateur à activer.
        Returns:
            Users: L'utilisateur activé.
        """
        user.is_active = True
        self.session.commit()
        return user

    def update_permissions(self, user: Users, permissions: str) -> Users:
        """
        Met a jour les permissions d'un utilisateur.
        Args:
            user (Users): L'utilisateur dont les permissions doivent être mises à jour.
            permissions (str): La nouvelle chaîne de permissions à attribuer à l'utilisateur.
            Il est possible d'utiliser les constantes définies dans le module pour construire
            la chaîne de permissions : ADMIN + COMMERCIAL ("13")
        Returns:
            Users: L'utilisateur avec les permissions mises à jour.
        """
        user.permissions = permissions
        self.session.commit()
        return user

    def get_by_username(self, username: str) -> Users | None:
        """
        Recupere un utilisateur par son nom d'utilisateur.
        Args:
            username (str): Le nom d'utilisateur de l'utilisateur à récupérer.
        Returns:
            Users | None: L'utilisateur correspondant au nom d'utilisateur,
                          ou None s'il n'existe pas.
        """
        return self.user_repo.get_by_username(username)
