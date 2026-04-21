"""Utilitaires pour les fournisseurs, utilisés par les routes et tests."""

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.sql import and_
from app_front.config import db_conf
from db_models.objects import Suppliers
from db_models.repositories.suppliers import SuppliersRepository


def search_suppliers(q: str = "", data_returned: str = "name") -> Optional[List[Dict[str, Any]]]:
    """
    Recherche de fournisseurs par nom (ILIKE, accès DB direct).

    Args:
        q: chaîne de recherche
        data_returned: type de données à retourner ("name", "id", "id_and_name")

    Returns:
        [{"id": 1, "name": "Hachette"}, ...]
    """
    session = db_conf.get_main_session()
    try:
        query = (
            select(Suppliers)
            .where(
                and_(
                    Suppliers.is_active.is_(True),
                    Suppliers.name.ilike(f"%{q}%")
                )
            )
            .order_by(Suppliers.name)
            .limit(10)
        )
        results = session.execute(query).scalars().all()
        if data_returned == "name":
            return [{"name": s.name} for s in results]
        if data_returned == "id":
            return [{"id": s.id} for s in results]
        if data_returned == "id_name_gln":
            return [
                {"id": s.id, "name": s.name, "gln13": s.gln13 or ""} for s in results
            ] if results else None
        return [{"id": s.id, "name": s.name} for s in results]
    finally:
        session.close()


def search_suppliers_paginated(
    *,
    name: str | None = None,
    gln13: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Recherche paginée des fournisseurs via le repository.

    Returns:
        Dict avec clés: items (list de dicts), total, page, per_page.
    """
    session = db_conf.get_main_session()
    try:
        repo = SuppliersRepository(session)
        result = repo.search_paginated(
            name=name, gln13=gln13, is_active=is_active, page=page, per_page=per_page,
        )
        result["items"] = [
            {
                "id": s.id,
                "name": s.name,
                "gln13": s.gln13 or "",
                "siren_siret": s.siren_siret or "",
                "vat_number": s.vat_number or "",
                "contact_email": s.contact_email or "",
                "contact_phone": s.contact_phone or "",
                "edi_active": s.edi_active,
                "is_active": s.is_active,
            }
            for s in result["items"]
        ]
        return result
    finally:
        session.close()


def get_supplier_by_id(supplier_id: int) -> Optional[Dict[str, Any]]:
    """Récupère un fournisseur par son ID.

    Returns:
        Dict avec les données du fournisseur, ou None.
    """
    session = db_conf.get_main_session()
    try:
        repo = SuppliersRepository(session)
        supplier = repo.get_by_id(supplier_id)
        if supplier is None:
            return None
        supplier_dict = supplier.to_dict()
        return supplier_dict
    finally:
        session.close()


def update_supplier_data(supplier_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Met à jour un fournisseur existant.

    Args:
        supplier_id: ID du fournisseur.
        data: Champs à mettre à jour (name, gln13, contact_email, contact_phone).

    Returns:
        Dict avec les données mises à jour.
    """
    session = db_conf.get_main_session()
    try:
        repo = SuppliersRepository(session)
        supplier = repo.update_supplier(
            supplier=Suppliers.from_dict({**data}),
            existing_id=supplier_id,
        )
        return supplier.to_dict()
    except ValueError as exc:
        session.rollback()
        raise ValueError(f"Erreur lors de la mise à jour : {exc}") from exc
    finally:
        session.close()


def toggle_supplier_active(supplier_id: int) -> Dict[str, Any]:
    """Bascule le statut actif/inactif d'un fournisseur.

    Returns:
        Dict avec les données du fournisseur mis à jour.
    """
    session = db_conf.get_main_session()
    try:
        repo = SuppliersRepository(session)
        supplier = repo.get_by_id(supplier_id)
        if supplier is None:
            raise ValueError("Fournisseur introuvable")
        supplier = repo.toggle_active(supplier)
        return supplier.to_dict()
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
    name = data.get("name")
    if not name:
        raise ValueError("Le nom du fournisseur est requis")
    session = db_conf.get_main_session()
    try:
        existing = (
            session.execute(select(Suppliers).where(Suppliers.name == name))
            .scalars()
            .first()
        )
        if existing:
            return {"id": existing.id, "name": existing.name}

        supplier = Suppliers(
            name=name,
            gln13=data.get("gln13"),
            siren_siret=data.get("siren_siret"),
            vat_number=data.get("vat_number"),
            address=data.get("address"),
            contact_email=data.get("contact_email"),
            contact_phone=data.get("contact_phone"),
            contact_fax=data.get("contact_fax"),
            web_site=data.get("web_site"),
            collect_days=data.get("collect_days"),
            cutoff_time=data.get("cutoff_time"),
            is_active=data.get("is_active"),
            edi_active=data.get("edi_active"),
        )
        session.add(supplier)
        session.commit()
        return {"id": supplier.id, "name": supplier.name}
    except Exception as exc:
        session.rollback()
        raise ValueError(f"Erreur lors de la création du fournisseur : {exc}") from exc
    finally:
        session.close()
