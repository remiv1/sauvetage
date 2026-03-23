"""Module utils pour le blueprint stock"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
from sqlalchemy import select, distinct
from app_front.config.db_conf import get_main_session
from app_front.blueprints.stock.forms import (
    CreateObjectForm,
    OrderInCreateForm,
    OrderInLineForm,
)
from db_models.objects import (
    Books,
    Tags,
    OrderIn,
    OrderInLine,
    GeneralObjects,
)
from db_models.repositories.stock import (
    StockRepository,
    DilicomReferencialRepository,
)
from db_models.repositories.objects.objects import ObjectsRepository
from db_models.repositories.tags import TagsRepository

VALUE_TYPE_NBR_MSG = "L'ID de la ligne doit être un nombre entier."


def get_zero_price_items() -> Sequence[dict]:
    """Récupère les articles dont le dernier inventaire a un prix de revient à zéro.

    Retourne une liste de dictionnaires avec les clés :
    - `general_object_id`, `name`, `ean13`, `price_at_movement`, `movement_id`.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_zero_price_items()


def is_zero_price_items() -> bool:
    """
    Indique s'il existes des articles dont le dernier inventaire a un prix de revient à zéro
    """
    stock_repo = StockRepository(get_main_session())
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
    stock_repo = StockRepository(get_main_session())
    return stock_repo.clone_movement_with_updated_price(movement_id, price)


def get_supplier_orders(out: bool = False) -> Sequence[OrderIn]:
    """Récupère la liste des commandes fournisseurs avec le nom du fournisseur
    et le nombre de lignes de commande.

    Returns:
        Sequence[OrderIn]: Liste des commandes avec relations complètement chargées.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_supplier_orders(out=out)


def cancel_supplier_order(order_id: int) -> bool:
    """Supprime une commande fournisseur et ses lignes associées.

    Les mouvements d'inventaire liés sont désassociés et un mouvement inverse est créé.

    Args:
        order_id: L'identifiant de la commande à annuler.

    Raises:
        ValueError: Si la commande n'existe pas.
        RuntimeError: En cas d'erreur lors du commit.
    """
    try:
        stock_repo = StockRepository(get_main_session())
        stock_repo.cancel_supplier_order(order_id)
        return True
    except ValueError as exc:
        msg = f"Erreur lors de l'annulation de la commande {order_id} : {str(exc)}"
        raise ValueError(msg) from exc
    except Exception as exc:
        msg = f"Erreur inattendue lors de l'annulation de la commande {order_id} : {str(exc)}"
        raise RuntimeError(msg) from exc


def create_order_in_db(form: OrderInCreateForm) -> int:
    """Crée une nouvelle commande fournisseur en base à partir des données du formulaire.

    Args:
        form: Le formulaire contenant les données de la commande.

    Raises:
        RuntimeError: En cas d'erreur lors du commit.
    """
    supplier_id = form.supplier_id.data
    if supplier_id is None:
        raise ValueError("Le champ fournisseur est requis.")
    try:
        supplier_id = int(supplier_id)
    except ValueError as e:
        raise ValueError("Le champ fournisseur doit être un nombre entier.") from e
    stock_repo = StockRepository(get_main_session())
    order = OrderIn(
        order_ref="temp",
        supplier_id=supplier_id,
    )
    return stock_repo.edit_order_in_db(order, action="create")


def get_order_by_id(order_id: int) -> OrderIn:
    """Récupère les détails d'une commande fournisseur à partir de son ID.

    Args:
        order_id: L'identifiant de la commande à récupérer.

    Returns:
        OrderIn: Les détails de la commande.

    Raises:
        ValueError: Si la commande n'existe pas.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_order_by_id(order_id)


def edit_order_in_line_db(
    form: OrderInLineForm, order_id: int, action: str = "create", line_id: int = 0
) -> int:
    """Crée une nouvelle ligne de commande fournisseur en base à partir des données du formulaire.

    Args:
        form: Le formulaire contenant les données de la ligne de commande.

    Raises:
        ValueError: Si les données du formulaire sont invalides.
        RuntimeError: En cas d'erreur lors du commit.
    """
    try:
        line_id = int(line_id)
    except ValueError as e:
        raise ValueError(VALUE_TYPE_NBR_MSG) from e
    stock_repo = StockRepository(get_main_session())

    # Gestion de la suppression d'une ligne de commande
    if action == "delete":
        line_id = stock_repo.delete_order_in_line_db(line_id)

    # Gestion de la création d'une ligne de commande
    elif action == "create":
        order_id, general_object_id, quantity, unit_price, vat_rate = (
            form.validate_form_data()
        )
        new_line = OrderInLine(
            order_in_id=order_id,
            general_object_id=general_object_id,
            qty_ordered=quantity,
            unit_price=unit_price,
            vat_rate=vat_rate,
        )
        line_id = stock_repo.edit_order_in_line_db(new_line=new_line, action=action)

    # Gestion de l'édition d'une ligne de commande
    elif action == "edit":
        order_id, general_object_id, quantity, unit_price, vat_rate = (
            form.validate_form_data()
        )
        edited_line = OrderInLine(
            id=line_id,
            order_in_id=order_id,
            general_object_id=general_object_id,
            qty_ordered=quantity,
            unit_price=unit_price,
            vat_rate=vat_rate,
        )
        line_id = stock_repo.edit_order_in_line_db(new_line=edited_line, action=action)

    else:
        raise ValueError("Action inconnue : " + action)
    stock_repo.update_order_in_price(order_id)
    return line_id


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
    stock_repo = StockRepository(get_main_session())
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
    session = get_main_session()
    obj = session.get(GeneralObjects, object_id)
    if obj is None:
        return None, None

    dilicom_repo = DilicomReferencialRepository(session)
    dilicom_ref = dilicom_repo.get_one_by_ean13(obj.ean13) if obj.ean13 else None
    return dilicom_ref, obj


def get_object_by_id(object_id: int) -> Optional[GeneralObjects]:
    """Récupère un objet complet par son identifiant (avec relations chargées)."""
    session = get_main_session()
    repo = ObjectsRepository(session)
    return repo.get_by_ref(object_id)


def toggle_object_active(object_id: int) -> bool:
    """Bascule le statut actif/inactif d'un objet. Retourne le nouveau statut."""
    session = get_main_session()
    repo = ObjectsRepository(session)
    return repo.toggle_active(object_id)


def add_object_to_dilicom(object_id: int, gln13: str) -> Any:
    """Planifie l'ajout d'un objet au référentiel Dilicom (create_ref=True).

    Returns:
        L'ID de la référence Dilicom créée.
    Raises:
        ValueError: si l'objet n'existe pas ou n'a pas d'EAN13.
        RuntimeError: en cas d'erreur lors du commit.
    """
    general_object_repo = ObjectsRepository(get_main_session())
    obj = general_object_repo.get_by_ref(object_id)
    if obj is None:
        raise ValueError(f"Objet avec l'id {object_id} introuvable.")
    dilicom_repo = DilicomReferencialRepository(get_main_session())
    dilicom_ref = dilicom_repo.create_status(obj.ean13, gln13, movement="to_create")
    return dilicom_ref


def remove_object_from_dilicom(object_id: int) -> Any:
    """Planifie la suppression d'un objet du référentiel Dilicom (delete_ref=True).

    Returns:
        L'ID de la référence Dilicom mise à jour.
    Raises:
        ValueError: si l'objet ou sa référence Dilicom n'existe pas.
        RuntimeError: en cas d'erreur lors du commit.
    """
    general_object_repo = ObjectsRepository(get_main_session())
    obj = general_object_repo.get_by_ref(object_id)
    if obj is None:
        raise ValueError(f"Objet avec l'id {object_id} introuvable.")
    dilicom_repo = DilicomReferencialRepository(get_main_session())
    existing = dilicom_repo.get_one_by_ean13(obj.ean13) if obj.ean13 else None
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

    Returns:
        L'objet GeneralObjects créé ou mis à jour.

    Raises:
        ValueError: Si la création ou la mise à jour échoue.
    """
    session = get_main_session()
    repo = ObjectsRepository(session)
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
    session = get_main_session()
    stmt = (
        select(distinct(column))
        .where(column.ilike(f"%{query}%"))
        .where(column.isnot(None))
        .where(column != "")
        .order_by(column)
        .limit(10)
    )
    return [row[0] for row in session.execute(stmt).all()]


def search_tags(query: str) -> List[Dict[str, Any]]:
    """Recherche des tags (id + name) correspondant à la requête."""
    session = get_main_session()
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


def create_tag(name: str, description: str = "") -> Dict[str, Any]:
    """Crée un nouveau tag et retourne son id + name."""
    session = get_main_session()
    repo = TagsRepository(session)
    tag = repo.create({"name": name, "description": description})
    return {"id": tag.id, "name": tag.name, "description": tag.description}
