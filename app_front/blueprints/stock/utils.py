"""Module utils pour le blueprint stock"""

from sqlalchemy import select, func
from sqlalchemy.sql import distinct
from app_front.config.db_conf import get_main_session
from db_models.objects import InventoryMovements
from db_models.objects.objects import GeneralObjects

def get_zero_price_items() -> list[dict]:
    """Récupère les articles dont le dernier inventaire a un prix de revient à zéro.

    Retourne une liste de dictionnaires avec les clés :
    - `general_object_id`, `name`, `ean13`, `price_at_movement`, `movement_id`.
    """
    session = get_main_session()
    im = InventoryMovements
    go = GeneralObjects

    # Sous-requête simple : timestamp max par general_object_id (mouvements d'inventaire)
    latest = select(
                im.general_object_id,
                func.max(im.movement_timestamp).label("max_ts")
            ).where(
                im.movement_type == "inventory"
            ).group_by(
                im.general_object_id
            ).subquery()

    stmt = select(
                im.id.label("movement_id"),
                im.general_object_id,
                go.name,
                go.ean13,
                im.price_at_movement
            ).select_from(
                im.__table__.join(
                    latest,
                    (im.general_object_id == latest.c.general_object_id) &
                    (im.movement_timestamp == latest.c.max_ts)
                ).join(go, im.general_object_id == go.id)
            ).where(
                im.price_at_movement == 0
            )

    result = session.execute(stmt).all()
    return [
        {
            "movement_id": row[0],
            "general_object_id": row[1],
            "name": row[2],
            "ean13": row[3],
            "price_at_movement": row[4],
        }
        for row in result
    ]

def is_zero_price_items() -> bool:
    """
    Indique s'il existes des articles dont le dernier inventaire
    a un prix de revient à zéro
    """
    return len(get_zero_price_items()) > 0

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
    session = get_main_session()
    original = session.get(InventoryMovements, movement_id)
    if original is None:
        raise ValueError(f"Mouvement {movement_id} introuvable")

    new_movement = InventoryMovements(
        general_object_id=original.general_object_id,
        movement_type=original.movement_type,
        quantity=original.quantity,
        price_at_movement=price,
        source=original.source,
        destination=original.destination,
        notes=f"Correction prix (réf. mouvement #{movement_id})",
    )
    session.add(new_movement)
    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"Erreur lors de la création du mouvement : {exc}") from exc
    return new_movement.id
