"""Module utils pour le blueprint stock"""

from app_front.config.db_conf import get_main_session
from app_front.blueprints.stock.forms import OrderInCreateForm
from db_models.repositories.stock import StockRepository


def get_zero_price_items() -> list[dict]:
    """Récupère les articles dont le dernier inventaire a un prix de revient à zéro.

    Retourne une liste de dictionnaires avec les clés :
    - `general_object_id`, `name`, `ean13`, `price_at_movement`, `movement_id`.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_zero_price_items()


def is_zero_price_items() -> bool:
    """
    Indique s'il existes des articles dont le dernier inventaire
    a un prix de revient à zéro
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


def get_supplier_orders() -> list[dict]:
    """Récupère la liste des commandes fournisseurs avec le nom du fournisseur
    et le nombre de lignes de commande.

    Returns:
        list[dict]: Liste de dictionnaires contenant les infos de chaque commande.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_supplier_orders()


def get_supplier_returns() -> list[dict]:
    """Récupère la liste des retours fournisseurs avec le nom du fournisseur
    et le nombre de lignes de retour.

    Returns:
        list[dict]: Liste de dictionnaires contenant les infos de chaque retour.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_supplier_returns()


def cancel_supplier_order(order_id: int) -> None:
    """Supprime une commande fournisseur et ses lignes associées.

    Les mouvements d'inventaire liés aux lignes sont désassociés (inventory_movement_id
    mis à NULL sur la ligne) mais conservés à titre de traçabilité.

    Args:
        order_id: L'identifiant de la commande à annuler.

    Raises:
        ValueError: Si la commande n'existe pas.
        RuntimeError: En cas d'erreur lors du commit.
    """
    stock_repo = StockRepository(get_main_session())
    stock_repo.cancel_supplier_order(order_id)


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


def get_order_by_id(order_id: int) -> dict:
    """Récupère les détails d'une commande fournisseur à partir de son ID.

    Args:
        order_id: L'identifiant de la commande à récupérer.

    Returns:
        dict: Un dictionnaire contenant les détails de la commande.

    Raises:
        ValueError: Si la commande n'existe pas.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_order_by_id(order_id)


def get_return_by_id(return_id: int) -> dict:
    """Récupère les détails d'un retour fournisseur à partir de son ID.

    Args:
        return_id: L'identifiant du retour à récupérer.

    Returns:
        dict: Un dictionnaire contenant les détails du retour.

    Raises:
        ValueError: Si le retour n'existe pas.
    """
    stock_repo = StockRepository(get_main_session())
    return stock_repo.get_return_by_id(return_id)
