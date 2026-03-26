"""Module de routage pour les utilisateurs (users) de l'application Sauvetage."""

from urllib.parse import unquote
from typing import Any, Dict, Annotated
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app_back.db_connection import config
from db_models.objects import Users, UsersPasswords
from db_models.repositories.user import UsersRepository

router = APIRouter(
    prefix="/users",
    tags=["users", "admin", "auth"],
)


@router.get("/search/{username}")
def read_users(username: str):
    """Recherche d'un utilisateur par le username."""
    session = config.get_secure_session()
    stmt = select(Users).where(Users.username == username)
    user = session.execute(stmt).scalar_one_or_none()
    return_dict: Dict[str, Any] = {
        "valid": user is not None,
        "username": user.username if user else None,
        "permissions": user.permissions if user else None,
        "email": user.email if user else None,
        "error": None if user else f"Utilisateur non trouvé : {username}",
    }
    if user is None:
        raise ValueError(f"Utilisateur non trouvé : {username}")
    return return_dict


@router.post("/login")
async def log_user(request: Request,
                   session: Annotated[Session, Depends(config.get_secure_session)]):
    """Recherche d'un utilisateur par le username."""
    data = await request.json()
    username = data.get("username")
    clear_password = data.get("password")

    user_obj = UsersRepository(session)
    user = user_obj.get_by_username(username)
    ok = user_obj.validate_password(user=user, password=clear_password)

    return_dict: Dict[str, Any] = {
        "valid": (user is not None and not user.is_locked and ok),
        "username": user.username if user else None,
        "permissions": user.permissions if (user and ok) else None,
        "mail": user.email if (user and ok) else None,
    }
    if user and user.is_locked:
        return_dict["error"] = "Compte vérouillé après 3 erreurs de connexion."
    elif user and ok:
        user_obj.reset_failed_logins(user)
    elif user:
        user_obj.add_failed_login(user)
        return_dict["error"] = "Mot de passe incorrect."
    else:
        return_dict["error"] = f"Utilisateur non trouvé : {username}"

    return return_dict


@router.get("/no-user")
def exists_first():
    """Vérifie s'il n'existe aucun utilisateur dans la base de données."""
    user_obj = UsersRepository(config.get_secure_session())
    no_user = user_obj.no_users_exists()
    return {"exists": no_user}


@router.post("/create")
async def create_user(request: Request):
    """Création d'un nouvel utilisateur."""
    # Récupération de la session sécurisée
    session = config.get_secure_session()
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
        return {"valid": False, "error": "L'utilisateur existe déjà."}

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
        return {
            "valid": False,
            "error": f"Erreur lors de la création de l'utilisateur : {str(e)}",
        }
    return {"valid": True, "message": f"Utilisateur {username} créé avec succès."}


@router.post("/change-password")
async def change_password(request: Request):
    """Change le mot de passe d'un utilisateur spécifique."""
    data = await request.json()
    username = data.get("username")
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    user_obj = UsersRepository(config.get_secure_session())
    user = user_obj.get_by_username(username)
    if not user:
        raise ValueError(f"Utilisateur non trouvé : {username}")
    auth = user_obj.validate_password(user=user, password=old_password)
    if not auth:
        raise ValueError("Mot de passe actuel incorrect.")
    ok = user_obj.new_password(user=user, password=new_password)
    if not ok:
        raise ValueError(
            "Échec du changement de mot de passe. Vérifiez les informations fournies."
        )
    return {
        "valid": True,
        "message": f"Mot de passe changé avec succès pour l'utilisateur {username}.",
    }


@router.post("/modify/{username}")
async def modify_user(username: str, request: Request):
    """Modifie les informations d'un utilisateur spécifique."""
    data = await request.json()
    username = unquote(username)
    email = data.get("email")
    permissions = data.get("permissions")

    user_obj = UsersRepository(config.get_secure_session())
    user = user_obj.get_by_username(username)
    if not user:
        raise ValueError(f"Utilisateur non trouvé : {username}")
    try:
        user_obj.modify_user(user=user, email=email, permissions=permissions)
    except (ValueError, TypeError) as e:
        message = f"Erreur lors de la modification de l'utilisateur : {str(e)}"
        raise ValueError(message) from e
    return {
        "valid": True,
        "message": f"Utilisateur {username} modifié avec succès.",
        "username": user.username,
        "email": user.email,
        "permissions": user.permissions,
    }
