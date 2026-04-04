"""Utilitaires pour les commandes, utilisés par les routes et tests."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy.exc import SQLAlchemyError
from app_front.config import db_conf
from db_models.objects import Order, OrderLine
from db_models.objects import InventoryMovements
from db_models.repositories.orders import OrdersRepository
from db_models.repositories.customers import CustomersRepository
from db_models.repositories.invoices import InvoiceRepository
from db_models.repositories.shipments import ShipmentsRepository
from db_models.repositories.objects.objects import ObjectsRepository, GeneralObjects


# ── Libellés statuts ──────────────────────────────────────────────────────

STATUS_LABELS: Dict[str, str] = {
    "draft": "Brouillon",
    "partial_invoiced": "Partiellement facturée",
    "invoiced": "Facturée",
    "partial_shipped": "Partiellement expédiée",
    "shipped": "Expédiée",
    "canceled": "Annulée",
    "returned": "Retournée",
}

STATUS_BADGE_CLASS: Dict[str, str] = {
    "draft": "badge-draft",
    "partial_invoiced": "badge-warning",
    "invoiced": "badge-info",
    "partial_shipped": "badge-warning",
    "shipped": "badge-success",
    "canceled": "badge-danger",
    "returned": "badge-danger",
}

_ORDER_NOT_FOUND = "Commande introuvable"


def _customer_display_name(customer) -> str:
    """Construit le nom d'affichage d'un client."""
    if customer.customer_type == "part" and customer.part:
        return f"{customer.part.first_name} {customer.part.last_name}"
    if customer.customer_type == "pro" and customer.pro:
        return customer.pro.company_name
    return f"Client #{customer.id}"


def _order_to_list_dict(order: Order) -> Dict[str, Any]:
    """Convertit une commande en dict pour la vue tableau."""
    total_ht = 0.0
    for line in (order.order_lines or []):
        if line.status == "canceled":
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
    if item["quantity"] > line.quantity or item["quantity"] < 1:
        raise ValueError(f"Quantité invalide pour la ligne {line.id}.")
    return line

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
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
        except ValueError:
            pass

    session = db_conf.get_main_session()
    try:
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
    finally:
        session.close()


# ── Lecture détail ───────────────────────────────────────────────────────

def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """Récupère une commande par son ID avec toutes ses relations.

    Returns:
        Dict complet de la commande, ou None.
    """
    session = db_conf.get_main_session()
    try:
        repo = OrdersRepository(session)
        order = repo.get_by_id(order_id)
        if order is None:
            return None

        data = _order_to_list_dict(order)
        data["invoice_address"] = (
            order.invoice_address.to_dict() if order.invoice_address else None
        )
        data["delivery_address"] = (
            order.delivery_address.to_dict() if order.delivery_address else None
        )

        # Lignes de commande (exclure les annulées pour le tableau principal)
        data["lines"] = []
        data["all_lines"] = []  # toutes les lignes y compris annulées
        for line in (order.order_lines or []):
            ld = line.to_dict()
            if line.general_object:
                ld["article_name"] = getattr(line.general_object, "name", None) \
                                            or f"Article #{line.general_object_id}"
            else:
                ld["article_name"] = f"Article #{line.general_object_id}"
            ld["status_label"] = STATUS_LABELS.get(line.status, line.status)
            price = float(line.unit_price) * line.quantity
            discount_amount = price * float(line.discount) / 100
            ld["line_total_ht"] = round(price - discount_amount, 2)
            data["all_lines"].append(ld)
            if line.status != "canceled":
                data["lines"].append(ld)

        # Factures rattachées
        inv_repo = InvoiceRepository(session)
        invoices = inv_repo.get_by_order_id(order_id)
        data["invoices"] = [inv.to_dict() for inv in invoices]

        # Envois rattachés
        ship_repo = ShipmentsRepository(session)
        shipments = ship_repo.get_by_order_id(order_id)
        data["shipments"] = [s.to_dict() for s in shipments]

        # Flags pour boutons facturer / expédier
        data["has_uninvoiced_lines"] = any(
            l.status == "draft" for l in (order.order_lines or [])
        )
        data["has_unshipped_invoiced_lines"] = any(
            l.status == "invoiced" for l in (order.order_lines or [])
        )
        return data
    finally:
        session.close()


# ── Création ─────────────────────────────────────────────────────────────

def create_order(customer_id: int) -> Dict[str, Any]:
    """Crée un brouillon de commande pour un client.

    Returns:
        Dict de la commande créée.
    """
    session = db_conf.get_main_session()
    try:
        repo = OrdersRepository(session)
        order = repo.create_order(customer_id=customer_id, create_source="backoffice")
        return {"id": order.id, "reference": order.reference}
    finally:
        session.close()


def add_order_line(     # pylint: disable=too-many-arguments
    order_id: int,
    *,
    general_object_id: int,
    quantity: int,
    unit_price: float,
    discount: float = 0,
    vat_rate: float,
) -> Dict[str, Any]:
    """Ajoute une ligne à une commande existante et crée un mouvement de réservation.

    Returns:
        Dict de la ligne créée.
    """
    session = db_conf.get_main_session()
    try:
        repo = OrdersRepository(session)
        order = repo.get_by_id(order_id)
        if order is None:
            raise ValueError(_ORDER_NOT_FOUND)
        line = repo.add_line(
            order,
            general_object_id=general_object_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            vat_rate=vat_rate,
            create_source="backoffice",
        )
        # Créer un mouvement de réservation dans inventory_movements
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
        session.commit()
        return line.to_dict()
    finally:
        session.close()


def remove_order_line(order_id: int, line_id: int) -> bool:
    """Annule une ligne de commande (soft delete) et crée un mouvement d'annulation."""
    session = db_conf.get_main_session()
    try:
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
    finally:
        session.close()


def cancel_order(order_id: int) -> Dict[str, Any]:
    """Annule une commande (passe en statut 'canceled').

    Returns:
        Dict de la commande mise à jour.
    """
    session = db_conf.get_main_session()
    try:
        repo = OrdersRepository(session)
        order = repo.get_by_id(order_id)
        if order is None:
            raise ValueError(_ORDER_NOT_FOUND)
        if order.status in ("canceled", "returned"):
            raise ValueError("Commande déjà annulée ou retournée")
        order = repo.update_order_status(order, "canceled", update_source="backoffice")
        return _order_to_list_dict(order)
    finally:
        session.close()


def invoice_order(order_id: int, line_items: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Crée une facture pour les lignes sélectionnées avec les quantités spécifiées.

    Args:
        order_id: ID de la commande.
        line_items: Liste de dicts {order_line_id: int, quantity: int}.
    Returns:
        Dict de la facture créée.
    """
    if not line_items:
        raise ValueError("Aucune ligne sélectionnée pour la facturation.")

    session = db_conf.get_main_session()
    try:
        order_repo = OrdersRepository(session)
        order = order_repo.get_by_id(order_id)
        if order is None:
            raise ValueError(_ORDER_NOT_FOUND)

        # Valider les lignes et enrichir avec les prix
        lines_by_id = {l.id: l for l in (order.order_lines or [])}
        enriched_items = []
        for item in line_items:
            line = _may_be_invoiced(lines_by_id.get(item["order_line_id"]), item)
            enriched_items.append({
                "order_line_id": line.id,
                "quantity": item["quantity"],
                "unit_price": float(line.unit_price),
                "discount": float(line.discount),
                "vat_rate": float(line.vat_rate),
            })

        # Créer la facture
        inv_repo = InvoiceRepository(session)
        invoice = inv_repo.create_invoice(
            order_id=order_id,
            line_items=enriched_items,
            create_source="backoffice",
        )

        # Mettre à jour le statut des lignes de commande
        for item in line_items:
            line = lines_by_id[item["order_line_id"]]
            if item["quantity"] == line.quantity:
                line.status = "invoiced"
            else:
                # Facturation partielle : couper la ligne
                order_repo.cut_line_for_invoice(line, item["quantity"])
                line.status = "invoiced"
        session.commit()

        # Recalculer le statut de la commande
        _recalculate_order_status(order, order_repo)
        return invoice.to_dict()
    except SQLAlchemyError as e:
        session.rollback()
        raise ValueError(f"Erreur lors de la facturation : {str(e)}") from e
    finally:
        session.close()


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
    try:
        order_repo = OrdersRepository(session)
        order = order_repo.get_by_id(order_id)
        if order is None:
            raise ValueError(_ORDER_NOT_FOUND)

        lines_by_id = {l.id: l for l in (order.order_lines or [])}
        for item in line_items:
            line = lines_by_id.get(item["order_line_id"])
            if line is None:
                raise ValueError(f"Ligne {item['order_line_id']} introuvable.")
            if line.status != "invoiced":
                raise ValueError(f"La ligne {line.id} n'est pas facturée.")
            if item["quantity"] > line.quantity or item["quantity"] < 1:
                raise ValueError(f"Quantité invalide pour la ligne {line.id}.")

        # Créer l'expédition
        ship_repo = ShipmentsRepository(session)
        shipment = ship_repo.create_shipment(
            order_id=order_id,
            carrier=carrier,
            tracking_number=tracking_number,
            line_items=line_items,
            create_source="backoffice",
        )

        # Mettre à jour le statut des lignes
        for item in line_items:
            line = lines_by_id[item["order_line_id"]]
            if item["quantity"] == line.quantity:
                line.status = "shipped"
            # Note: pour une expédition partielle on pourrait couper la ligne,
            # mais on garde simple pour l'instant
        session.commit()

        # Recalculer le statut de la commande
        _recalculate_order_status(order, order_repo)
        return shipment.to_dict()
    finally:
        session.close()


def _recalculate_order_status(order: Order, repo: OrdersRepository) -> None:
    """Recalcule le statut de la commande en fonction des statuts de ses lignes."""
    statuses = {
        l.status for l in (order.order_lines or []) if l.status != "canceled"
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
    try:
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
    finally:
        session.close()


# ── Recherche objets (pour autocomplete) ─────────────────────────────────

def get_objects_by_name(name: str) -> Optional[Sequence[GeneralObjects]]:
    """Récupère un objet général par son nom pour l'autocomplete.

    Returns:
        Liste de dicts avec id et name, ou None.
    """
    session = db_conf.get_main_session()
    try:
        repo = ObjectsRepository(session)
        results = repo.get_by_name(name)
        if results is None:
            return None
        return results
    finally:
        session.close()
