"""Module utils pour le blueprint stock"""

from typing import Sequence
from app_front.config.db_conf import get_main_session
from app_front.blueprints.stock.forms import OrderInCreateForm, OrderInLineForm
from db_models.repositories.stock import StockRepository, OrderIn


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
