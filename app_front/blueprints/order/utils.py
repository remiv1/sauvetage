"""Utilitaires pour les commandes, utilisés par les routes et tests."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from app_front.config import db_conf
from app_front.blueprints.order.utils_henrri import (
    HenrriSyncError,
    create_invoice as create_henrri_invoice,
    find_invoice as find_henrri_invoice,
    get_invoice_pdf as get_henrri_invoice_pdf,
)
from db_models.objects import Order, OrderLine, CustomerAddresses
from db_models.objects import InventoryMovements
from db_models.repositories.orders import OrdersRepository
from db_models.repositories.customers import CustomersRepository
from db_models.repositories.invoices import InvoiceRepository, Invoice, InvoiceLine
from db_models.repositories.shipments import ShipmentsRepository, ShipmentLine
from db_models.repositories.objects.objects import ObjectsRepository, GeneralObjects
from db_models.services.woo_commerce.orders import WCOrdersService

logger = logging.getLogger(__name__)


# ── Libellés statuts ──────────────────────────────────────────────────────

STATUS_LABELS: Dict[str, str] = {
    "draft": "Brouillon",
    "partial_invoiced": "Partiellement facturée",
    "invoiced": "Facturée",
    "partial_shipped": "Partiellement expédiée",
    "shipped": "Expédiée",
    "cancelled": "Annulée",
    "returned": "Retournée",
}

STATUS_BADGE_CLASS: Dict[str, str] = {
    "draft": "badge-draft",
    "partial_invoiced": "badge-warning",
    "invoiced": "badge-info",
    "partial_shipped": "badge-warning",
    "shipped": "badge-success",
    "cancelled": "badge-danger",
    "returned": "badge-danger",
}

_ORDER_NOT_FOUND = "Commande introuvable"
_CUSTOMER_NOT_FOUND = "Client introuvable"


def _customer_display_name(customer) -> str:
    """Construit le nom d'affichage d'un client."""
    if customer.customer_type == "part" and customer.part:
        return f"{customer.part.first_name} {customer.part.last_name}"
    if customer.customer_type == "pro" and customer.pro:
        return customer.pro.company_name
    return f"Client #{customer.id}"


def _sorted_active_addresses(customer) -> list[CustomerAddresses]:
    """Retourne les adresses actives d'un client triées par identifiant."""
    addresses = [a for a in (customer.addresses or []) if a.is_active]
    return sorted(addresses, key=lambda address: address.id)


def _find_default_billing_address(customer) -> CustomerAddresses | None:
    """Retourne la première adresse de facturation active du client."""
    return next(
        (address for address in _sorted_active_addresses(customer) if address.is_billing),
        None,
    )


def _find_shipping_addresses(customer) -> list[CustomerAddresses]:
    """Retourne les adresses de livraison actives du client."""
    return [
        address
        for address in _sorted_active_addresses(customer)
        if address.is_shipping
    ]


def _shipping_options_for_customer(customer) -> list[dict[str, Any]]:
    """Construit les options de select pour les adresses de livraison du client."""
    return [
        {
            "id": address.id,
            "label": _format_address_option_label(address.to_dict()),
        }
        for address in _find_shipping_addresses(customer)
    ]


def _order_to_list_dict(order: Order) -> Dict[str, Any]:
    """Convertit une commande en dict pour la vue tableau."""
    total_ht = 0.0
    for line in (order.order_lines or []):
        if line.status == "cancelled":
            continue
        price = float(line.unit_price) * line.quantity
        discount_amount = price * float(line.discount) / 100
        total_ht += price - discount_amount
    return {
        "id": order.id,
        "reference": order.reference,
        "customer_id": order.customer_id,
        "customer_name": _customer_display_name(order.customer) if order.customer else "—",
        "status": order.status,
        "status_label": STATUS_LABELS.get(order.status, order.status),
        "status_badge": STATUS_BADGE_CLASS.get(order.status, ""),
        "nb_lines": len(order.order_lines) if order.order_lines else 0,
        "total_ht": round(total_ht, 2),
        "created_at": order.created_at.strftime("%d/%m/%Y %H:%M") if order.created_at else "—",
    }


def _may_be_invoiced(line: Optional[OrderLine], item: Dict[str, Any]) -> OrderLine:
    """
    Retourne la ligne si elle existe et est en statut "draft", sinon lève une exception.
    args:
    - line: la ligne de commande à vérifier
    - item: dict avec les données de la ligne à facturer,
            doit contenir "order_line_id" et "quantity"
    """
    if line is None:
        raise ValueError(f"Ligne {item['order_line_id']} introuvable.")
    if line.status != "draft":
        raise ValueError(f"La ligne {line.id} n'est pas en brouillon.")
    if not _has_valid_quantity_sign(line.quantity, item["quantity"]):
        raise ValueError(f"Quantité invalide pour la ligne {line.id}.")
    return line


def _has_valid_quantity_sign(available: int, requested: int) -> bool:
    """Vérifie que la quantité demandée garde le signe et ne dépasse pas le disponible."""
    if available > 0:
        return 1 <= requested <= available
    return available <= requested <= -1

# ── Recherche paginée ────────────────────────────────────────────────────

def search_orders_paginated(    # pylint: disable=too-many-arguments
    *,
    reference: str | None = None,
    customer_name: str | None = None,
    status: str | list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Recherche paginée des commandes via le repository.

    Returns:
        Dict avec clés: items (list de dicts), total, page, per_page.
    """
    dt_from = None
    dt_to = None
    if date_from:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    if date_to:
        dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )

    session = db_conf.get_main_session()
    repo = OrdersRepository(session)
    result = repo.search_paginated(
        reference=reference,
        customer_name=customer_name,
        status=status,
        date_from=dt_from,
        date_to=dt_to,
        page=page,
        per_page=per_page,
    )
    result["items"] = [_order_to_list_dict(o) for o in result["items"]]
    return result


# ── Lecture détail ───────────────────────────────────────────────────────

def _build_order_line_dto(line: OrderLine) -> dict[str, Any]:
    """Convertit une ligne ORM en dict de présentation."""
    if line.general_object:
        article_name = (
            getattr(line.general_object, "name", None)
            or f"Article #{line.general_object_id}"
        )
    else:
        article_name = f"Article #{line.general_object_id}"
    price = float(line.unit_price) * line.quantity
    discount_amount = price * float(line.discount) / 100
    ld = line.to_dict()
    ld["article_name"] = article_name
    ld["variation_name"] = line.object_variation.name if line.object_variation else None
    ld["status_label"] = STATUS_LABELS.get(line.status, line.status)
    ld["line_total_ht"] = round(price - discount_amount, 2)
    return ld


def _compute_order_totals(active_lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcule total HT, ventilation TVA par taux et total TTC."""
    vat_accumulator: dict[float, float] = {}
    total_ht = 0.0
    for ld in active_lines:
        ht = ld["line_total_ht"]
        rate = round(float(ld.get("vat_rate") or 0), 2)
        total_ht += ht
        vat_accumulator[rate] = vat_accumulator.get(rate, 0.0) + ht * rate / 100
    vat_breakdown = [
        {"rate": rate, "amount": round(amount, 2)}
        for rate, amount in sorted(vat_accumulator.items())
    ]
    return {
        "total_ht": round(total_ht, 2),
        "vat_breakdown": vat_breakdown,
        "total_ttc": round(total_ht + sum(v["amount"] for v in vat_breakdown), 2),
    }


def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """Récupère une commande par son ID avec toutes ses relations.

    Returns:
        Dict complet de la commande, ou None.
    """
    session = db_conf.get_main_session()
    order = OrdersRepository(session).get_by_id(order_id)
    if order is None:
        return None

    data = _order_to_list_dict(order)

    # Adresses
    data["invoice_address"] = (
        order.invoice_address.to_dict() if order.invoice_address else None
    )
    data["delivery_address"] = (
        order.delivery_address.to_dict() if order.delivery_address else None
    )
    data["invoice_address_id"] = order.invoice_address_id
    data["delivery_address_id"] = order.delivery_address_id
    data["shipping_addresses"] = (
        _shipping_options_for_customer(order.customer) if order.customer else []
    )

    # Lignes (toutes + actives uniquement)
    all_lines = [_build_order_line_dto(line) for line in (order.order_lines or [])]
    data["all_lines"] = all_lines
    data["lines"] = [ld for ld in all_lines if ld.get("status") != "cancelled"]
    data["cancelled_lines"] = [
        ld for ld in all_lines if ld.get("status") == "cancelled"
    ]
    data |= _compute_order_totals(data["lines"])

    # Documents liés
    data["invoices"] = [
        inv.to_dict() | _get_sync_data_for_invoice(inv)
        for inv in InvoiceRepository(session).get_by_order_id(order_id)
    ]
    data["shipments"] = [
        s.to_dict()
        for s in ShipmentsRepository(session).get_by_order_id(order_id)
    ]
    data["alerts"] = [
        {
            "code": alert.code,
            "message": alert.message,
            "created_at": alert.created_at.strftime("%d/%m/%Y %H:%M"),
        }
        for alert in (order.alerts or [])
        if not alert.is_resolved
    ]
    data["is_return"] = order.return_of_order_id is not None

    # Flags pour boutons facturer / expédier
    order_lines = order.order_lines or []
    data["has_uninvoiced_lines"] = any(l.status == "draft" for l in order_lines)
    data["has_unshipped_invoiced_lines"] = any(l.status == "invoiced" for l in order_lines)

    # Synchronisation WooCommerce
    data |= _get_sync_data_for_order(order)
    return data

def _get_sync_data_for_order(order: Order) -> Dict[str, Any]:
    """Extrait les données de synchronisation WooCommerce d'une commande."""
    data: dict[str, Any] = {"wpwc_id": order.wpwc_id}
    last_sync = None
    if order.sync_logs:
        wpwc_logs = [
            log for log in order.sync_logs if log.external_system == "wpwc"
        ]
        if wpwc_logs:
            last_sync = max(wpwc_logs, key=lambda log: log.synced_at)
    if last_sync:
        data["wpwc_sync_status"] = last_sync.sync_status       # success / failed / pending
        data["wpwc_sync_operation"] = last_sync.operation      # create / update / delete
        data["wpwc_sync_at"] = last_sync.synced_at.strftime("%d/%m/%Y %H:%M")
        data["wpwc_sync_error"] = last_sync.error_message
    else:
        data["wpwc_sync_status"] = None
        data["wpwc_sync_operation"] = None
        data["wpwc_sync_at"] = None
        data["wpwc_sync_error"] = None
    return data


def _get_sync_data_for_invoice(invoice: Invoice) -> Dict[str, Any]:
    """Extrait les données de synchronisation Henrri d'une facture."""
    data: dict[str, Any] = {"henrri_id": invoice.henrri_id}
    last_sync = _get_last_henrri_sync_log(invoice)
    if last_sync:
        data["henrri_sync_status"] = last_sync.sync_status
        data["henrri_sync_operation"] = last_sync.operation
        data["henrri_sync_at"] = last_sync.synced_at.strftime("%d/%m/%Y %H:%M")
        data["henrri_sync_error"] = last_sync.error_message
    else:
        data["henrri_sync_status"] = None
        data["henrri_sync_operation"] = None
        data["henrri_sync_at"] = None
        data["henrri_sync_error"] = None
    return data


def _get_last_henrri_sync_log(invoice: Invoice):
    """Retourne le dernier log de synchronisation Henrri d'une facture."""
    if not invoice.sync_logs:
        return None
    henrri_logs = [
        log for log in invoice.sync_logs if log.external_system == "henrri"
    ]
    if not henrri_logs:
        return None
    return max(henrri_logs, key=lambda log: log.synced_at)


def _format_henrri_sync_error(exc: HenrriSyncError) -> str:
    """Construit un message d'erreur Henrri exploitable dans l'interface."""
    parts = [str(exc)]
    if exc.details:
        if isinstance(exc.details, (dict, list)):
            details = json.dumps(exc.details, ensure_ascii=False)
        else:
            details = str(exc.details)
        parts.append(details)
    return " | ".join(parts)


def _sync_invoice_with_henrri(
    invoice: Invoice,
    invoice_repo: InvoiceRepository,
) -> Invoice:
    """Synchronise une facture avec Henrri et journalise le résultat."""
    try:
        _, synced_invoice = create_henrri_invoice(invoice)
    except HenrriSyncError as exc:
        error_message = _format_henrri_sync_error(exc)
        invoice_repo.add_sync_log(
            invoice,
            sync_status="failed",
            error_message=error_message,
        )
        logger.warning(
            "Facture %s créée localement mais non synchronisée Henrri: %s",
            invoice.id,
            error_message,
        )
        raise

    synced_invoice.last_synced_at = datetime.now(timezone.utc)
    invoice_repo.add_sync_log(
        synced_invoice,
        external_id=synced_invoice.henrri_id,
        sync_status="success",
    )
    return synced_invoice


# ── Création ─────────────────────────────────────────────────────────────

def create_order(customer_id: int, delivery_address_id: int) -> Dict[str, Any]:
    """Crée une commande avec facturation automatique et livraison choisie."""
    session = db_conf.get_main_session()
    customer_repo = CustomersRepository(session)
    customer = customer_repo.get_by_id(customer_id, complete=True)
    if customer is None:
        raise ValueError(_CUSTOMER_NOT_FOUND)

    billing_address = _find_default_billing_address(customer)
    if billing_address is None:
        raise ValueError("Aucune adresse de facturation active disponible pour ce client.")

    shipping_addresses = _find_shipping_addresses(customer)
    selected_shipping = next(
        (address for address in shipping_addresses if address.id == delivery_address_id),
        None,
    )
    if selected_shipping is None:
        raise ValueError("Adresse de livraison invalide pour ce client.")

    repo = OrdersRepository(session)
    order = repo.create_order(
        customer_id=customer_id,
        invoice_address_id=billing_address.id,
        delivery_address_id=selected_shipping.id,
        create_source="backoffice",
    )
    return {"id": order.id, "reference": order.reference}


def _format_address_option_label(address: Dict[str, Any]) -> str:
    """Formatte une adresse en libellé lisible pour un select HTML."""
    address_name = address.get("address_name") or "Adresse"
    address_line1 = address.get("address_line1") or ""
    city = address.get("city") or ""
    postal_code = address.get("postal_code") or ""
    return f"{address_name} - {address_line1} - {postal_code} {city}".strip()


def get_customer_order_addresses(customer_id: int) -> Dict[str, Any]:
    """Retourne les adresses de commande disponibles pour un client."""
    session = db_conf.get_main_session()
    customer_repo = CustomersRepository(session)
    customer = customer_repo.get_by_id(customer_id, complete=True)
    if customer is None:
        raise ValueError(_CUSTOMER_NOT_FOUND)

    billing_address = _find_default_billing_address(customer)
    shipping_addresses = _find_shipping_addresses(customer)

    return {
        "billing": billing_address.to_dict() if billing_address else None,
        "shipping": [
            {
                "id": address.id,
                "label": _format_address_option_label(address.to_dict()),
            }
            for address in shipping_addresses
        ],
    }


def update_order_delivery_address(order_id: int, delivery_address_id: int) -> Dict[str, Any]:
    """Met à jour l'adresse de livraison si la commande est en brouillon."""
    session = db_conf.get_main_session()
    repo = OrdersRepository(session)
    order = repo.get_by_id(order_id)
    if order is None:
        raise ValueError(_ORDER_NOT_FOUND)
    if order.status != "draft":
        raise ValueError(
            "L'adresse de livraison n'est modifiable que pour une commande en brouillon."
        )

    updated_order = repo.update_delivery_address(
        order,
        delivery_address_id=delivery_address_id,
        update_source="backoffice",
    )
    return {
        "id": updated_order.id,
        "delivery_address_id": updated_order.delivery_address_id,
    }


def add_order_line(     # pylint: disable=too-many-arguments
    order_id: int,
    *,
    general_object_id: int,
    quantity: int,
    unit_price: float,
    discount: float = 0,
    vat_rate: float,
    object_variation_id: int | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Ajoute une ligne à une commande existante et crée un mouvement de réservation.

    Lorsque l'article a plusieurs prix valides, la commande est découpée en plusieurs
    lignes de commande, une par tarif actif.
    """
    session = db_conf.get_main_session()
    repo = OrdersRepository(session)
    order = repo.get_by_id(order_id)
    if order is None:
        raise ValueError(_ORDER_NOT_FOUND)
    created_lines = repo.add_line(
        order,
        general_object_id=general_object_id,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        vat_rate=vat_rate,
        object_variation_id=object_variation_id,
        create_source="backoffice",
    )
    if isinstance(created_lines, list):
        for line in created_lines:
            movement = InventoryMovements(
                general_object_id=general_object_id,
                movement_type="reserved",
                quantity=line.quantity,
                price_at_movement=float(line.unit_price),
                source="order",
                destination=f"CMD-{order_id}",
                notes=f"Réservation commande {order.reference}",
            )
            session.add(movement)
        return [line.to_dict() for line in created_lines]

    movement = InventoryMovements(
        general_object_id=general_object_id,
        movement_type="reserved",
        quantity=quantity,
        price_at_movement=unit_price,
        source="order",
        destination=f"CMD-{order_id}",
        notes=f"Réservation commande {order.reference}",
    )
    session.add(movement)
    return created_lines.to_dict()


def remove_order_line(order_id: int, line_id: int) -> bool:
    """Annule une ligne de commande (soft delete) et crée un mouvement d'annulation."""
    session = db_conf.get_main_session()
    repo = OrdersRepository(session)
    order = repo.get_by_id(order_id)
    if order is None:
        raise ValueError(_ORDER_NOT_FOUND)
    line = next((l for l in order.order_lines if l.id == line_id), None)
    if line is None:
        raise ValueError("Ligne introuvable")
    # Annuler le mouvement de réservation
    movement = InventoryMovements(
        general_object_id=line.general_object_id,
        movement_type="reserved",
        quantity=-line.quantity,
        price_at_movement=float(line.unit_price),
        source="order",
        destination=f"CMD-{order_id}",
        notes=f"Annulation réservation commande {order.reference}",
    )
    session.add(movement)
    result = repo.remove_line(line)
    return result


def cancel_order(order_id: int) -> Dict[str, Any]:
    """Annule une commande (passe en statut 'cancelled').

    Returns:
        Dict de la commande mise à jour.
    """
    session = db_conf.get_main_session()
    repo = OrdersRepository(session)
    order = repo.get_by_id(order_id)
    if order is None:
        raise ValueError(_ORDER_NOT_FOUND)
    if order.status in ("cancelled", "returned"):
        raise ValueError("Commande déjà annulée ou retournée")
    order = repo.cancel_order(order, update_source="backoffice")
    return _order_to_list_dict(order)


def create_return_order(order_id: int) -> Order:
    """Crée ou retrouve la commande de retour déclenchée par une alerte WooCommerce."""
    session = db_conf.get_main_session()
    repo = OrdersRepository(session)
    source_order = repo.get_by_id(order_id)
    if source_order is None:
        raise ValueError(_ORDER_NOT_FOUND)
    alert = next(
        (
            item
            for item in source_order.alerts
            if item.code == "credit_note_required" and not item.is_resolved
        ),
        None,
    )
    if alert is None:
        raise ValueError("Aucune alerte d'avoir ouverte pour cette commande.")

    return_order = repo.create_return_order(source_order)
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    session.commit()
    return return_order


def invoice_order(order_id: int, line_items: list[Dict[str, Any]]) -> Invoice:
    """Crée une facture pour les lignes sélectionnées avec les quantités spécifiées.

    Args:
        order_id: ID de la commande.
        line_items: Liste de dicts {order_line_id: int, quantity: int}.
    Returns:
        Invoice créée (objet SQLAlchemy).
    """
    if not line_items:
        raise ValueError("Aucune ligne sélectionnée pour la facturation.")

    session = db_conf.get_main_session()
    order_repo = OrdersRepository(session)
    order = order_repo.get_by_id(order_id)
    if order is None:
        raise ValueError(_ORDER_NOT_FOUND)
    if order.customer_id is None:
        raise ValueError("Commande sans client de rattachement.")
    if order.status == "invoiced":
        raise ValueError(
            "Commande déjà facturée. Pour créer une facture d'avoir, utilisez le flux dédié."
        )

    # Valider les lignes et enrichir avec les prix
    requested_ids = {item["order_line_id"] for item in line_items}
    line_objects = [l for l in order.order_lines if l.id in requested_ids]

    invoice_lines = []
    for line in line_objects:
        if line.status != "draft":
            raise ValueError(f"La ligne {line.id} n'est pas en brouillon.")
        qty = next(item["quantity"] for item in line_items if item["order_line_id"] == line.id)
        if not _has_valid_quantity_sign(line.quantity, qty):
            raise ValueError(f"Quantité invalide pour la ligne {line.id}.")
        invoice_lines.append(
            InvoiceLine(
                order_line_id=line.id,
                reference=line.general_object.ean13,
                description=line.general_object.name,
                quantity=qty,
                unit_price=float(line.unit_price),
                discount=float(line.discount),
                vat_rate=float(line.vat_rate),
            )
        )

    # Créer la facture en local
    inv_repo = InvoiceRepository(session)
    local_invoice = inv_repo.create_invoice(
        order_id=order_id,
        customer_id=order.customer_id,
        line_items=invoice_lines,
        create_source="backoffice",
    )

    try:
        local_invoice = _sync_invoice_with_henrri(local_invoice, inv_repo)
    except HenrriSyncError:
        pass

    # Mettre à jour le statut des lignes de commande
    for line in line_objects:
        qty_invoiced = next(
            item["quantity"] for item in line_items if item["order_line_id"] == line.id
            )

        if line.quantity != qty_invoiced:
            order_repo.cut_line_for_invoice(line, qty_invoiced)

        line.status = "invoiced"
    session.commit()

    # Recalculer le statut de la commande
    _recalculate_order_status(order, order_repo)
    return local_invoice


def retry_henrri_invoice(invoice_id: int) -> Invoice:
    """Relance la création Henrri d'une facture locale non synchronisée.
    
    Si la facture est déjà créée sur Henrri (henrri_id défini), relance juste
    la création des lignes et la finalisation.
    """
    session = db_conf.get_main_session()
    invoice_repo = InvoiceRepository(session)
    invoice = invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise ValueError("Facture introuvable")

    # Vérifie d'abord l'état réel côté Henrri pour éviter une relance inutile.
    sync_candidates: list[str] = []
    if invoice.henrri_id:
        sync_candidates.append(str(invoice.henrri_id))
    if invoice.sync_logs:
        for log in sorted(invoice.sync_logs, key=lambda item: item.synced_at, reverse=True):
            if log.external_system == "henrri" and log.external_id:
                sync_candidates.append(str(log.external_id))
    seen_candidates = set()
    for external_id in sync_candidates:
        if external_id in seen_candidates:
            continue
        seen_candidates.add(external_id)
        try:
            remote_invoice = find_henrri_invoice(external_id)
        except HenrriSyncError:
            continue

        if remote_invoice.finalized:
            invoice.henrri_id = str(remote_invoice.id) \
                if remote_invoice.id is not None \
                else external_id
            invoice.last_synced_at = datetime.now(timezone.utc)
            invoice_repo.add_sync_log(
                invoice,
                external_id=invoice.henrri_id,
                operation="update",
                sync_status="success",
            )
            session.commit()
            logger.info(
                "Facture %s déjà synchronisée/finalisée sur Henrri (id externe %s).",
                invoice.id,
                invoice.henrri_id,
            )
            return invoice

    last_sync = _get_last_henrri_sync_log(invoice)
    if last_sync and last_sync.sync_status == "success":
        invoice.last_synced_at = datetime.now(timezone.utc)
        invoice_repo.add_sync_log(
            invoice,
            external_id=invoice.henrri_id,
            operation="update",
            sync_status="success",
        )
        session.commit()
        logger.info(
            "Facture %s déjà finalisée sur Henrri, journalisation d'un succès idempotent.",
            invoice.id,
        )
        return invoice

    try:
        synced_invoice = _sync_invoice_with_henrri(invoice, invoice_repo)
    except HenrriSyncError as exc:
        session.commit()
        raise ValueError(_format_henrri_sync_error(exc)) from exc

    session.commit()
    return synced_invoice


def download_henrri_invoice_pdf(invoice_id: int) -> tuple[bytes, str]:
    """Télécharge le PDF d'une facture synchronisée sur Henrri.

    Args:
        invoice_id: Identifiant de la facture locale.

    Returns:
        Tuple contenant le PDF binaire et le nom de fichier.

    Raises:
        ValueError: Si la facture n'est pas trouvée, pas finalisée ou inaccessible.
    """
    session = db_conf.get_main_session()
    invoice_repo = InvoiceRepository(session)
    invoice = invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise ValueError("Facture introuvable")

    if not invoice.henrri_id:
        raise ValueError("Facture non synchronisée sur Henrri")

    last_sync = _get_last_henrri_sync_log(invoice)
    if last_sync is None or last_sync.sync_status != "success":
        raise ValueError("Facture non finalisée sur Henrri")

    try:
        pdf_bytes = get_henrri_invoice_pdf(str(invoice.henrri_id))
    except HenrriSyncError as exc:
        raise ValueError(_format_henrri_sync_error(exc)) from exc

    return pdf_bytes, f"{invoice.reference}.pdf"


def ship_order(
    order_id: int,
    line_items: list[Dict[str, Any]],
    carrier: str,
    tracking_number: str | None = None,
) -> Dict[str, Any]:
    """Crée un envoi pour les lignes sélectionnées avec les quantités spécifiées.

    Args:
        order_id: ID de la commande.
        line_items: Liste de dicts {order_line_id: int, quantity: int}.
        carrier: Transporteur.
        tracking_number: Numéro de suivi (optionnel).
    Returns:
        Dict de l'envoi créé.
    """
    if not line_items:
        raise ValueError("Aucune ligne sélectionnée pour l'expédition.")

    session = db_conf.get_main_session()
    order_repo = OrdersRepository(session)
    order = order_repo.get_by_id(order_id)
    if order is None:
        raise ValueError(_ORDER_NOT_FOUND)

    line_objects: List[OrderLine] = [
        l for l in (order.order_lines or []) \
            if l.id in {item["order_line_id"] for item in line_items}]

    shipment_lines: List[ShipmentLine] = []
    for line in line_objects:
        if line.status != "invoiced":
            raise ValueError(f"La ligne {line.id} n'est pas facturée.")
        qty = next(item["quantity"] for item in line_items if item["order_line_id"] == line.id)
        if not _has_valid_quantity_sign(line.quantity, qty):
            raise ValueError(f"Quantité invalide pour la ligne {line.id}.")
        shipment_lines.append(
            ShipmentLine(
                order_line_id=line.id,
                quantity=qty,
            )
        )

    # Créer l'expédition
    ship_repo = ShipmentsRepository(session)
    shipment = ship_repo.create_shipment(
        order_id=order_id,
        carrier=carrier,
        tracking_number=tracking_number,
        line_items=shipment_lines,
        create_source="backoffice",
    )

    # Mettre à jour le statut des lignes
    for line in line_objects:
        qty_shipped = next(
            item["quantity"] for item in line_items if item["order_line_id"] == line.id
            )
        if qty_shipped == line.quantity:
            line.status = "shipped"
        # Note: Tout ce qui est facturé est expédié, le cutting est fait lors de la facturation.
    session.commit()

    # Recalculer le statut de la commande
    _recalculate_order_status(order, order_repo)
    return shipment.to_dict()


def _recalculate_order_status(order: Order, repo: OrdersRepository) -> None:
    """Recalcule le statut de la commande en fonction des statuts de ses lignes."""
    statuses = {
        l.status for l in (order.order_lines or []) if l.status != "cancelled"
    }
    if not statuses:
        return
    if statuses == {"shipped"}:
        new_status = "shipped"
    elif "shipped" in statuses:
        new_status = "partial_shipped"
    elif statuses == {"invoiced"}:
        new_status = "invoiced"
    elif "invoiced" in statuses:
        new_status = "partial_invoiced"
    else:
        new_status = order.status
    if new_status != order.status:
        repo.update_order_status(order, new_status, update_source="backoffice")


# ── Recherche clients (pour dropdown) ────────────────────────────────────

def search_customers_for_dropdown(query: str) -> List[Dict[str, Any]]:
    """Recherche de clients par nom pour le dropdown de sélection.

    Returns:
        Liste de dicts avec id, display_name, customer_type, location.
    """
    session = db_conf.get_main_session()
    repo = CustomersRepository(session)
    customers = repo.get_by_name_like(query, complete=True)
    if not customers:
        return []
    results = []
    for c in customers:
        results.append({
            "id": c.id,
            "display_name": _customer_display_name(c),
            "customer_type": c.customer_type,
            "location": c.addresses[0].city if c.addresses else "—",
        })
    return results


# ── Recherche objets (pour autocomplete) ─────────────────────────────────

def get_objects_by_name(query: str) -> Optional[Sequence[GeneralObjects]]:
    """Récupère des objets par titre ou EAN13 pour l'autocomplete.

    Returns:
        Liste de dicts avec id et name, ou None.
    """
    session = db_conf.get_main_session()
    repo = ObjectsRepository(session)
    results = repo.get_by_name_or_ean(query)
    if results is None:
        return None
    return results


# ── WooCommerce ───────────────────────────────────────────────────────────

def push_order_wc(order_id: int) -> tuple[bool, str | None]:
    """Pousse une commande vers WooCommerce (création ou mise à jour).

    Enregistre un OrderSyncLog et commite la session.

    Returns:
        (success, error_message)
    """
    session = db_conf.get_main_session()
    repo = OrdersRepository(session)
    order = repo.get_by_id(order_id)
    if order is None:
        return False, "Commande introuvable"
    svc = WCOrdersService(session)
    success, error = svc.push_order(order)
    try:
        session.commit()
    except Exception as exc:    # pylint: disable=broad-except
        session.rollback()
        logger.exception("Erreur commit après push WC (commande %d) : %s", order_id, exc)
        return False, str(exc)
    return success, error
