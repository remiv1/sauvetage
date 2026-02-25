"""Utilitaires pour le module client --> Emails uniquement."""

from typing import Dict, Any, List
from db_models.repositories.customers import CustomersRepository, CustomerMailsRepository
from app_front.config.db_conf import get_main_session

def get_emails(customer_id: int) -> List[Dict[str, Any]]:
    """Récupère la liste des emails d'un client.
    Args:
        customer_id (int): L'ID du client dont on veut les emails.
    Returns:
        List[Dict[str, Any]]: Liste des emails du client sous forme de dictionnaires.
    """
    repo = CustomersRepository(get_main_session())
    customer = repo.get_by_id(customer_id, complete=True)
    if not customer:
        return []
    return [email.to_dict() for email in customer.emails]

def add_email(customer_id: int, email_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """Ajoute un email à un client.
    Args:
        customer_id (int): L'ID du client auquel ajouter l'email.
        email_data (Dict[str, Any]): Dictionnaire des champs de l'email à ajouter.
    Returns:
        Dict[str, Any] | None: Les données de l'email ajouté ou None si échec.
    """
    repo = CustomerMailsRepository(get_main_session())
    email_data["customer_id"] = customer_id
    email = repo.add_email(email_data)
    if not email:
        return None

    return email.to_dict()

def update_email(customer_id: int, email_id: int, email_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """Met à jour un email d'un client.
    Args:
        customer_id (int): L'ID du client auquel appartient l'email.
        email_id (int): L'ID de l'email à modifier.
        email_data (Dict[str, Any]): Dictionnaire des champs de l'email à modifier.
    Returns:
        Dict[str, Any] | None: Les données de l'email mis à jour ou None si introuvable.
    """
    repo = CustomerMailsRepository(get_main_session())
    try:
        email = repo.update_email(customer_id, email_id, email_data)
        return email.to_dict()
    except ValueError as e:
        raise ValueError(f"E-mail #{email_id} introuvable.") from e
    except (KeyError, TypeError, AttributeError) as e:
        raise ValueError("Données d'e-mail invalides.") from e

def delete_email(email_id: int) -> bool:
    """Supprime un email d'un client en le marquant comme inactive.
    Args:
        email_id (int): L'ID de l'email à supprimer.
    Returns:
        bool: True si la suppression a réussi, False sinon.
    """
    repo = CustomerMailsRepository(get_main_session())
    try:
        repo.delete_email(email_id)
        return True
    except ValueError:
        return False
