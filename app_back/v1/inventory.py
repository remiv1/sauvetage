"""Routes FastAPI pour le workflow d'inventaire.

Ce module contient toute la logique métier :
- Normalisation et validation des EAN13
- Détection des produits inconnus
- Calcul du stock théorique par mouvements
- Validation des écarts et préparation des mouvements
- Tâche asynchrone de commit (thread Python)
- Fichier JSON d'état pour le suivi
"""

import json
import os
import re
import threading
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from app_back.v1.schems.inventory import (
    ParseRequest,
    ParseResponse,
    PrepareRequest,
    ReconciliationLine,
    ValidateResponse,
    PlannedMovement,
    CommitRequest,
    CommitResponse,
    StatusResponse,
    ValidatePayload,
    ObjectPrice,
)
from app_back.db_connection import config
from db_models.objects import GeneralObjects, InventoryMovements

router = APIRouter(prefix="/inventory", tags=["inventory"])

# Constantes du module
STATUS_FILE = os.environ.get(
    "INVENTORY_STATUS_FILE", "/tmp/inventory_commit_status.json"
)
_EAN13_RE = re.compile(r"^\d{13}$")


def _normalize_ean13(raw: str) -> List[str]:
    """Normalise un texte brut en liste d'EAN13 valides.

    Split sur virgules, retours à la ligne, tabulations.
    Supprime les espaces et ne conserve que les chaînes de 13 chiffres.
    Les doublons sont conservés (ils représentent la quantité scannée).
    """
    if not raw:
        return []
    # Remplacer tous les séparateurs par des virgules
    normalized = raw.replace("\r\n", ",").replace("\n", ",").replace("\t", ",")
    tokens = normalized.split(",")
    result: List[str] = []
    for token in tokens:
        cleaned = token.strip().replace(" ", "")
        if not cleaned:
            continue
        if _EAN13_RE.match(cleaned):
            result.append(cleaned)
    return result


def _unique_preserve_order(items: List[str]) -> List[str]:
    """Déduplique une liste tout en conservant l'ordre d'apparition."""
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


@router.post(
    "/parse",
    tags=["inventory", "utils"],
    summary="Parse EAN13",
    description="Normalise le texte et classifie en connu/inconnu.",
    responses={
        200: {"model": ParseResponse, "description": "Résultat du parsing"},
        400: {"description": "Requête invalide (ex: inventory_type incorrect)"},
        500: {"description": "Erreur serveur lors de la récupération des EAN13 connus"},
    },
)
def parse_ean13(payload: ParseRequest) -> ParseResponse:
    """
    Normalise le texte brut et classifie chaque EAN13 en connu/inconnu.
    """
    inventory_type = payload.inventory_type
    category = payload.category
    if inventory_type not in {"complete", "partial", "single"}:
        message = "inventory_type doit être 'complete', 'partial' ou 'single'"
        raise HTTPException(status_code=400, detail=message)
    if inventory_type == "partial" and not category:
        message = "category est requise pour un inventaire partiel"
        raise HTTPException(status_code=400, detail=message)
    inventory_type = payload.inventory_type
    category = payload.category
    if inventory_type not in {"complete", "partial", "single"}:
        message = "inventory_type doit être 'complete', 'partial' ou 'single'"
        raise HTTPException(status_code=400, detail=message)
    if inventory_type == "partial" and not category:
        message = "category est requise pour un inventaire partiel"
        raise HTTPException(status_code=400, detail=message)
    eans = _normalize_ean13(payload.raw)
    unique_eans = _unique_preserve_order(eans)

    # Récupération des EAN13 connus en base selon le type d'inventaire
    # Récupération des EAN13 connus en base selon le type d'inventaire
    session = config.get_main_session()
    if inventory_type in {"partial", "single"}:
        stmt = select(GeneralObjects.ean13).where(GeneralObjects.ean13.in_(unique_eans))
    else:
        stmt = select(GeneralObjects.ean13)
    try:
        known_eans = set(session.execute(stmt).scalars().all())
    except Exception as exc:
        message = f"Erreur lors de la récupération des EAN13 connus : {exc}"
        raise RuntimeError(message) from exc
    if inventory_type in {"partial", "single"}:
        stmt = select(GeneralObjects.ean13).where(GeneralObjects.ean13.in_(unique_eans))
    else:
        stmt = select(GeneralObjects.ean13)
    try:
        known_eans = set(session.execute(stmt).scalars().all())
    finally:
        session.close()

    known = [ean for ean in unique_eans if ean in known_eans]
    unknown = [ean for ean in unique_eans if ean not in known_eans]
    known = [ean for ean in unique_eans if ean in known_eans]
    unknown = [ean for ean in unique_eans if ean not in known_eans]
    return ParseResponse(ean13=eans, unknown=unknown, known=known)


# =========================================================================== #
#  Étape 5 – Préparation / conciliation                                      #
# =========================================================================== #


def _compute_theoretical_stock(session, general_object_id: int) -> int:
    """
    Calcule le stock théorique d'un objet par la somme des mouvements
    depuis le dernier inventaire.

    stock = last inventory + Σ in − Σ out
    """

    def _sum_by_type(mvt_type: str, since: str) -> int:
        val = session.execute(
            select(func.coalesce(func.sum(InventoryMovements.quantity), 0)).where(
                InventoryMovements.general_object_id == general_object_id,
                InventoryMovements.movement_type == mvt_type,
                InventoryMovements.movement_timestamp > since,
            )
        ).scalar_one()
        return int(val)

    def _last_inventory() -> int:
        val = (
            session.execute(
                select(InventoryMovements.quantity)
                .where(
                    InventoryMovements.general_object_id == general_object_id,
                    InventoryMovements.movement_type == "inventory",
                )
                .order_by(InventoryMovements.movement_timestamp.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        return int(val) if val is not None else 0

    def _last_inventory_date() -> str:
        last = (
            session.execute(
                select(InventoryMovements.movement_timestamp)
                .where(
                    InventoryMovements.general_object_id == general_object_id,
                    InventoryMovements.movement_type == "inventory",
                )
                .order_by(InventoryMovements.movement_timestamp.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        return last.isoformat() if last is not None else "1970-01-01T00:00:00Z"

    inventory_init = _last_inventory()
    since = _last_inventory_date()
    entrants = _sum_by_type("in", since=since)
    sortants = _sum_by_type("out", since=since)
    return inventory_init + entrants - sortants


@router.post(
    "/prepare",
    tags=["inventory"],
    summary="Préparer l'inventaire",
    description="Calcule, pour chaque EAN13 unique, le stock théorique vs réel.",
)
def prepare_inventory(payload: PrepareRequest) -> List[ReconciliationLine]:
    """Calcule, pour chaque EAN13 unique, le stock théorique vs réel."""
    # Compter les occurrences (le nombre de fois scanné = stock réel)
    counts: Dict[str, int] = {}
    set_eans = set(payload.ean13)
    inventory_type = getattr(payload, "inventory_type", "partial")
    for ean in set_eans:
        counts[ean] = payload.ean13.count(ean)

    session = config.get_main_session()
    results: List[ReconciliationLine] = []
    if inventory_type == "complete":
        # Pour un inventaire complet, on doit aussi inclure les produits non scannés
        stmt = select(GeneralObjects)
    else:
        stmt = select(GeneralObjects).where(
            GeneralObjects.ean13.in_(list(counts.keys()))
        )
    objects = session.execute(stmt).scalars().all()
    go_by_ean: Dict[str, GeneralObjects] = {g.ean13: g for g in objects}
    if inventory_type == "complete":
        set_eans.update(
            go_by_ean.keys()
        )  # inclure les EAN13 non scannés pour le calcul

    try:
        for ean in set_eans:
            real_count = counts.get(ean, 0)
            go = go_by_ean.get(ean)
            title = go.name if go else "(inconnu)"
            stock_th = _compute_theoretical_stock(session, go.id) if go else 0
            diff = real_count - stock_th
            results.append(
                ReconciliationLine(
                    ean13=ean,
                    title=title,
                    stock_theorique=stock_th,
                    stock_reel=real_count,
                    difference=diff,
                )
            )
    finally:
        session.close()

    return results


# =========================================================================== #
#  Étape 6 – Validation                                                      #
# =========================================================================== #


@router.post(
    "/validate",
    tags=["inventory"],
    summary="Valider l'inventaire",
    description="Prépare les mouvements de stock pour chaque ligne validée.",
    responses={
        200: {"model": ValidateResponse, "description": "Mouvements préparés"},
        404: {"description": "Produit introuvable"},
        500: {"description": "Erreur serveur lors de la validation"},
    },
)
def validate_inventory(payload: ValidatePayload) -> ValidateResponse:
    """Prépare les mouvements de stock pour chaque ligne validée."""
    planned: List[PlannedMovement] = []
    lines = payload.lines
    session = config.get_main_session()
    try:
        eans = {line.ean13 for line in lines}
        objects = (
            session.execute(
                select(GeneralObjects).where(GeneralObjects.ean13.in_(eans))
            )
            .scalars()
            .all()
        )
        go_by_ean: Dict[str, GeneralObjects] = {g.ean13: g for g in objects}

        for line in lines:
            go = go_by_ean.get(line.ean13)
            if not go:
                raise HTTPException(
                    status_code=404, detail=f"Produit {line.ean13} introuvable"
                )
            delta = line.stock_reel - line.stock_theorique
            if delta == 0:
                continue  # Pas d'écart → pas de mouvement à planifier
            movement_type = "in" if delta > 0 else "out"
            planned.append(
                PlannedMovement(
                    general_object_id=go.id,
                    ean13=line.ean13,
                    quantity=abs(delta),
                    movement_type=movement_type,
                    motifs=line.motifs,
                    commentaire=line.commentaire,
                )
            )
        for line in lines:
            go = go_by_ean.get(line.ean13)
            if not go:
                raise HTTPException(
                    status_code=404, detail=f"Produit {line.ean13} introuvable"
                )
            planned.append(
                PlannedMovement(
                    general_object_id=go.id,
                    ean13=line.ean13,
                    quantity=line.stock_reel,
                    movement_type="inventory",
                    motifs=line.motifs,
                    commentaire=line.commentaire,
                )
            )
    finally:
        session.close()

    return ValidateResponse(planned=planned)


# =========================================================================== #
#  Étape 7 – Commit asynchrone                                               #
# =========================================================================== #


def _write_status(data: Dict) -> None:
    """Écrit le fichier JSON d'état de la tâche."""
    with open(STATUS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)


def _get_prices_at_movement(objects_id: List[int]) -> List[ObjectPrice]:
    """Récupère le prix au moment du mouvement pour un objet général donné."""

    def _get_last_inventory_price(oid: int):
        """Récupère le prix du dernier mouvement d'inventaire pour un objet général."""
        stmt = (
            select(
                InventoryMovements.price_at_movement,
                InventoryMovements.movement_timestamp,
            )
            .where(
                InventoryMovements.general_object_id == oid,
                InventoryMovements.movement_type == "inventory",
            )
            .order_by(InventoryMovements.movement_timestamp.desc())
            .limit(1)
        )
        return session.execute(stmt).first()

    def _get_avg_in_price_since(oid: int, since: str) -> float:
        """Récupère le prix moyen des mouvements 'in' depuis une date donnée."""
        stmt = select(
            func.coalesce(func.avg(InventoryMovements.price_at_movement), 0.0)
        ).where(
            InventoryMovements.general_object_id == oid,
            InventoryMovements.movement_type == "in",
            InventoryMovements.movement_timestamp > since,
        )
        return session.execute(stmt).scalar_one()

    if not objects_id:
        return []

    session = config.get_main_session()
    try:
        results: List[ObjectPrice] = []
        # travailler sur l'ensemble dédupliqué d'ids
        for oid in set(objects_id):
            # dernier prix enregistré pour le type 'inventory'
            last_row = _get_last_inventory_price(oid)
            last_price = (
                float(last_row[0]) if last_row and last_row[0] is not None else 0.0
            )
            last_ts = last_row[1] if last_row and last_row[1] is not None else None

            # moyenne des prix des mouvements 'in' depuis la dernière date d'inventaire
            # (si présente), sinon sur tout l'historique 'in'
            if last_ts is not None:
                avg_in = _get_avg_in_price_since(oid, last_ts)
            else:
                avg_in = _get_avg_in_price_since(oid, "1970-01-01T00:00:00Z") or 0.0

            avg_in = float(avg_in or 0.0)
            final_price = last_price + avg_in

            # récupérer l'ean13 de l'objet général (peut être None)
            ean = session.execute(
                select(GeneralObjects.ean13).where(GeneralObjects.id == oid)
            ).scalar_one_or_none()

            if not ean:
                raise RuntimeError(
                    f"Objet général {oid} introuvable pour récupérer l'EAN13"
                )

            results.append(
                ObjectPrice(
                    general_object_id=oid,
                    ean13=ean,
                    price_at_movement=final_price,
                )
            )

        return results
    finally:
        session.close()


def _run_commit(planned: List[Dict], price_by_object_id: Dict[int, float]) -> None:
    """
    Thread cible : applique les mouvements un par un et met à jour l'état.

    args:
        - planned : liste de mouvements à appliquer, sous forme de dicts
                    (issus de ValidateResponse)
        - price_by_object_id : dictionnaire mapping les IDs d'objets généraux à leur prix
                                au moment du mouvement
    """
    started = datetime.now(timezone.utc).isoformat()
    try:
        _write_status(
            {
                "status": "running",
                "progress": 0,
                "started_at": started,
                "message": "Démarrage…",
            }
        )
        total = len(planned)
        session = config.get_main_session()
        try:
            for idx, mvt in enumerate(planned, start=1):
                movement = InventoryMovements(
                    general_object_id=mvt["general_object_id"],
                    movement_type=mvt["movement_type"],
                    quantity=mvt["quantity"],
                    price_at_movement=price_by_object_id.get(
                        mvt["general_object_id"], 0.0
                    ),
                    source="inventory_workflow",
                    destination="stock",
                    notes=json.dumps(
                        {
                            "motifs": mvt.get("motifs", []),
                            "commentaire": mvt.get("commentaire"),
                        },
                        ensure_ascii=False,
                    ),
                )
                session.add(movement)
                progress = int((idx / total) * 100)
                _write_status(
                    {
                        "status": "running",
                        "progress": progress,
                        "started_at": started,
                        "message": f"Mouvement {idx}/{total} appliqué",
                    }
                )
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise RuntimeError(f"Erreur lors de l'application des mouvements : {exc}") from exc
        except Exception as exc:
            session.rollback()
            raise RuntimeError(f"Erreur lors du commit : {exc}") from exc
        finally:
            session.close()
            # Succès → supprimer le fichier d'état
            try:
                os.remove(STATUS_FILE)
            except FileNotFoundError:
                pass
    except (ValueError, TypeError, OSError, RuntimeError) as exc:
        _write_status(
            {
                "status": "error",
                "progress": 0,
                "started_at": started,
                "message": str(exc),
            }
        )


@router.post(
    "/commit",
    tags=["inventory"],
    summary="Lancer le commit de l'inventaire",
    description="Lance un thread pour appliquer les mouvements de manière asynchrone.",
    responses={
        200: {"model": CommitResponse, "description": "Tâche de commit lancée"},
        400: {
            "description": "Requête invalide (ex: données de mouvements incorrectes)"
        },
        500: {"description": "Erreur serveur lors du lancement du commit"},
    },
)
def commit_inventory(payload: CommitRequest) -> CommitResponse:
    """Lance un thread pour appliquer les mouvements de manière asynchrone."""
    movements = [m.model_dump() for m in payload.planned]
    objects_ids = [m["general_object_id"] for m in movements]
    prices = _get_prices_at_movement(objects_ids)
    price_by_object_id = {p.general_object_id: p.price_at_movement for p in prices}
    thread = threading.Thread(
        target=_run_commit, args=(movements, price_by_object_id), daemon=True
    )
    thread.start()
    return CommitResponse(status="started")


# =========================================================================== #
#  Étape 8 – Statut                                                          #
# =========================================================================== #


@router.get(
    "/status",
    tags=["inventory"],
    summary="Obtenir le statut du commit de l'inventaire",
    description="Retourne l'état courant de la tâche de commit.",
    responses={
        200: {
            "model": StatusResponse,
            "description": "Statut actuel de la tâche de commit",
        },
        500: {"description": "Erreur serveur lors de la récupération du statut"},
    },
)
def inventory_status() -> StatusResponse:
    """Retourne l'état courant de la tâche de commit."""
    if not os.path.exists(STATUS_FILE):
        return StatusResponse(running=False)
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return StatusResponse(
            running=True,
            status=data.get("status"),
            progress=data.get("progress"),
            started_at=data.get("started_at"),
            message=data.get("message"),
        )
    except (json.JSONDecodeError, OSError):
        return StatusResponse(running=False)
