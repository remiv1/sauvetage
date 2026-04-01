"""Utilitaires pour l'administration : TVA (SQLAlchemy direct) et utilisateurs (API)."""

from typing import Any, Dict, Optional
from urllib.parse import quote
from datetime import datetime, timezone

import requests
from sqlalchemy import select, func
from app_front.config import db_conf, USERS
from db_models.objects.vat import VatRate


# ── TVA — accès direct SQLAlchemy ─────────────────────────────────────────────

def get_vat_rates_paginated(
    *,
    code: Optional[int] = None,
    active_only: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Retourne la liste paginée des taux de TVA."""
    session = db_conf.get_main_session()
    try:
        stmt = select(VatRate)
        if code is not None:
            stmt = stmt.where(VatRate.code == code)
        if active_only:
            stmt = stmt.where(VatRate.date_end.is_(None))

        count_stmt = select(func.count()).select_from(stmt.subquery())  # pylint: disable=not-callable
        total = session.execute(count_stmt).scalar_one()

        offset = (page - 1) * per_page
        stmt = stmt.order_by(VatRate.code, VatRate.date_start.desc()).offset(offset).limit(per_page)
        rates = session.execute(stmt).scalars().all()

        items = [
            {
                "id": r.id,
                "code": r.code,
                "rate": float(r.rate),
                "label": r.label,
                "date_start": r.date_start.strftime("%d/%m/%Y") if r.date_start else "",
                "date_end": r.date_end.strftime("%d/%m/%Y") if r.date_end else None,
                "is_active": r.date_end is None,
            }
            for r in rates
        ]
        return {"items": items, "total": total, "page": page, "per_page": per_page}
    finally:
        session.close()


def get_vat_rate_by_id(vat_id: int) -> Optional[Dict[str, Any]]:
    """Retourne un taux de TVA par son identifiant."""
    session = db_conf.get_main_session()
    try:
        rate = session.get(VatRate, vat_id)
        if rate is None:
            return None
        return {
            "id": rate.id,
            "code": rate.code,
            "rate": float(rate.rate),
            "label": rate.label,
            "date_start": rate.date_start.isoformat() if rate.date_start else "",
            "date_end": rate.date_end.isoformat() if rate.date_end else None,
            "is_active": rate.date_end is None,
        }
    finally:
        session.close()


def create_vat_rate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Crée un nouveau taux de TVA."""
    session = db_conf.get_main_session()
    try:
        # Convertir les datetimes locaux en timezone-aware (UTC)
        date_start = data["date_start"]
        if hasattr(date_start, 'replace') and date_start.tzinfo is None:
            date_start = date_start.replace(tzinfo=timezone.utc)
        date_end = data.get("date_end")
        if date_end and hasattr(date_end, 'replace') and date_end.tzinfo is None:
            date_end = date_end.replace(tzinfo=timezone.utc)

        rate = VatRate(
            code=int(data["code"]),
            rate=float(data["rate"]),
            label=str(data["label"]),
            date_start=date_start,
            date_end=date_end,
        )
        session.add(rate)
        session.commit()
        return {"id": rate.id, "valid": True}
    except Exception as exc:
        session.rollback()
        raise ValueError(str(exc)) from exc
    finally:
        session.close()


def update_vat_rate(vat_id: int, data: Dict[str, Any]) -> bool:
    """Met à jour un taux de TVA existant."""
    session = db_conf.get_main_session()
    try:
        rate = session.get(VatRate, vat_id)
        if rate is None:
            return False
        # Convertir les datetimes locaux en timezone-aware (UTC)
        date_start = data["date_start"]
        if hasattr(date_start, 'replace') and date_start.tzinfo is None:
            date_start = date_start.replace(tzinfo=timezone.utc)
        date_end = data.get("date_end")
        if date_end and hasattr(date_end, 'replace') and date_end.tzinfo is None:
            date_end = date_end.replace(tzinfo=timezone.utc)

        rate.code = int(data["code"])
        rate.rate = float(data["rate"])
        rate.label = str(data["label"])
        rate.date_start = date_start
        rate.date_end = date_end
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        raise ValueError(str(exc)) from exc
    finally:
        session.close()


def close_vat_rate(vat_id: int) -> bool:
    """Ferme un taux de TVA en mettant sa date_end à maintenant."""
    session = db_conf.get_main_session()
    try:
        rate = session.get(VatRate, vat_id)
        if rate is None:
            return False
        rate.date_end = datetime.now(timezone.utc)
        session.commit()
        return True
    finally:
        session.close()


# ── Utilisateurs — via API FastAPI ────────────────────────────────────────────

def list_users_paginated(
    *,
    username: Optional[str] = None,
    email: Optional[str] = None,
    permissions: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_locked: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Liste paginée des utilisateurs via l'API."""
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    if username:
        params["username"] = username
    if email:
        params["email"] = email
    if permissions:
        params["permissions"] = permissions
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    if is_locked is not None:
        params["is_locked"] = str(is_locked).lower()

    response = requests.get(USERS["list"], params=params, timeout=10)
    if response.status_code // 100 != 2:
        raise requests.RequestException(f"Erreur API liste utilisateurs : {response.text}")
    return response.json()


def toggle_user_lock(username: str) -> Dict[str, Any]:
    """Bascule le verrou d'un utilisateur via l'API."""
    url = f"{USERS['toggle_lock']}/{quote(username)}"
    response = requests.post(url, timeout=10)
    if response.status_code // 100 != 2:
        raise requests.RequestException(f"Erreur toggle lock : {response.text}")
    return response.json()


def toggle_user_active(username: str) -> Dict[str, Any]:
    """Bascule l'état actif d'un utilisateur via l'API."""
    url = f"{USERS['toggle_active']}/{quote(username)}"
    response = requests.post(url, timeout=10)
    if response.status_code // 100 != 2:
        raise requests.RequestException(f"Erreur toggle active : {response.text}")
    return response.json()


# ── Logs MongoDB ───────────────────────────────────────────────────────────────

def get_logs_stats(year: Optional[int] = None) -> Dict[str, Any]:
    """Retourne des statistiques sur les logs de l'année courante (ou celle spécifiée)."""
    from app_front.config.db_conf import get_mongo_db   # pylint: disable=import-outside-toplevel
    target_year = str(year) if year else datetime.now().strftime("%Y")
    db = get_mongo_db()
    if db is None:
        # Retourner une structure cohérente avec celle attendue par le template
        return {"year": target_year, "stats": {}, "error": "MongoDB non disponible"}

    stats: Dict[str, Any] = {}
    for log_type in ["users", "logs", "clients", "métiers"]:
        collection_name = f"{target_year}-{log_type}"
        try:
            pipeline = [
                {"$group": {"_id": "$level", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ]
            result = list(db[collection_name].aggregate(pipeline))
            stats[log_type] = {r["_id"]: r["count"] for r in result}
            stats[f"{log_type}_total"] = sum(r["count"] for r in result)
        except (KeyError, TypeError, ValueError):
            stats[log_type] = {}
            stats[f"{log_type}_total"] = 0

    return {"year": target_year, "stats": stats}


def get_logs_recent(
    *,
    log_type: str = "logs",
    level: Optional[str] = None,
    user_id: Optional[str] = None,
    method: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """Retourne les logs récents paginés depuis MongoDB."""
    from app_front.config.db_conf import get_mongo_db   # pylint: disable=import-outside-toplevel
    db = get_mongo_db()
    if db is None:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}

    target_year = str(year) if year else datetime.now().strftime("%Y")
    collection_name = f"{target_year}-{log_type}"

    query: Dict[str, Any] = {}
    if level:
        query["level"] = level
    if user_id:
        query["user_id"] = user_id
    if method:
        query["action"] = method
    if status:
        # status peut être "2xx", "3xx", "4xx", "5xx" ou un code exact comme "200"
        if status.endswith("xx"):
            hundreds = int(status[0]) * 100
            query["status_code"] = {"$gte": hundreds, "$lt": hundreds + 100}
        elif status.isdigit():
            query["status_code"] = int(status)

    try:
        total = db[collection_name].count_documents(query)
        skip = (page - 1) * per_page
        cursor = (
            db[collection_name]
            .find(query, {"_id": 0})
            .sort("timestamp", -1)
            .skip(skip)
            .limit(per_page)
        )
        items = []
        for doc in cursor:
            if "timestamp" in doc and hasattr(doc["timestamp"], "strftime"):
                doc["timestamp"] = doc["timestamp"].strftime("%d/%m/%Y %H:%M:%S")
            items.append(doc)
        return {"items": items, "total": total, "page": page, "per_page": per_page}
    except (KeyError, TypeError, ValueError):
        return {"items": [], "total": 0, "page": page, "per_page": per_page}
