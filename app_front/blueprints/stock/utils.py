"""Module utils pour le blueprint stock"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select, distinct, text

from app_front.config import MAILS, WOO_COMMERCE, db_conf, post
from app_front.blueprints.stock.forms import (
    CreateObjectForm,
    OrderInCreateForm,
    OrderInLineForm,
    VariationForm,
)
from db_models.objects import (
    Books,
    Tags,
    OrderIn,
    OrderInLine,
    OrderInLinePrice,
    GeneralObjects,
    ObjectVariations,
    VatRate,
)
from db_models.repositories.stocks import (
    StockRepository,
    DilicomReferencialRepository,
    InventoryRepository,
    )
from db_models.repositories.objects.objects import ObjectsRepository
from db_models.repositories.objects.variations import VariationsRepository
from db_models.repositories.tags import TagsRepository
from db_models.services.henrri import sync_product_to_henrri
from db_models.services.woo_commerce.products import WCProductsService

logger = logging.getLogger("stock_utils")

VALUE_TYPE_NBR_MSG = "L'ID de la ligne doit être un nombre entier."


def get_supplier_order_dispatch(supplier: Any) -> Dict[str, str]:
    """Retourne le mode de transmission optimisé pour un fournisseur."""
    if getattr(supplier, "edi_active", False):
        return {"code": "EDI", "label": "EDI", "display": "EDI"}
    if getattr(supplier, "contact_email", None):
        return {"code": "MAIL", "label": "MAIL", "display": "MAIL"}
    return {"code": "MANUAL", "label": ":-(", "display": ":-("}


def dispatch_supplier_order(order: Any) -> Dict[str, str]:
    """Détermine le canal d'envoi de la commande fournisseur.

    L'EDI est prioritaire quand le fournisseur le supporte. Sinon on bascule sur
    un envoi mail si un contact est renseigné. En dernier recours, on renvoie le
    mode manuel et le bon de commande sera généré pour téléchargement.
    """
    dispatch = get_supplier_order_dispatch(getattr(order, "supplier", None))
    if dispatch["code"] == "EDI":
        logger.info(
            "Commande %s envoyée par EDI pour fournisseur %s.",
            order.id,
            order.supplier_id,
        )
        return {"code": "EDI", "label": "EDI", "display": "EDI"}
    if dispatch["code"] == "MAIL":
        logger.info(
            "Commande %s envoyée par mail pour fournisseur %s.",
            order.id,
            order.supplier_id,
        )
        return {"code": "MAIL", "label": "MAIL", "display": "MAIL"}
    logger.info(
        "Commande %s générée en bon de commande téléchargeable pour fournisseur %s.",
        order.id,
        order.supplier_id,
    )
    return {"code": "MANUAL", "label": ":-(", "display": ":-("}


def send_order_by_edi(order: Any) -> bool:
    """Placeholder d'envoi EDI.

    À remplacer par l'intégration réelle vers l'EDI du fournisseur.
    La valeur de retour est volontairement False tant qu'aucune intégration
    n'est branchée, ce qui garde le comportement explicite et sûr.
    """
    # Intégration EDI non disponible actuellement : garder un comportement explicite.
    logger.warning(
        "Placeholder EDI appelé pour la commande %s : intégration non implémentée.",
        getattr(order, "id", None),
    )
    return False


def send_order_by_mail(order: Any) -> str | bool:
    """Demande au backend de générer le PDF et d'envoyer le bon de commande par mail.

    Retourne soit un statut métier explicite (`success`, `accepted_by_smtp`) soit `False`
    si le backend a refusé l'envoi. Le statut `accepted_by_smtp` ne confirme pas la
    livraison réelle dans la messagerie du fournisseur.
    """
    supplier = getattr(order, "supplier", None)
    supplier_email = str(getattr(supplier, "contact_email", "") or "").strip()
    if not supplier_email:
        logger.warning(
            "Impossible d'envoyer le bon de commande %s : aucun email fournisseur renseigné.",
            getattr(order, "id", None),
        )
        return False

    try:
        payload = {
            "order_id": getattr(order, "id", None),
            "supplier_email": supplier_email,
            "supplier_name": getattr(supplier, "name", "Fournisseur") or "Fournisseur",
            "order_ref": getattr(order, "order_ref", "") or f"CMD-{getattr(order, 'id', 0)}",
        }
        response = post(MAILS["send_supplier_order"], payload)
        status = response.get("status") if isinstance(response, dict) else None
        if status in {"success", "accepted_by_smtp"}:
            return status
        return False
    except RuntimeError as exc:
        logger.exception(
            "Échec de la demande d'envoi du bon de commande %s par email au fournisseur %s : %s",
            getattr(order, "id", None),
            supplier_email,
            exc,
        )
        return False


def get_vat_rates() -> List[tuple]:
    """Retourne les taux de TVA actuellement en vigueur sous forme de liste de tuples.

    Cette liste est utilisée pour les lignes de prix de vente (historique de prix),
    qui sont la seule source de vérité pour la TVA de vente.
    """
    session = db_conf.get_main_session()
    rates = session.execute(
        select(VatRate).where(VatRate.date_end.is_(None)).order_by(VatRate.code)
    ).scalars().all()
    return [(str(r.id), f"{r.label} ({r.rate} %)") for r in rates]


def get_zero_price_items() -> Sequence[dict]:
    """Récupère les articles dont le dernier inventaire a un prix de revient à zéro.

    Retourne une liste de dictionnaires avec les clés :
    - `general_object_id`, `name`, `ean13`, `price_at_movement`, `movement_id`.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    return stock_repo.get_zero_price_items()


def is_zero_price_items() -> bool:
    """
    Indique s'il existes des articles dont le dernier inventaire a un prix de revient à zéro
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    return len(stock_repo.get_zero_price_items()) > 0


def update_movement_price(movement_id: int, price: float) -> int:
    """Crée un nouveau mouvement d'inventaire en dupliquant le mouvement
    d'origine et en y appliquant le nouveau prix de revient.

    Le mouvement original reste inchangé (traçabilité).

    Args:
        movement_id: ID du mouvement d'origine à dupliquer.
        price: Nouveau prix de revient à appliquer.

    Returns:
        L'ID du nouveau mouvement créé.

    Raises:
        ValueError: si le mouvement d'origine n'existe pas.
        RuntimeError: en cas d'erreur lors du commit.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    return stock_repo.clone_movement_with_updated_price(movement_id, price)


def get_supplier_orders(
    out: bool = False, reservation: bool = False
) -> Sequence[OrderIn]:
    """Récupère la liste des commandes fournisseurs avec le nom du fournisseur
    et le nombre de lignes de commande.

    Args:
        out: True pour les retours fournisseur.
        reservation: True pour les réservations.

    Returns:
        Sequence[OrderIn]: Liste des commandes avec relations complètement chargées.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    return stock_repo.get_supplier_orders(out=out, reservation=reservation)


def cancel_supplier_order(
    order_id: int, out: bool = False, reservation: bool = False
) -> bool:
    """Supprime une commande fournisseur, un retour ou une réservation et ses lignes.

    Les mouvements d'inventaire liés sont désassociés et un mouvement inverse est créé.

    Args:
        order_id: L'identifiant de la commande à annuler.
        out: True pour supprimer un retour fournisseur.
        reservation: True pour supprimer une réservation.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    stock_repo.cancel_supplier_order(order_id, out=out, reservation=reservation)
    return True


def build_reservation_context(form: Any) -> Dict[str, str]:
    """Construit le contexte métier d’une réservation à partir du formulaire."""
    context: Dict[str, str] = {}
    for key, field_name in {
        "notes": "reservation_notes",
        "location": "reservation_location",
        "responsible_name": "reservation_responsible_name",
    }.items():
        field = getattr(form, field_name, None)
        value = field.data if field is not None and hasattr(field, "data") else None
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            context[key] = cleaned
    return context


def create_order_in_db(
    form: OrderInCreateForm, out: bool = False, reservation: bool = False
) -> int:
    """Crée une nouvelle commande fournisseur, un retour ou une réservation en base.

    Args:
        form: Le formulaire contenant les données de la commande.
        out: True pour créer un retour fournisseur (RET-).
        reservation: True pour créer une réservation (RES-).
    """
    supplier_id = form.supplier_id.data
    if supplier_id is None:
        raise ValueError("Le champ fournisseur est requis.")
    try:
        supplier_id = int(supplier_id)
    except ValueError as e:
        msg = f"ID de fournisseur invalide : {form.supplier_id.data}"
        logger.error(msg)
        raise ValueError(msg) from e
    stock_repo = StockRepository(db_conf.get_main_session())
    reservation_context = build_reservation_context(form) if reservation else {}
    order = OrderIn(
        order_ref="temp",
        supplier_id=supplier_id,
        reservation_context=reservation_context,
    )
    return stock_repo.edit_order_in_db(
        order, action="create", out=out, reservation=reservation
    )


def get_order_by_id(order_id: int) -> OrderIn:
    """Récupère les détails d'une commande fournisseur à partir de son ID.

    Args:
        order_id: L'identifiant de la commande à récupérer.

    Returns:
        OrderIn: Les détails de la commande.

    Raises:
        ValueError: Si la commande n'existe pas.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    order = stock_repo.get_order_by_id(order_id)
    if order is None:
        raise ValueError(f"Commande avec l'id {order_id} introuvable.")
    return order


def _validate_reservation_quantity(
    order: Any, inventory_repo: InventoryRepository
) -> float:
    """Vérifie la disponibilité du stock pour une réservation."""
    if not inventory_repo.has_inventory_history(order.general_object_id):
        return inventory_repo.get_last_inventory_price(order.general_object_id)

    available_qty = inventory_repo.get_available_quantity(order.general_object_id)
    if order.qty > available_qty:
        raise ValueError(
            f"Quantité indisponible : {order.qty} > stock disponible ({available_qty})."
        )
    return inventory_repo.get_last_inventory_price(order.general_object_id)


def _resolve_order_line_unit_price(
    order: Any, reservation: bool, inventory_repo: InventoryRepository
) -> float:
    """Calcule le prix unitaire de la ligne selon le type de commande."""
    if reservation:
        return _validate_reservation_quantity(order, inventory_repo)
    return sum(price.unit_price for price in order.prices)


def _build_order_line(
    order: Any,
    reservation: bool,
    unit_price: float,
    line_id: int = 0,
    action: str = "create",
) -> OrderInLine:
    """Construit la ligne de commande avec la structure de prix associée."""
    if reservation:
        prices = [
            OrderInLinePrice(
                unit_price=unit_price,
                vat_rate=0,
                position=0,
            )
        ]
    else:
        prices = [
            OrderInLinePrice(
                unit_price=price.unit_price,
                vat_rate=price.vat_rate,
                position=position,
            )
            for position, price in enumerate(order.prices)
        ]

    line = OrderInLine(
        order_in_id=order.id,
        general_object_id=order.general_object_id,
        qty_ordered=order.qty,
        prices=prices,
    )
    if action == "edit":
        line.id = line_id
    return line


def edit_order_in_line_db(
    form: OrderInLineForm, order_id: int, action: str = "create",
    line_id: int = 0, reservation: bool = False
) -> int:
    """Crée/édite/supprime une ligne de commande fournisseur en base.

    Args:
        form: Le formulaire contenant les données de la ligne de commande.
        order_id: L'identifiant de la commande.
        action: "create", "edit" ou "delete".
        line_id: L'identifiant de la ligne (pour edit/delete).
        reservation: True pour une ligne de réservation (prix auto depuis purchase_price).
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    inventory_repo = InventoryRepository(db_conf.get_main_session())
    normalized_line_id = _coerce_order_line_id(line_id)

    if action == "delete":
        line_id = stock_repo.delete_order_in_line_db(normalized_line_id)
        stock_repo.update_order_in_price(order_id)
        return line_id

    if action not in {"create", "edit"}:
        raise ValueError("Action inconnue : " + action)

    order = form.validate_form_data(reservation=reservation)
    unit_price = _resolve_order_line_unit_price(order, reservation, inventory_repo)
    line = _build_order_line(
        order,
        reservation=reservation,
        unit_price=unit_price,
        line_id=normalized_line_id,
        action=action,
    )
    line_id = stock_repo.edit_order_in_line_db(
        new_line=line, action=action, reservation=reservation
    )
    stock_repo.update_order_in_price(order_id)
    return line_id


def _coerce_order_line_id(value: Any) -> int:
    """Convertit un identifiant de ligne en entier avec un message explicite."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        msg = f"ID de ligne invalide : {value}"
        logger.error(msg)
        raise ValueError(msg) from exc


def _build_return_order_line(order: Any, line_id: int = 0) -> OrderInLine:
    """Construit une ligne de retour fournisseur à partir d'un formulaire validé."""
    return OrderInLine(
        order_in_id=order.id,
        general_object_id=order.general_object_id,
        qty_ordered=order.qty,
        prices=[
            OrderInLinePrice(
                unit_price=price.unit_price,
                vat_rate=price.vat_rate,
                position=position,
            )
            for position, price in enumerate(order.prices)
        ],
        id=line_id if line_id else None,
    )


def edit_return_order_in_line_db(
    form: OrderInLineForm, order_id: int, action: str = "create",
    line_id: int = 0
) -> int:
    """Crée/édite/supprime une ligne de retour fournisseur en base.

    Args:
        form: Le formulaire contenant les données de la ligne.
        order_id: L'identifiant du retour.
        action: "create", "edit" ou "delete".
        line_id: L'identifiant de la ligne (pour edit/delete).
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    normalized_line_id = _coerce_order_line_id(line_id)

    if action == "delete":
        updated_line_id = stock_repo.delete_order_in_line_db(normalized_line_id)
        stock_repo.update_order_in_price(order_id)
        return updated_line_id

    if action not in {"create", "edit"}:
        raise ValueError("Action inconnue : " + action)

    order = form.validate_form_data(reservation=False)
    line = _build_return_order_line(order, normalized_line_id if action == "edit" else 0)
    saved_line_id = stock_repo.edit_order_in_line_db(new_line=line, action=action, out=True)
    stock_repo.update_order_in_price(order_id)
    return saved_line_id


def receive_return_order_line(
    line_id: int,
    qty_received: int,
    qty_cancelled: int,
    prices: list[OrderInLinePrice],
) -> int:
    """Traite la réception d'une ligne de retour fournisseur avec prix validés.

    Args:
        line_id: L'identifiant de la ligne.
        qty_received: Quantité confirmée comme retournée au fournisseur.
        qty_cancelled: Quantité annulée/réintégrée en stock.
        prices: Composantes financières validées à la réception.

    Returns:
        L'ID du retour parent.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    order_id = stock_repo.receive_order_line(
        line_id, qty_received, qty_cancelled, prices=prices
    )
    stock_repo.update_order_in_price(order_id)
    return order_id


def search_stock_global(
    name: Optional[str] = None,
    ean13: Optional[str] = None,
    supplier_id: Optional[int] = None,
    object_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    dilicom_status: Optional[str] = None,
    page: int = 1,
) -> Dict[str, Any]:
    """Recherche paginée du stock global.

    Returns:
        Dict avec 'items', 'total', 'page', 'per_page'.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    return stock_repo.search_stock_global(
        name=name,
        ean13=ean13,
        supplier_id=supplier_id,
        object_type=object_type,
        is_active=is_active,
        dilicom_status=dilicom_status,
        page=page,
    )


def get_dilicom_referencial(
    object_id: int,
) -> Tuple[Optional[dict], Optional[GeneralObjects]]:
    """Récupère les données de référentiel Dilicom pour un objet donné.

    Args:
        object_id: L'identifiant de l'objet pour lequel récupérer les données.

    Returns:
        Un tuple contenant un dictionnaire avec les données de référentiel Dilicom
        et l'objet GeneralObjects, ou None si non trouvé.
    """
    session = db_conf.get_main_session()
    obj = session.get(GeneralObjects, object_id)
    if obj is None:
        return None, None

    dilicom_repo = DilicomReferencialRepository(session)
    dilicom_ref = dilicom_repo.get_last_by_ean13(obj.ean13) if obj.ean13 else None
    return dilicom_ref, obj


def get_object_by_id(object_id: int) -> Optional[GeneralObjects]:
    """Récupère un objet complet par son identifiant (avec relations chargées)."""
    session = db_conf.get_main_session()
    repo = ObjectsRepository(session)
    return repo.get_by_ref(object_id)


def toggle_object_active(object_id: int) -> bool:
    """Bascule le statut actif/inactif d'un objet.

    Args:
        object_id: L'identifiant de l'objet à activer/désactiver.

    Returns:
        Le nouveau statut (True = actif, False = inactif).

    Raises:
        ValueError: si l'objet n'existe pas ou en cas d'erreur de bdd.
        Le rollback est géré automatiquement par le middleware Flask.
    """
    repo = ObjectsRepository(db_conf.get_main_session())
    return repo.toggle_active(object_id)


def add_object_to_dilicom(object_id: int, gln13: str) -> Any:
    """Planifie l'ajout d'un objet au référentiel Dilicom (create_ref=True).

    Returns:
        L'ID de la référence Dilicom créée.
    Raises:
        ValueError: si l'objet n'existe pas ou n'a pas d'EAN13, ou en cas d'erreur de bdd.
        Le rollback est géré automatiquement par le middleware Flask.
    """
    session = db_conf.get_main_session()
    general_object_repo = ObjectsRepository(session)
    obj = general_object_repo.get_by_ref(object_id)
    if obj is None:
        raise ValueError(f"Objet avec l'id {object_id} introuvable.")
    dilicom_repo = DilicomReferencialRepository(session)
    dilicom_ref = dilicom_repo.create_status(obj.ean13, gln13, movement="to_create")
    return dilicom_ref


def remove_object_from_dilicom(object_id: int) -> Any:
    """Planifie la suppression d'un objet du référentiel Dilicom (delete_ref=True).

    Returns:
        L'ID de la référence Dilicom mise à jour.
    Raises:
        ValueError: si l'objet ou sa référence Dilicom n'existe pas, ou en cas d'erreur de bdd.
        Le rollback est géré automatiquement par le middleware Flask.
    """
    session = db_conf.get_main_session()
    general_object_repo = ObjectsRepository(session)
    obj = general_object_repo.get_by_ref(object_id)
    if obj is None:
        raise ValueError(f"Objet avec l'id {object_id} introuvable.")
    dilicom_repo = DilicomReferencialRepository(session)
    existing = dilicom_repo.get_last_by_ean13(obj.ean13) if obj.ean13 else None
    if existing is None:
        raise ValueError("Aucun référentiel Dilicom trouvé pour cet objet.")
    dilicom_ref = dilicom_repo.create_status(
        obj.ean13, existing.gln13, movement="to_delete"
    )
    return dilicom_ref


def save_object_complete(
    form: CreateObjectForm, object_id: Optional[int] = None
) -> int:
    """Crée un objet complet à partir du formulaire CreateObjectForm.

    Args:
        form: Le formulaire validé contenant les données de l'objet.
        object_id: L'ID de l'objet à mettre à jour (None pour création).

    Returns:
        L'ID de l'objet GeneralObjects créé ou mis à jour.

    Raises:
        ValueError: Si la création ou la mise à jour échoue.
    """
    repo = ObjectsRepository(db_conf.get_main_session())

    if object_id is None:
        obj_id = repo.save_from_form(form)
        return obj_id

    general_object = repo.get_by_ref(object_id)
    obj_id = repo.save_from_form(form, instance=general_object)
    return obj_id


# ============================================================================
# Recherche autocomplete pour les champs livre et tags
# ============================================================================

_BOOK_FIELD_MAP = {
    "author": Books.author,
    "editor": Books.editor,
    "diffuser": Books.diffuser,
    "genre": Books.genre,
}


def search_book_field(field_name: str, query: str) -> List[str]:
    """Recherche des valeurs distinctes d'un champ Books correspondant à la requête."""
    column = _BOOK_FIELD_MAP.get(field_name)
    if column is None:
        return []
    session = db_conf.get_main_session()
    stmt = (
        select(distinct(column))
        .where(column.ilike(f"%{query}%"))
        .where(column.isnot(None))
        .where(column != "")
        .order_by(column)
        .limit(10)
    )
    return [row[0] for row in session.execute(stmt).all()]


def get_variation_attribut_suggestions() -> List[str]:
    """Retourne les noms d'attribut de variation existants sans doublon de casse."""
    session = db_conf.get_main_session()
    values = session.execute(
        select(GeneralObjects.object_variation_attribut)
        .where(GeneralObjects.object_variation_attribut.isnot(None))
        .where(GeneralObjects.object_variation_attribut != "")
        .order_by(GeneralObjects.object_variation_attribut)
    ).scalars()
    suggestions: dict[str, str] = {}
    for value in values:
        if not isinstance(value, str) or not value:
            continue
        suggestions.setdefault(value.casefold(), value)
    return list(suggestions.values())


def search_tags(query: str) -> List[Dict[str, Any]]:
    """Recherche des tags (id + name) correspondant à la requête."""
    session = db_conf.get_main_session()
    stmt = (
        select(Tags.id, Tags.name, Tags.description)
        .where(Tags.name.ilike(f"%{query}%"))
        .order_by(Tags.name)
        .limit(10)
    )
    return [
        {"id": row[0], "name": row[1], "description": row[2]}
        for row in session.execute(stmt).all()
    ]


def search_metadata_keys(query: str) -> List[str]:
    """Recherche des clés de métadonnées distinctes correspondant à la requête."""
    session = db_conf.get_main_session()
    stmt = text(
        "SELECT DISTINCT k"
        " FROM app_schema.obj_metadatas,"
        " json_object_keys(semistructured_data) AS k"
        " WHERE k ILIKE :pattern"
        " ORDER BY k"
        " LIMIT 10"
    )
    return [row[0] for row in session.execute(stmt, {"pattern": f"%{query}%"}).all()]


def create_tag(name: str, description: str = "") -> Dict[str, Any]:
    """Crée un nouveau tag et retourne son id + name."""
    session = db_conf.get_main_session()
    repo = TagsRepository(session)
    tag = repo.create({"name": name, "description": description})
    return {"id": tag.id, "name": tag.name, "description": tag.description}


# ============================================================================
# Workflow commandes fournisseurs
# ============================================================================


def confirm_supplier_order(order_id: int) -> OrderIn:
    """Confirme une commande fournisseur (draft → sended).

    Args:
        order_id: L'identifiant de la commande à confirmer.

    Returns:
        L'objet OrderIn mis à jour.

    Raises:
        ValueError: Si la commande n'existe pas ou n'est pas en état 'draft'.
        RuntimeError: En cas d'erreur lors du commit.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    return stock_repo.confirm_order(order_id)


def receive_order_line(
    line_id: int, qty_received: int, qty_cancelled: int
) -> int:
    """Traite la réception d'une ligne de commande avec split possible.

    Args:
        line_id: L'identifiant de la ligne de commande.
        qty_received: La quantité reçue.
        qty_cancelled: La quantité annulée.

    Returns:
        L'ID de la commande parente.

    Raises:
        ValueError: Si les quantités sont incohérentes.
        RuntimeError: En cas d'erreur lors du commit.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    return stock_repo.receive_order_line(line_id, qty_received, qty_cancelled)


def update_order_external_ref(order_id: int, external_ref: str) -> None:
    """Met à jour la référence externe d'une commande fournisseur.

    Args:
        order_id: L'identifiant de la commande.
        external_ref: La référence externe du fournisseur.
    """
    stock_repo = StockRepository(db_conf.get_main_session())
    stock_repo.update_order_external_ref(order_id, external_ref)


# ============================================================================
# Workflow réservations
# ============================================================================


def return_reservation(order_id: int) -> None:
    """Retourne (clôture) une réservation."""
    stock_repo = StockRepository(db_conf.get_main_session())
    stock_repo.return_reservation(order_id)


def save_reservation_context(order_id: int, form: Any) -> None:
    """Met à jour le contexte métier d'une réservation."""
    stock_repo = StockRepository(db_conf.get_main_session())
    stock_repo.update_reservation_context(order_id, build_reservation_context(form))


# ============================================================================
# Gestion des variations d'objet
# ============================================================================


def get_variations(general_object_id: int) -> List[ObjectVariations]:
    """Retourne toutes les variations actives d'un objet général."""
    session = db_conf.get_main_session()
    repo = VariationsRepository(session)
    return list(repo.get_all(general_object_id))


def create_variation_for_object(
    general_object_id: int,
    form: "VariationForm",
    variation_attribut: str,
) -> int:
    """Crée une nouvelle variation pour l'objet donné.

    Returns:
        L'ID de la variation créée.
    """
    session = db_conf.get_main_session()
    object_repo = ObjectsRepository(session)
    general_object = object_repo.get_by_ref(general_object_id, only_actives=False)
    if general_object is None:
        raise ValueError(f"Objet {general_object_id} introuvable.")
    object_repo.set_variation_attribut(general_object, variation_attribut)
    repo = VariationsRepository(session)
    variation = repo.save_from_form(form, general_object_id=general_object_id)
    return variation.id


def update_variation_for_object(
    variation_id: int,
    general_object_id: int,
    form: "VariationForm",
    variation_attribut: str,
) -> int:
    """Met à jour une variation existante.

    Returns:
        L'ID de la variation mise à jour.

    Raises:
        ValueError: Si la variation n'appartient pas à l'objet général donné.
    """
    session = db_conf.get_main_session()
    object_repo = ObjectsRepository(session)
    general_object = object_repo.get_by_ref(general_object_id, only_actives=False)
    if general_object is None:
        raise ValueError(f"Objet {general_object_id} introuvable.")
    object_repo.set_variation_attribut(general_object, variation_attribut)
    repo = VariationsRepository(session)
    variation = repo.get_by_id(variation_id)
    if variation is None or variation.general_object_id != general_object_id:
        raise ValueError(
            f"Variation {variation_id} introuvable pour l'objet {general_object_id}."
        )
    repo.save_from_form(form, general_object_id=general_object_id, instance=variation)
    return variation.id


def delete_variation_for_object(variation_id: int) -> bool:
    """Effectue une suppression logique d'une variation (is_active = False).

    Returns:
        True si la variation a bien été désactivée.

    Raises:
        ValueError: Si la variation n'existe pas.
    """
    session = db_conf.get_main_session()
    repo = VariationsRepository(session)
    variation = repo.get_by_id(variation_id)
    if variation is None:
        raise ValueError(f"Variation {variation_id} introuvable.")
    repo.delete(variation_id)
    return True


def push_product_partners(object_id: int) -> None:
    """Pousse un produit vers WooCommerce et Henrri selon le workflow multi-partenaires.

    Args:
        object_id: Identifiant local du produit (GeneralObjects).
    """
    session = db_conf.get_main_session()
    product = ObjectsRepository(session).get_by_ref(object_id, only_actives=False)
    if product is None:
        raise ValueError(f"Produit {object_id} introuvable.")

    WCProductsService(session).update_product(object_id)
    sync_product_to_henrri(product)
    session.commit()


def trigger_catalog_wc_sync() -> None:
    """Déclenche la synchronisation globale du catalogue vers WooCommerce via app-back."""
    post(WOO_COMMERCE["sync_catalog"], {})
