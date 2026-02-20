"""Module de routage pour les utilisateurs (users) de l'application Sauvetage."""

from typing import Any, Dict
from fastapi import APIRouter, Request
from sqlalchemy import select
from app_back.db_connection.config import get_secure_session
from db_models.objects.users import Users, UsersPasswords
from db_models.repositories.user import UsersRepository
from db_models.services.auth import AuthService

router = APIRouter(
    prefix="/users",
    tags=["users", "admin", "auth"],
)

@router.get("/search/{username}")
def read_users(username: str):
    """Recherche d'un utilisateur par le username."""
    session = get_secure_session()
    stmt = select(Users).where(Users.username == username)
    user = session.execute(stmt).scalar_one_or_none()
    return_dict: Dict[str, Any] = {
        "valid": user is not None,
        "username": user.username if user else None,
        "permissions": user.permissions if user else None,
        "mail": user.mail if user else None,
        "error": None if user else f"Utilisateur non trouvé : {username}"
    }
    return return_dict

@router.post("/login/{username}/{password}")
def log_user(username: str, clear_password: str):
    """Recherche d'un utilisateur par le username."""
    user_obj = UsersRepository(get_secure_session())
    session = get_secure_session()
    auth = AuthService(user_repo=user_obj)
    ok, user = auth.login(username, clear_password)

    return_dict: Dict[str, Any] = {
        "valid": (user is not None and not user.is_locked and ok),
        "username": user.username if user else None,
        "permissions": user.permissions if (user and ok) else None,
        "mail": user.mail if (user and ok) else None
    }
    if user and user.is_locked:
        return_dict["error"] = "Compte vérouillé après 3 erreurs de connexion."
    elif user and ok:
        pass    # type: ignore
    elif user:
        user.failed_logins += 1
        user.is_locked = user.failed_logins >= 3
        session.commit()
        return_dict["error"] = "Mot de passe incorrect."
    else:
        return_dict["error"] = f"Utilisateur non trouvé : {username}"

    return return_dict

@router.get("/no-user")
def exists_first():
    """Vérifie s'il n'existe aucun utilisateur dans la base de données."""
    user_obj = UsersRepository(get_secure_session())
    no_user = user_obj.no_users_exists()
    return {"exists": no_user is not None}

@router.post("/create")
async def create_user(request: Request):
    """Création d'un nouvel utilisateur."""
    # Récupération de la session sécurisée
    session = get_secure_session()
    user_obj = UsersRepository(session)

    # Récupération des données du formulaire
    data = await request.json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    permissions = data.get("permissions")

    # Vérification de l'existence d'un utilisateur avec le même username
    stmt = select(Users).where(Users.username == username)
    existing_user = session.execute(stmt).scalar_one_or_none()
    if existing_user:
        return {"valid": False,
                "error": "L'utilisateur existe déjà."}

    # Création du nouvel utilisateur et de son mot de passe
    try:
        new_user = Users(username=username, email=email, permissions=permissions)
        session.add(new_user)
        session.flush()
        hash_pwd = user_obj.hash_password(password)
        del password
        new_password = UsersPasswords(user_id=new_user.id, password_hash=hash_pwd)
        del hash_pwd
        session.add(new_password)
        session.commit()
    # Rollback en cas d'erreur (ex: violation de contrainte) et retour d'une erreur claire
    except (ValueError, TypeError) as e:
        session.rollback()
        return {"valid": False,
                "error": f"Erreur lors de la création de l'utilisateur : {str(e)}"
                }
    return {"valid": True,
            "message": f"Utilisateur {username} créé avec succès."
            }
