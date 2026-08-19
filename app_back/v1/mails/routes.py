"""Routes FastAPI de gestion des e-mails."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app_back.db_connection import config
from app_back.v1.schems.mails import MailSchema, SupplierOrderMailSchema
from db_models.objects.stocks import OrderIn

from .utils import build_supplier_order_mail, send_mail_payload

router = APIRouter(
    prefix="/mails",
    tags=["documents", "admin", "auth", "mails"],
)


@router.post(
    "/send-order",
    responses={
        200: {"description": "Bon de commande envoyé avec succès."},
        400: {"description": "Requête invalide ou données manquantes."},
        404: {"description": "Commande introuvable."},
        500: {"description": "Erreur lors de l'envoi du bon de commande."},
        502: {"description": "Le relais SMTP est indisponible ou a refusé le message."},
    },
)
def send_supplier_order_mail(payload: SupplierOrderMailSchema) -> dict[str, Any]:
    """Génère le PDF du bon de commande côté back puis l'envoie par mail SMTP."""
    with config.main_session_ctx() as session:
        order = session.get(OrderIn, payload.order_id)
        if order is None:
            raise HTTPException(
                status_code=404,
                detail=f"Commande {payload.order_id} introuvable.",
            )
        mail_payload, order_ref = build_supplier_order_mail(order, payload)

    return send_mail_payload(mail_payload, f"la commande fournisseur {order_ref}")


@router.post(
    "/create",
    responses={
        200: {"description": "Mail créé avec succès."},
        400: {"description": "Pièce jointe invalide."},
        500: {"description": "Impossible de préparer le message."},
        502: {"description": "Le relais SMTP est indisponible ou a refusé le message."},
    },
)
def create_mail(payload: MailSchema) -> dict[str, Any]:
    """Envoie un e-mail construit depuis un template et des données dynamiques."""
    return send_mail_payload(payload, "le mail générique")
