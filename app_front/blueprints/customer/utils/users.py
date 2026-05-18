"""Utilitaires pour le module client --> clients uniquement."""

import logging
from typing import Dict, Any
from sqlalchemy import select, or_
from db_models.objects import (
    Customers,
    CustomerMails,
    CustomerPhones,
    CustomerAddresses,
    CustomerParts,
    CustomerPros,
)
from db_models.repositories.customers import CustomersRepository
from db_models.services.woo_commerce.customers import WCCustomersService
from app_front.blueprints.customer.forms import CustomerMainForm
from app_front.config import db_conf

logger = logging.getLogger(__name__)

def form_to_dict(form: CustomerMainForm) -> Dict[str, Any]:
    """Convertit un formulaire WTForms en dictionnaire de données."""
    customer_type = form.customer_type.data

    customer_data = {"customer_type": customer_type}

    if customer_type == "part":
        customer_data["part"] = {
            "civil_title": form.civil_title.data,
            "first_name": form.first_name.data,
            "last_name": form.last_name.data,
            "date_of_birth": form.date_of_birth.data,
        }
    else:
        customer_data["pro"] = {
            "company_name": form.company_name.data,
            "siret_number": form.siret_number.data,
            "vat_number": form.vat_number.data,
        }
    return customer_data


def create_from_dict(customer_data: Dict[str, Any]) -> int:
    """Crée un client à partir d'un dictionnaire de données et retourne son ID."""
    repo = CustomersRepository(db_conf.get_main_session())
    new_customer = repo.create(customer_data)
    return new_customer.id


def get_customer(customer_id: int) -> Dict[str, Any] | None:
    """Récupère un client à partir de son ID et retourne ses données sous forme de dictionnaire.
    Args:
        customer_id (int): L'ID du client à récupérer.
    Returns:
        Dict[str, Any] | None: Les données du client ou None s'il n'existe pas.
    """
    session = db_conf.get_main_session()
    repo = CustomersRepository(session)
    customer = repo.get_by_id(customer_id, complete=True)
    if not customer:
        return None
    data = customer.to_dict()
    # Enrichissement avec les données de synchronisation WooCommerce
    last_sync = None
    if customer.sync_logs:
        wpwc_logs = [log for log in customer.sync_logs if log.external_system == "wpwc"]
        if wpwc_logs:
            last_sync = max(wpwc_logs, key=lambda log: log.synced_at)
    if last_sync:
        data["wpwc_sync_status"] = last_sync.sync_status
        data["wpwc_sync_operation"] = last_sync.operation
        data["wpwc_sync_at"] = last_sync.synced_at.strftime("%d/%m/%Y %H:%M")
        data["wpwc_sync_error"] = last_sync.error_message
    else:
        data["wpwc_sync_status"] = None
        data["wpwc_sync_operation"] = None
        data["wpwc_sync_at"] = None
        data["wpwc_sync_error"] = None
    return data


def push_customer_wc(customer_id: int) -> tuple[bool, str | None]:
    """Pousse un client vers WooCommerce (création ou mise à jour).

    Enregistre un CustomerSyncLog et commite la session.

    Returns:
        (success, error_message)
    """
    session = db_conf.get_main_session()
    repo = CustomersRepository(session)
    customer = repo.get_by_id(customer_id, complete=True)
    if customer is None:
        logger.exception("Client #%d introuvable pour push WooCommerce.", customer_id)
        return False, "Client introuvable"
    svc = WCCustomersService(session)
    success, error = svc.push_customer(customer)
    try:
        session.commit()
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        logger.exception("Erreur commit après push WC (client %d) : %s", customer_id, exc)
        return False, str(exc)
    return success, error


def update_customer_info(
    customer_id: int, data: Dict[str, Any]
) -> Dict[str, Any] | None:
    """Met à jour les informations principales d'un client (part ou pro).
    Args:
        customer_id (int): L'ID du client à modifier.
        data (Dict[str, Any]): Dictionnaire des champs à modifier.
    Returns:
        Dict[str, Any] | None: Les données du client mis à jour ou None si introuvable.
    """
    repo = CustomersRepository(db_conf.get_main_session())
    customer = repo.update_info(customer_id, data)
    return customer.to_dict()


def get_customers_by_name(name: str) -> list[Dict[str, Any]] | None:
    """
    Récupère les clients dont le nom correspond à une recherche de type "like" et retourne
    leurs données sous forme de liste de dictionnaires.
    Args:
        name (str): Le nom à rechercher (peut être partiel).
    Returns:
        list[Dict[str, Any]] | None: Une liste de clients correspondant à la recherche
                                        ou None s'il n'y en a pas.
    """
    repo = CustomersRepository(db_conf.get_main_session())
    customers = repo.get_by_name_like(name, complete=True)
    if not customers:
        return None
    results = []
    for customer in customers:
        customer_dict = customer.to_dict()
        customer_dict["display_name"] = (
            customer.part.first_name + " " + customer.part.last_name
            if customer.customer_type == "part"
            else customer.pro.company_name
        )
        customer_dict["location"] = (
            customer.addresses[0].city if customer.addresses else "N/A"
        )
        results.append(customer_dict)
    return results


def multi_search_filter(
    name: str, email: str, phone: str, cp: str, ville: str, c_type: str
) -> list[Dict[str, Any]]:
    """
    Effectue une recherche multi-critères sur les clients en fonction du nom, de l'e-mail,
    du téléphone, du code postal et de la ville.
    Args:
        name (str): Le nom à rechercher (peut être partiel).
        email (str): L'adresse e-mail à rechercher.
        phone (str): Le numéro de téléphone à rechercher.
        cp (str): Le code postal à rechercher.
        ville (str): La ville à rechercher.
        c_type (str): Le type de client à rechercher ('part' | 'pro').
    Returns:
        list[Dict[str, Any]]: Une liste de clients correspondant à la recherche.
    """
    session = db_conf.get_main_session()
    filters = []

    # Recherche par nom (partiel)
    if name := name.strip():
        name_filter = or_(
            Customers.part.has(CustomerParts.first_name.ilike(f"%{name}%")),
            Customers.part.has(CustomerParts.last_name.ilike(f"%{name}%")),
            Customers.pro.has(CustomerPros.company_name.ilike(f"%{name}%")),
        )
        filters.append(name_filter)
    # Recherche par e-mail
    if email := email.strip():
        email_filter = Customers.emails.any(CustomerMails.email.ilike(f"%{email}%"))
        filters.append(email_filter)
    # Recherche par téléphone
    if phone := phone.strip():
        phone_filter = Customers.phones.any(
            CustomerPhones.phone_number.ilike(f"%{phone}%")
        )
        filters.append(phone_filter)
    # Recherche par code postal
    if cp := cp.strip():
        cp_filter = Customers.addresses.any(CustomerAddresses.postal_code == cp)
        filters.append(cp_filter)
    # Recherche par ville
    if ville := ville.strip():
        ville_filter = Customers.addresses.any(
            CustomerAddresses.city.ilike(f"%{ville}%")
        )
        filters.append(ville_filter)
    # Recherche par type de client
    if c_type in ("part", "pro"):
        type_filter = Customers.customer_type == c_type
        filters.append(type_filter)
    stmt = select(Customers).where(*filters)
    results = session.execute(stmt).scalars().all()

    customers_list = []

    for customer in results:
        customer_dict = customer.to_dict()
        customer_dict["display_name"] = (
            customer.part.first_name + " " + customer.part.last_name
            if customer.customer_type == "part"
            else customer.pro.company_name
        )
        customer_dict["location"] = (
            customer.addresses[0].city if customer.addresses else "N/A"
        )
        customer_dict["email"] = customer.emails[0].email if customer.emails else "N/A"
        customer_dict["phone"] = (
            customer.phones[0].phone_number if customer.phones else "N/A"
        )
        customers_list.append(customer_dict)

    return customers_list
