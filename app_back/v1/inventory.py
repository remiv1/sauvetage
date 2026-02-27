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
from app_back.v1.schems.inventory import (
    ParseRequest, ParseResponse, UnknownRequest, UnknownResponse,
    PrepareRequest, ReconciliationLine, ValidateLine, ValidateResponse,
    PlannedMovement, CommitRequest, CommitResponse, StatusResponse)
from app_back.db_connection.config import get_main_session
from db_models.objects.objects import GeneralObjects
from db_models.objects.inventory import InventoryMovements

router = APIRouter(prefix="/inventory", tags=["inventory"])

# Constantes du module
STATUS_FILE = os.environ.get("INVENTORY_STATUS_FILE", "/tmp/inventory_commit_status.json")
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

@router.post("/parse", response_model=ParseResponse,
    tags=["inventory", "utils"], summary="Parse EAN13",
    description="Normalise le texte et classifie en connu/inconnu.")
def parse_ean13(payload: ParseRequest) -> ParseResponse:
    """Normalise le texte brut et classifie chaque EAN13 en connu/inconnu."""
    eans = _normalize_ean13(payload.raw)
    unique_eans = _unique_preserve_order(eans)

    known: List[str] = []
    unknown: List[str] = []
    session = get_main_session()
    try:
        for ean in unique_eans:
            obj = session.execute(
                select(GeneralObjects).where(GeneralObjects.ean13 == ean)
            ).scalars().first()
            if obj:
                known.append(ean)
            else:
                unknown.append(ean)
    finally:
        session.close()

    return ParseResponse(ean13=eans, unknown=unknown, known=known)

@router.post("/unknown-products", response_model=UnknownResponse,
    tags=["inventory", "utils"], summary="Produits inconnus",
    description="Retourne les EAN13 qui ne correspondent à aucun produit en base.")
def unknown_products(payload: UnknownRequest) -> UnknownResponse:
    """Retourne les EAN13 qui ne correspondent à aucun produit en base."""
    session = get_main_session()
    unknown: List[str] = []
    try:
        for ean in payload.ean13:
            obj = session.execute(
                select(GeneralObjects).where(GeneralObjects.ean13 == ean)
            ).scalars().first()
            if not obj:
                unknown.append(ean)
    finally:
        session.close()
    return UnknownResponse(unknown=unknown)

# =========================================================================== #
#  Étape 5 – Préparation / conciliation                                      #
# =========================================================================== #

def _compute_theoretical_stock(session, general_object_id: int) -> int:
    """
    Calcule le stock théorique d'un objet par la somme des mouvements
    depuis le dernier inventaire.

    stock = last inventory + Σ in − Σ out
    """
    def _sum_by_type(mvt_type: str) -> int:
        val = session.execute(
            select(func.coalesce(func.sum(InventoryMovements.quantity), 0)).where(
                InventoryMovements.general_object_id == general_object_id,
                InventoryMovements.movement_type == mvt_type,
            )
        ).scalar_one()
        return int(val)

    def _last_inventory() -> int:
        return session.execute(
            select(InventoryMovements.quantity).where(
                InventoryMovements.general_object_id == general_object_id,
                InventoryMovements.movement_type == "inventory",
            ).order_by(InventoryMovements.created_at.desc())
        ).first() or 0

    inventory_init = _last_inventory()
    entrants = _sum_by_type("in")
    sortants = _sum_by_type("out")
    return inventory_init + entrants - sortants

@router.post("/prepare", response_model=List[ReconciliationLine],
    tags=["inventory"], summary="Préparer l'inventaire",
    description="Calcule, pour chaque EAN13 unique, le stock théorique vs réel.")
def prepare_inventory(payload: PrepareRequest) -> List[ReconciliationLine]:
    """Calcule, pour chaque EAN13 unique, le stock théorique vs réel."""
    # Compter les occurrences (le nombre de fois scanné = stock réel)
    counts: Dict[str, int] = {}
    set_eans = set(payload.ean13)
    for ean in set_eans:
        counts[ean] = payload.ean13.count(ean)

    session = get_main_session()
    results: List[ReconciliationLine] = []
    try:
        # Récupérer tous les objets concernés en une seule requête
        objects = session.execute(
            select(GeneralObjects).where(
                GeneralObjects.ean13.in_(list(counts.keys()))
            )
        ).scalars().all()
        go_by_ean: Dict[str, GeneralObjects] = {g.ean13: g for g in objects}

        for ean, real_count in counts.items():
            go = go_by_ean.get(ean)
            title = go.name if go else "(inconnu)"
            stock_th = _compute_theoretical_stock(session, go.id) if go else 0
            diff = real_count - stock_th
            results.append(ReconciliationLine(
                ean13=ean,
                title=title,
                stock_theorique=stock_th,
                stock_reel=real_count,
                difference=diff,
            ))
    finally:
        session.close()

    return results


# =========================================================================== #
#  Étape 6 – Validation                                                      #
# =========================================================================== #

@router.post("/validate", response_model=ValidateResponse)
def validate_inventory(lines: List[ValidateLine]):
    """Prépare les mouvements de stock pour chaque ligne validée."""
    planned: List[PlannedMovement] = []
    session = get_main_session()
    try:
        for line in lines:
            go = session.execute(
                select(GeneralObjects).where(GeneralObjects.ean13 == line.ean13)
            ).scalars().first()
            if not go:
                raise HTTPException(
                    status_code=404, detail=f"Produit {line.ean13} introuvable"
                )
            delta = line.stock_reel - line.stock_theorique
            if delta == 0:
                continue
            movement_type = "in" if delta > 0 else "out"
            planned.append(PlannedMovement(
                general_object_id=go.id,
                ean13=line.ean13,
                quantity=abs(delta),
                movement_type=movement_type,
                motifs=line.motifs,
                commentaire=line.commentaire,
            ))
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

def _run_commit(planned: List[Dict]) -> None:
    """Thread cible : applique les mouvements un par un et met à jour l'état."""
    started = datetime.now(timezone.utc).isoformat()
    try:
        _write_status({
            "status": "running", "progress": 0,
            "started_at": started, "message": "Démarrage…"
        })
        total = len(planned)
        session = get_main_session()
        try:
            for idx, mvt in enumerate(planned, start=1):
                movement = InventoryMovements(
                    general_object_id=mvt["general_object_id"],
                    movement_type=mvt["movement_type"],
                    quantity=mvt["quantity"],
                    price_at_movement=0.0,
                    source="inventory_workflow",
                    destination="stock",
                    notes=json.dumps({
                        "motifs": mvt.get("motifs", []),
                        "commentaire": mvt.get("commentaire"),
                    }, ensure_ascii=False),
                )
                session.add(movement)
                progress = int((idx / total) * 100)
                _write_status({
                    "status": "running", "progress": progress,
                    "started_at": started,
                    "message": f"Mouvement {idx}/{total} appliqué",
                })
            session.commit()
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
        _write_status({
            "status": "error", "progress": 0,
            "started_at": started, "message": str(exc),
        })

@router.post("/commit", response_model=CommitResponse)
def commit_inventory(payload: CommitRequest):
    """Lance un thread pour appliquer les mouvements de manière asynchrone."""
    movements = [m.model_dump() for m in payload.planned]
    thread = threading.Thread(target=_run_commit, args=(movements,), daemon=True)
    thread.start()
    return CommitResponse(status="started")


# =========================================================================== #
#  Étape 8 – Statut                                                          #
# =========================================================================== #

@router.get("/status", response_model=StatusResponse)
def inventory_status():
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
