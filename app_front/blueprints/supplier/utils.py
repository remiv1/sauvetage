"""Utilitaires pour les fournisseurs, utilisés par les routes et tests."""

from typing import Any, Dict, List
from sqlalchemy import select
from app_front.config.db_conf import get_main_session
from db_models.objects.suppliers import Suppliers

def search_suppliers(q: str = "", data_returned: str = "name") -> List[Dict[str, Any]]:
    """
    Recherche de fournisseurs par nom (ILIKE, accès DB direct).

    Args:
        q: chaîne de recherche
        data_returned: type de données à retourner ("name", "id", "id_and_name")

    Returns:
        [{"id": 1, "name": "Hachette"}, ...]
    """
    session = get_main_session()
    try:
        query = (
            select(Suppliers)
            .where(Suppliers.is_active.is_(True), Suppliers.name.ilike(f"%{q}%"))
            .order_by(Suppliers.name)
            .limit(10)
        )
        results = session.execute(query).scalars().all()
        if data_returned == "name":
            return [{"name": s.name} for s in results]
        if data_returned == "id":
            return [{"id": s.id} for s in results]
        return [{"id": s.id, "name": s.name} for s in results]
    finally:
        session.close()


def create_supplier(data: Dict[str, Any]) -> Dict[str, Any]:
    """Crée un fournisseur complet, accès DB direct.

    Si un fournisseur du même nom existe déjà, retourne l'existant.

    Args:
        data: {
            "name": str (requis),
            "gln13": str (optionnel),
            "contact_email": str (optionnel),
            "contact_phone": str (optionnel)
        }
    Returns:
        {"id": 42, "name": "Nouveau fournisseur"}
    Raises:
        ValueError: en cas d'erreur DB ou données invalides.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Le nom du fournisseur est requis")

    gln13 = (data.get("gln13") or "").strip() or ""
    contact_email = (data.get("contact_email") or "").strip() or ""
    contact_phone = (data.get("contact_phone") or "").strip() or ""

    session = get_main_session()
    try:
        # Chercher si un fournisseur du même nom existe
        existing = (
            session.execute(select(Suppliers).where(Suppliers.name == name))
            .scalars()
            .first()
        )
        if existing:
            return {"id": existing.id, "name": existing.name}

        # Créer le nouveau fournisseur
        supplier = Suppliers(
            name=name,
            gln13=gln13,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )
        session.add(supplier)
        session.commit()
        return {"id": supplier.id, "name": supplier.name}
    except Exception as exc:
        session.rollback()
        raise ValueError(f"Erreur lors de la création du fournisseur : {exc}") from exc
    finally:
        session.close()
