"""Synchronisation des entités locales vers Henrri.

Ce module centralise les opérations d'upsert (POST si l'entité est inconnue chez
Henrri, PUT sinon) et le report en base des identifiants retournés par l'API.

Fonctions:
- ``sync_customer_to_henrri``: Synchronise un client et ses identifiants associés.
- ``sync_product_to_henrri``: Synchronise un produit.
"""

import logging
from typing import Any

from henrri_connect.models import Contact, Customer, Item

from .customers import HenrriCustomersService
from .products import HenrriProductsService

logger = logging.getLogger(__name__)


def sync_customer_to_henrri(
    customer: Any,
    service: HenrriCustomersService | None = None,
) -> Customer:
    """Crée ou met à jour un client chez Henrri et reporte les identifiants reçus.

    Args:
        customer: Le client local à synchroniser.
        service: Le service Henrri à utiliser (instancié par défaut).

    Returns:
        Customer: Le client tel que retourné par Henrri.

    Raises:
        ValueError: Si le client n'a pas d'adresse de facturation active exploitable.
    """
    hcs = service or HenrriCustomersService()
    remote = hcs.upsert_customer(
        Customer(**customer.to_dict_henrri(with_contact=False)), customer.henrri_id
    )
    if not remote:
        raise ValueError("Le client Henrri n'a pas été créé ou mis à jour.")
    _apply_henrri_customer_ids(customer, remote)
    if remote.id is None:
        raise ValueError("Le client Henrri n'a pas d'identifiant après synchronisation.")
    remote_contact = hcs.upsert_contact(
        remote.id,
        Contact(**customer.to_dict_henrri()["contacts"][0]),
        _get_henrri_contact_id(customer),
    )
    _apply_henrri_contact_id(customer, remote_contact.id)
    return remote


def sync_product_to_henrri(
    product: Any,
    service: HenrriProductsService | None = None,
) -> Item:
    """Crée ou met à jour un produit chez Henrri et reporte l'identifiant reçu.

    Args:
        product: Le produit local à synchroniser.
        service: Le service Henrri à utiliser (instancié par défaut).

    Returns:
        Item: Le produit tel que retourné par Henrri.
    """
    hps = service or HenrriProductsService()
    remote = hps.upsert_product(Item(**product.to_dict_henrri()), product.henrri_id)
    product.henrri_id = remote.id
    return remote


def _apply_henrri_customer_ids(customer: Any, remote: Customer) -> None:
    """Reporte en base les identifiants Henrri du client, de son adresse et de son contact."""
    customer.henrri_id = str(remote.id)

    remote_address_id = getattr(remote.address, "id", None)
    if remote_address_id is not None:
        try:
            customer.get_henrri_billing_address().henrri_id = remote_address_id
        except ValueError:
            logger.warning(
                "Client %s sans adresse de facturation active lors du report "
                "de l'identifiant Henrri",
                customer.id,
            )

def _get_henrri_contact_id(customer: Any) -> int | None:
    """Retourne l'identifiant Henrri du contact local lorsqu'il existe."""
    if customer.pro:
        return customer.pro.contact_henrri_id
    if customer.part:
        return customer.part.contact_henrri_id
    return None


def _apply_henrri_contact_id(customer: Any, contact_id: int | None) -> None:
    """Reporte l'identifiant du contact Henrri synchronisé."""
    if contact_id is None:
        return
    if customer.pro:
        customer.pro.contact_henrri_id = contact_id
    elif customer.part:
        customer.part.contact_henrri_id = contact_id
