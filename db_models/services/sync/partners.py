"""Synchronisation du référentiel local vers les partenaires WooCommerce et Henrri.

Ce module orchestre la propagation des clients et des produits vers les deux
plateformes partenaires au cours de la même opération. Un échec sur une cible
n'empêche pas la synchronisation de l'autre : chaque résultat est retourné et
journalisé indépendamment.

Classes:
- ``TargetResult``: Résultat de synchronisation pour une cible donnée.

Fonctions:
- ``sync_customer``: Synchronise un client vers WooCommerce et Henrri.
- ``sync_all_customers``: Synchronise tous les clients actifs.
- ``sync_all_products``: Synchronise tous les produits actifs.
"""

import json
import logging
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models.objects import Customers
from db_models.objects.objects import GeneralObjects
from db_models.repositories.sync_log import SyncLogRepository
from db_models.services.henrri import sync_customer_to_henrri, sync_product_to_henrri
from db_models.services.woo_commerce.customers import WCCustomersService
from db_models.services.woo_commerce.products import WCProductsService

logger = logging.getLogger(__name__)

WPWC = "wpwc"
HENRRI = "henrri"


@dataclass
class TargetResult:
    """Résultat de synchronisation d'une entité vers une cible partenaire."""

    target: str
    status: str
    external_id: str | None = None
    error: str | None = None


def sync_customer(
    session: Session,
    customer: Customers,
    wc_service: WCCustomersService | None = None,
) -> list[TargetResult]:
    """Synchronise un client vers WooCommerce et Henrri.

    Args:
        session: La session SQLAlchemy courante.
        customer: Le client local à propager.
        wc_service: Le service WooCommerce à utiliser (instancié par défaut).

    Returns:
        list[TargetResult]: Un résultat par cible partenaire.
    """
    sync_repo = SyncLogRepository(session)
    results: list[TargetResult] = []

    wcs = wc_service or WCCustomersService(session, separated_keys=True)
    results.append(
        _run_target(
            target=WPWC,
            operation="create" if customer.wpwc_id is None else "update",
            action=lambda: str(wcs.create_wpwc_customer_if_not_exists(customer).wpwc_id),
            customer_id=customer.id,
            sync_repo=sync_repo,
        )
    )
    results.append(
        _run_target(
            target=HENRRI,
            operation="create" if customer.henrri_id is None else "update",
            action=lambda: str(sync_customer_to_henrri(customer).id),
            customer_id=customer.id,
            sync_repo=sync_repo,
        )
    )
    return results


def sync_all_customers(session: Session) -> list[TargetResult]:
    """Synchronise tous les clients actifs vers WooCommerce et Henrri.

    Args:
        session: La session SQLAlchemy courante.

    Returns:
        list[TargetResult]: Les résultats cumulés de toutes les cibles.
    """
    customers = _get_active_customers(session)
    logger.info("Synchronisation partenaires de %d clients...", len(customers))
    wcs = WCCustomersService(session, separated_keys=True)
    results: list[TargetResult] = []
    for customer in customers:
        results.extend(sync_customer(session, customer, wc_service=wcs))
    session.commit()
    return results


def sync_all_products(session: Session) -> list[TargetResult]:
    """Synchronise le catalogue vers WooCommerce (batch) puis vers Henrri (unitaire).

    Args:
        session: La session SQLAlchemy courante.

    Returns:
        list[TargetResult]: Les résultats cumulés de toutes les cibles.
    """
    sync_repo = SyncLogRepository(session)
    results: list[TargetResult] = []

    wc_service = WCProductsService(session, separated_keys=True)
    try:
        wc_service.export_all_products()
        results.append(TargetResult(target=WPWC, status="success"))
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Échec de l'export du catalogue vers WooCommerce : %s", exc)
        results.append(TargetResult(target=WPWC, status="error", error=str(exc)))

    for product in _get_active_products(session):
        results.append(
            _run_object_target(
                product=product,
                sync_repo=sync_repo,
            )
        )
    session.commit()
    return results


def _run_target(
    *,
    target: str,
    operation: str,
    action,
    customer_id: int,
    sync_repo: SyncLogRepository,
) -> TargetResult:
    """Exécute une synchronisation client vers une cible et journalise l'issue."""
    try:
        external_id = action()
    except Exception as exc:  # pylint: disable=broad-except
        error_message = _format_target_error(target, exc)
        logger.exception(
            "Échec de synchronisation du client %s vers %s : %s",
            customer_id,
            target,
            error_message,
        )
        sync_repo.log_customer(
            customer_id=customer_id,
            external_id=None,
            external_system=target,
            sync_direction="outbound",
            operation=operation,
            sync_status="failed",
            error_message=error_message,
        )
        return TargetResult(target=target, status="error", error=error_message)

    sync_repo.log_customer(
        customer_id=customer_id,
        external_id=external_id,
        external_system=target,
        sync_direction="outbound",
        operation=operation,
        sync_status="success",
    )
    return TargetResult(target=target, status="success", external_id=external_id)


def _format_target_error(target: str, error: Exception) -> str:
    """Formate une erreur partenaire avec le détail Henrri lorsque disponible."""
    message = str(error)
    body = getattr(error, "body", None)
    if target != HENRRI or body is None:
        return message
    details = json.dumps(body, ensure_ascii=False, default=str)
    return f"{message} | Détails de validation Henrri : {details[:1000]}"


def _run_object_target(
    *,
    product: GeneralObjects,
    sync_repo: SyncLogRepository,
) -> TargetResult:
    """Synchronise un produit vers Henrri et journalise l'issue."""
    operation = "create" if product.henrri_id is None else "update"
    try:
        remote = sync_product_to_henrri(product)
    except Exception as exc:  # pylint: disable=broad-except
        error_message = _format_target_error(HENRRI, exc)
        logger.exception(
            "Échec de synchronisation du produit %s vers Henrri : %s",
            product.id,
            error_message,
        )
        sync_repo.log_object(
            entity_type="object",
            entity_id=product.id,
            external_id=None,
            external_system=HENRRI,
            sync_direction="outbound",
            operation=operation,
            sync_status="failed",
            error_message=error_message,
        )
        return TargetResult(target=HENRRI, status="error", error=error_message)

    sync_repo.log_object(
        entity_type="object",
        entity_id=product.id,
        external_id=str(remote.id),
        external_system=HENRRI,
        sync_direction="outbound",
        operation=operation,
        sync_status="success",
    )
    return TargetResult(target=HENRRI, status="success", external_id=str(remote.id))


def _get_active_customers(session: Session) -> Sequence[Customers]:
    """Retourne les clients actifs de la base locale."""
    stmt = select(Customers).where(Customers.is_active.is_(True))
    return session.execute(stmt).scalars().all()


def _get_active_products(session: Session) -> Sequence[GeneralObjects]:
    """Retourne les produits actifs de la base locale."""
    stmt = select(GeneralObjects).where(GeneralObjects.is_active.is_(True))
    return session.execute(stmt).scalars().all()
