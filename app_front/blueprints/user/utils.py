"""Module de gestion des routes liées aux utilisateurs."""

from urllib.parse import quote
import requests
from app_front.config import (
    NO_USERS_URL, LOGIN_URL, CREATE_USER_URL, SEARCH_USER_URL, CHANGE_PASSWORD_URL, MODIFY_USER_URL
    )

def user_search(username: str) -> dict:
    """Recherche d'un utilisateur par le username."""
    response = requests.get(f"{SEARCH_USER_URL}/{username}", timeout=10)
    if response.status_code // 100 != 2:
        message = f"Erreur lors de la recherche de l'utilisateur : {response.text}"
        raise requests.RequestException(message)
    data = response.json()
    return data

def check_no_users() -> bool:
    """Vérifie s'il n'existe aucun utilisateur dans la base de données."""
    response = requests.get(NO_USERS_URL, timeout=10)
    if response.status_code // 100 != 2:
        message = f"Erreur lors de la vérification des utilisateurs : {response.text}"
        raise requests.RequestException(message)
    response_data = response.json()
    return response_data.get("exists", False)

def log_user(username: str, password: str) -> dict:
    """Recherche d'un utilisateur par le username."""
    body = {
        "username": username,
        "password": password
    }
    response = requests.post(LOGIN_URL, json=body, timeout=10)
    if response.status_code // 100 != 2:
        message = f"Erreur lors de la connexion : {response.text}"
        raise requests.RequestException(message)
    data = response.json()
    return data

def create_user(username: str, email: str, password: str, permissions: str) -> bool:
    """Création d'un nouvel utilisateur."""
    body = {
        "username": username,
        "email": email,
        "password": password,
        "permissions": permissions
    }
    response = requests.post(CREATE_USER_URL, json=body, timeout=10)
    if response.status_code // 100 != 2:
        message = f"Erreur lors de la création de l'utilisateur : {response.text}"
        raise requests.RequestException(message)
    return True

def change_password(username: str, old_password: str, new_password: str) -> bool:
    """Change le mot de passe d'un utilisateur spécifique."""
    body = {
        "username": username,
        "old_password": old_password,
        "new_password": new_password
    }
    response = requests.post(CHANGE_PASSWORD_URL, json=body, timeout=10)
    if response.status_code // 100 != 2:
        message = f"Erreur lors du changement de mot de passe : {response.text}"
        raise requests.RequestException(message)
    return True

def modify_user(username: str, email: str, permissions: str) -> bool:
    """Modifie les informations d'un utilisateur spécifique."""
    body = {
        "username": username,
        "email": email,
        "permissions": permissions
    }
    response = requests.post(f"{MODIFY_USER_URL}/{quote(username)}", json=body, timeout=10)
    if response.status_code // 100 != 2:
        message = f"Erreur lors de la modification de l'utilisateur : {response.text}"
        raise requests.RequestException(message)
    return True
