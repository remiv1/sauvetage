"""Module utilitaire pour le workflow d'inventaire.

Opérations légères (CRUD produit, fournisseur) : accès direct à la base via
les repositories partagés (db_models).
Opérations lourdes (commit, prepare, validate…) : délèguent au micro-service
FastAPI (app-back) qui gère les traitements asynchrones.
"""

from os import getenv
from typing import Any, Dict, List, Optional
import requests
from sqlalchemy import select, func
from app_front.config.db_conf import get_main_session
from db_models.objects.objects import GeneralObjects, Books, OtherObjects
from db_models.objects.suppliers import Suppliers

# =========================================================================== #
#  Helpers HTTP – uniquement pour les opérations lourdes (FastAPI)            #
# =========================================================================== #

FASTAPI_BASE = getenv("FASTAPI_BASE_URL", "http://app-back:8000/api/v1")
_TIMEOUT = 30  # secondes

def _post(path: str, payload: Dict[str, Any] | List[Any]) -> Dict[str, Any]:
    """POST JSON vers le micro-service FastAPI (opérations lourdes uniquement)."""
    url = f"{FASTAPI_BASE}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Erreur de communication avec le service d'inventaire : {exc}") from exc

def _get(path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """GET vers le micro-service FastAPI (opérations lourdes uniquement)."""
    url = f"{FASTAPI_BASE}{path}"
    try:
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Erreur de communication avec le service d'inventaire : {exc}") from exc

def parse_ean13(raw: str, inventory_type: str = "complete",
                category: Optional[str] = None) -> Dict[str, Any]:
    """Envoie le texte brut d'EAN13 au service de parsing.

    Returns:
        {"ean13": [...], "unknown": [...], "known": [...]}
    """
    return _post("/inventory/parse", {
        "raw": raw,
        "inventory_type": inventory_type,
        "category": category,
    })

#---
def get_unknown_products(ean13_list: List[str]) -> Dict[str, Any]:
    """Renvoie la liste des EAN13 inconnus en base.

    Returns:
        {"unknown": [...]}
    """
    return _post("/inventory/unknown-products", {"ean13": ean13_list})

def prepare_inventory(ean13_list: List[str]) -> Any:
    """Calcule le stock théorique vs réel (opération lourde → FastAPI).

    Returns:
        Liste de dicts avec ean13, title, stock_theorique, stock_reel, difference.
    """
    return _post("/inventory/prepare", {"ean13": ean13_list})

def validate_inventory(lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Valide et prépare les mouvements pour chaque ligne (opération lourde → FastAPI).

    Returns:
        {"planned": [...]}
    """
    return _post("/inventory/validate", lines)

def commit_inventory(planned: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Lance l'application asynchrone des mouvements (opération lourde → FastAPI).

    Returns:
        {"status": "started"}
    """
    return _post("/inventory/commit", {"planned": planned})

def get_inventory_status() -> Dict[str, Any]:
    """Interroge l'état de la tâche de commit (opération lourde → FastAPI).

    Returns:
        {"running": false} ou {"status": "running", "progress": N, ...}
    """
    return _get("/inventory/status")

# =========================================================================== #
#  Opérations légères → accès direct à la base de données                    #
# =========================================================================== #

def create_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Crée un produit (GeneralObjects + Books ou OtherObjects) en accès DB direct.

    Args:
        product_data: dict avec ean13, product_type, supplier_id, title, category, price.
                      Si product_type == 'book' : author, diffuser, editor, genre,
                      publication_year, pages en plus.
    Returns:
        {"status": "created", "ean13": "...", "general_object_id": N}
    Raises:
        ValueError: si product_type invalide, EAN13 existant, fournisseur introuvable.
    """
    product_type = product_data.get("product_type", "book")
    if product_type not in ("book", "other"):
        raise ValueError(f"product_type invalide : '{product_type}'. "
                         "Valeurs acceptées : 'book', 'other'")

    ean13 = product_data.get("ean13", "")
    supplier_id = product_data.get("supplier_id")

    session = get_main_session()
    try:
        # EAN13 déjà existant ?
        existing = session.execute(
            select(GeneralObjects).where(GeneralObjects.ean13 == ean13)
        ).scalars().first()
        if existing:
            raise ValueError(f"EAN13 {ean13} existe déjà")

        # Fournisseur valide ?
        supplier = session.execute(
            select(Suppliers).where(Suppliers.id == supplier_id)
        ).scalars().first()
        if not supplier:
            raise ValueError(f"Fournisseur id={supplier_id} introuvable")

        # Création de l'objet général
        go = GeneralObjects(
            supplier_id=product_data.get("supplier_id"),
            general_object_type=product_data.get("product_type", "book"),
            ean13=product_data.get("ean13", ""),
            name=product_data.get("name", ""),
            description=product_data.get("description", ""),
            price=product_data.get("price", 0)
        )
        session.add(go)
        session.flush()

        # Création de l'objet enfant (Book ou OtherObjects)
        if product_type == "book":
            child = Books(
                general_object_id=go.id,
                author=product_data.get("author", ""),
                diffuser=product_data.get("diffuser", ""),
                editor=product_data.get("editor", ""),
                genre=product_data.get("genre", ""),
                publication_year=product_data.get("publication_year", ""),
                pages=product_data.get("pages", "")
            )
        else:
            child = OtherObjects(general_object_id=go.id)

        session.add(child)
        session.commit()

        return {"status": "created", "ean13": ean13, "general_object_id": go.id}
    except ValueError as e:
        session.rollback()
        raise ValueError(f"Erreur de validation des données du produit : {e}") from e
    except Exception as e:
        session.rollback()
        raise ValueError(f"Erreur lors de la création du produit : {e}") from e
    finally:
        session.close()

def search_suppliers(q: str = "") -> List[Dict[str, Any]]:
    """Recherche de fournisseurs par nom (ILIKE, accès DB direct).

    Returns:
        [{"id": 1, "name": "Hachette"}, ...]
    """
    session = get_main_session()
    try:
        query = (
            select(Suppliers)
            .where(Suppliers.is_active.is_(True), Suppliers.name.ilike(f"%{q}%"))
            .order_by(Suppliers.name)
            .limit(15)
        )
        results = session.execute(query).scalars().all()
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
        existing = session.execute(
            select(Suppliers).where(Suppliers.name == name)
        ).scalars().first()
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

def search_objects_info(q: dict[str, str]) -> List[str]:
    """
    Recherche d'éléments communs sur les livres
    - Liste des auteurs filtrés dans la requête.
    - Liste des distributeurs filtrés dans la requête.
    - Liste des éditeurs filtrés dans la requête.
    - Liste des catégories filtrées dans la requête.
    """
    session = get_main_session()
    modal = list(q.keys())
    if not modal:
        raise ValueError("Fournir au moins un critère de recherche")
    if len(modal) > 1:
        raise ValueError("Veuillez n'en fournir qu'un seul")
    if modal[0] == "author":
        req = q["author"]
        stmt = select(Books.author).where(
            func.unaccent(func.lower(Books.author))
                .ilike(func.unaccent(func.lower(f"%{req}%")))).distinct()
    elif modal[0] == "diffuser":
        req = q["diffuser"]
        stmt = select(Books.diffuser).where(
            func.unaccent(func.lower(Books.diffuser))
                .ilike(func.unaccent(func.lower(f"%{req}%")))).distinct()
    elif modal[0] == "editor":
        req = q["editor"]
        stmt = select(Books.editor).where(
            func.unaccent(func.lower(Books.editor))
                .ilike(func.unaccent(func.lower(f"%{req}%")))).distinct()
    elif modal[0] == "genre":
        req = q["genre"]
        stmt = select(Books.genre).where(
            func.unaccent(func.lower(Books.genre))
                .ilike(func.unaccent(func.lower(f"%{req}%")))).distinct()
    else:
        raise ValueError(f"Critère de recherche invalide : {modal[0]}. "
                         "Valeurs acceptées : 'author', 'diffuser', 'editor', 'genre'")
    try:
        response = session.execute(stmt).scalars().all()
        return list({r for r in response if r})  # Uniques et non vides
    finally:
        session.close()
