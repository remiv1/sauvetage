"""Module utils pour le blueprint stock"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
from flask import request as flask_request
from sqlalchemy import select, distinct
from app_front.config.db_conf import get_main_session
from app_front.blueprints.stock.forms import CreateObjectForm, OrderInCreateForm, OrderInLineForm
from db_models.objects import (
    Books,
    Tags,
    ObjectTags,
    ObjMetadatas,
    OrderIn,
    GeneralObjects,
    MediaFiles,
)
from db_models.repositories.stock import (
    StockRepository,
    DilicomReferencialRepository,
)
from db_models.repositories.objects.objects import ObjectsRepository
from db_models.repositories.tags import TagsRepository



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
    return stock_repo.update_movement_price(movement_id, price)


def get_supplier_orders() -> Sequence[OrderIn]:
    """Récupère la liste des commandes fournisseurs avec le nom du fournisseur
    et le nombre de lignes de commande.

    Returns:
        Sequence[OrderIn]: Liste des commandes avec relations complètement chargées.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_supplier_orders()


def get_supplier_returns() -> Sequence[OrderIn]:
    """Récupère la liste des retours fournisseurs avec le nom du fournisseur
    et le nombre de lignes de retour.

    Returns:
        Sequence[OrderIn]: Liste des retours avec relations complètement chargées.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_supplier_returns()


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
    return stock_repo.create_order_in_db(supplier_id)


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


def get_return_by_id(return_id: int) -> Sequence[OrderIn]:
    """Récupère les détails d'un retour fournisseur à partir de son ID.

    Args:
        return_id: L'identifiant du retour à récupérer.

    Returns:
        Sequence[OrderIn]: Une séquence contenant les objets récupérés.

    Raises:
        ValueError: Si le retour n'existe pas.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_return_by_id(return_id)


def create_order_in_line_db(form: OrderInLineForm, action: str = "create", line_id: int = 0) -> int:
    """Crée une nouvelle ligne de commande fournisseur en base à partir des données du formulaire.

    Args:
        form: Le formulaire contenant les données de la ligne de commande.

    Raises:
        ValueError: Si les données du formulaire sont invalides.
        RuntimeError: En cas d'erreur lors du commit.
    """
    order_id, general_object_id, quantity, unit_price, vat_rate = form.validate_form_data()
    stock_repo = StockRepository(get_main_session())
    if action == "create":
        return stock_repo.create_order_in_line_db(
            order_id,
            general_object_id,
            quantity,
            unit_price,
            vat_rate
        )
    if action == "edit":
        try:
            line_id = int(line_id)
            stock_repo.edit_order_in_line_db(
                line_id,
                general_object_id,
                quantity,
                unit_price,
                vat_rate
            )
            return line_id
        except ValueError as e:
            raise ValueError("L'ID de la ligne doit être un nombre entier.") from e
    if action == "delete":
        try:
            line_id = int(line_id)
            stock_repo.delete_order_in_line_db(line_id)
            return line_id
        except ValueError as e:
            raise ValueError("L'ID de la ligne doit être un nombre entier.") from e
    raise ValueError("Action inconnue : " + action)


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


def get_dilicom_referencial(object_id: int) -> Tuple[Optional[dict], Optional[GeneralObjects]]:
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


def create_object_complete(form: CreateObjectForm) -> int:
    """Crée un objet complet à partir du formulaire CreateObjectForm.

    Args:
        form: Le formulaire validé contenant les données de l'objet.

    Returns:
        L'objet GeneralObjects créé.

    Raises:
        ValueError: Si la création échoue.
    """
    session = get_main_session()
    repo = ObjectsRepository(session)

    obj_id = repo.create_object(
        supplier_id=int(form.supplier_id.data or 0),
        general_object_type=form.general_object_type.data,
        ean13=form.ean_13.data,
        name=form.name.data,
        description=form.description.data or "",
        price=float(form.price.data or 0),
    )

    if form.general_object_type.data == "book":
        _create_book(session, obj_id, form.book)

    tag_ids = flask_request.form.getlist("tag_id")
    _create_tags(session, obj_id, tag_ids)
    _create_metadata(session, obj_id, form.metadata)
    _create_media_files(session, obj_id, form.media_files)

    repo.commit_object()
    return obj_id


def _create_book(session: Any, object_id: int, book_form: Any) -> None:
    """Crée l'enregistrement Book associé à un objet."""
    book = Books(
        general_object_id=object_id,
        author=book_form.author.data or "",
        diffuser=book_form.diffuser.data or "",
        editor=book_form.editor.data or "",
        genre=book_form.genre.data or "",
        publication_year=int(book_form.publication_year.data)
            if book_form.publication_year.data else None,
        pages=int(book_form.pages.data) if book_form.pages.data else None,
        add_to_dilicom=book_form.add_to_dilicom.data == "true",
    )
    session.add(book)


def _create_tags(session: Any, object_id: int, tag_ids: List[str]) -> None:
    """Crée les associations objet-tag à partir des tag_id du formulaire."""
    for tid in tag_ids:
        if tid:
            session.add(ObjectTags(
                general_object_id=object_id,
                tag_id=int(tid),
            ))


def _create_metadata(session: Any, object_id: int, metadata_form: Any) -> None:
    """Crée les métadonnées associées à un objet."""
    meta_data = metadata_form.data if isinstance(metadata_form.data, dict) else {}
    session.add(ObjMetadatas(
        general_object_id=object_id,
        semistructured_data=meta_data,
    ))


def _create_media_files(session: Any, object_id: int, media_files_form: Any) -> None:
    """Crée les enregistrements MediaFiles associés à un objet."""
    media_files = media_files_form.data if isinstance(media_files_form.data, list) else []
    for mf in media_files:
        file_data = mf.get("file_data")
        file_bytes = None
        # Si file_data est un FileStorage (upload Flask), on lit directement
        if file_data and hasattr(file_data, "read"):
            file_bytes = file_data.read()
        session.add(MediaFiles(
            general_object_id=object_id,
            file_name=mf.get("file_name", ""),
            file_type=mf.get("file_type", ""),
            alt_text=mf.get("alt_text", ""),
            file_data=file_bytes,
            file_link=mf.get("file_url", None),
        ))


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
        {
            "id": row[0],
            "name": row[1],
            "description": row[2]
        }
        for row in session.execute(stmt).all()
    ]


def create_tag(name: str, description: str = "") -> Dict[str, Any]:
    """Crée un nouveau tag et retourne son id + name."""
    session = get_main_session()
    repo = TagsRepository(session)
    tag = repo.create({"name": name, "description": description})
    return {"id": tag.id, "name": tag.name, "description": tag.description}
