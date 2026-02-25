"""Utilitaires pour le module client --> Téléphones uniquement."""

from typing import Dict, Any, List
from db_models.repositories.customers import CustomersRepository, CustomerPhonesRepository
from app_front.config.db_conf import get_main_session

def get_phones(customer_id: int) -> List[Dict[str, Any]]:
    """Récupère la liste des téléphones d'un client.
    Args:
        customer_id (int): L'ID du client dont on veut les téléphones.
    Returns:
        List[Dict[str, Any]]: Liste des téléphones du client sous forme de dictionnaires.
    """
    repo = CustomersRepository(get_main_session())
    customer = repo.get_by_id(customer_id, complete=True)
    if not customer:
        return []
    return [phone.to_dict() for phone in customer.phones]

def add_phone(customer_id: int, phone_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """Ajoute un téléphone à un client.
    Args:
        customer_id (int): L'ID du client auquel ajouter le téléphone.
        phone_data (Dict[str, Any]): Dictionnaire des champs du téléphone à ajouter.
    Returns:
        Dict[str, Any] | None: Les données du téléphone ajouté ou None si échec.
    """
    repo = CustomerPhonesRepository(get_main_session())
    phone_data["customer_id"] = customer_id
    phone = repo.add_phone(phone_data)
    if not phone:
        return None

    return phone.to_dict()

def update_phone(customer_id: int, phone_id: int,
                 phone_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """Met à jour un téléphone d'un client.
    Args:
        customer_id (int): L'ID du client auquel appartient le téléphone.
        phone_id (int): L'ID du téléphone à modifier.
        phone_data (Dict[str, Any]): Dictionnaire des champs du téléphone à modifier.
    Returns:
        Dict[str, Any] | None: Les données du téléphone mis à jour ou None si introuvable.
    """
    repo = CustomerPhonesRepository(get_main_session())
    try:
        phone = repo.update_phone(customer_id, phone_id, phone_data)
        return phone.to_dict()
    except ValueError as e:
        raise ValueError(f"Téléphone #{phone_id} introuvable.") from e
    except (KeyError, TypeError, AttributeError) as e:
        raise ValueError("Données de téléphone invalides.") from e

def delete_phone(phone_id: int) -> bool:
    """Supprime un téléphone d'un client en le marquant comme inactive.
    Args:
        phone_id (int): L'ID du téléphone à supprimer.
    Returns:
        bool: True si la suppression a réussi, False sinon.
    """
    repo = CustomerPhonesRepository(get_main_session())
    try:
        repo.delete_phone(phone_id)
        return True
    except ValueError:
        return False
