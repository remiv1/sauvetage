"""Module de routage pour la gestion des mails de l'application Sauvetage."""

import base64
import logging
from pathlib import Path
from typing import Any

import toml
from fastapi import APIRouter, HTTPException

from app_back.db_connection import config
from app_back.utils.documents import create_document_buffer
from app_back.utils.mails import send_mail
from app_back.v1.schems.mails import MailSchema
from db_models.objects.stocks import OrderIn

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mails",
    tags=["documents", "admin", "auth", "mails"],
)


def _get_company_config() -> dict[str, Any]:
    """Charge la config entreprise depuis le fichier de config partagé du projet."""
    company_file = Path(__file__).resolve().parents[2] / "config" / "company.toml"
    if not company_file.exists():
        return {}
    data = toml.load(company_file)
    return data.get("company", {})


@router.post("/send-order",
             responses={
                 200: {"description": "Bon de commande envoyé avec succès."},
                 400: {"description": "Requête invalide ou données manquantes."},
                 404: {"description": "Commande introuvable."},
                 500: {"description": "Erreur lors de l'envoi du bon de commande."},
             })
def send_supplier_order_mail(payload: dict):
    """Génère le PDF du bon de commande côté back puis l'envoie par mail SMTP."""
    with config.main_session_ctx() as session:
        order_id = payload.get("order_id")
        if order_id is None:
            raise HTTPException(status_code=400, detail="order_id est requis.")

        order = session.get(OrderIn, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Commande {order_id} introuvable.")

        supplier = order.supplier
        supplier_email = str(
            payload.get("supplier_email") or (supplier.contact_email if supplier else "")
        ).strip()
        if not supplier_email:
            raise HTTPException(status_code=400, detail="Aucun email fournisseur renseigné.")

        company = _get_company_config()
        company_name = str(company.get("name", "Sauvetage"))
        contact_name = company.get("contact_name") or company.get("name") or "Service achats"
        contact_email = company.get("mail") or company.get("email") or ""
        order_ref = payload.get("order_ref") or order.order_ref or f"CMD-{order.id}"
        supplier_name = payload.get("supplier_name") or (
            supplier.name if supplier else "Fournisseur"
        )

        pdf_data = {
            "order": {
                "reference": order_ref,
                "external_ref": order.external_ref or "-",
                "supplier_name": supplier_name,
                "state": order.order_state,
            },
            "company": {
                "name": company_name,
                "address": company.get("address", "-"),
                "siret": company.get("siret", "-"),
                "greffe": company.get("greffe", "-"),
                "naf": company.get("naf", "-"),
                "tva": company.get("tva", "-"),
                "tel": company.get("tel", "-"),
                "email": contact_email,
            },
            "lines": [],
            "total_ht": "0.00 EUR",
            "qr_code_data_uri": "",
        }

        lines = []
        total_ht = 0.0
        for line in order.orderin_lines or []:
            if getattr(line, "line_state", None) == "cancelled":
                continue
            unit_price = float(getattr(line, "unit_price", 0) or 0)
            qty = float(getattr(line, "qty_ordered", 0) or 0)
            total_ht += qty * unit_price
            lines.append(
                {
                    "article_name": getattr(getattr(line, "general_object", None), "name", None)
                    or f"Article #{getattr(line, 'general_object_id', '?')}",
                    "ean13": getattr(getattr(line, "general_object", None), "ean13", None) or "-",
                    "quantity": int(qty),
                    "unit_price": f"{unit_price:.2f} EUR",
                    "line_total_ht": f"{(qty * unit_price):.2f} EUR",
                }
            )
        pdf_data["lines"] = lines
        pdf_data["total_ht"] = f"{total_ht:.2f} EUR"

        pdf_bytes = create_document_buffer(
            template_name="pdf/supplier_order_slip.html",
            data=pdf_data,
        )
        mail_payload = MailSchema(
            to=[supplier_email],
            subject=f"Bon de commande fournisseur {order_ref}",
            template="emails/purchase_order_email.html",
            data={
                "commande": {
                    "numero": order_ref,
                    "date": order.created_at.strftime("%d/%m/%Y") \
                        if getattr(order, "created_at", None) is not None \
                        else "",
                },
                "fournisseur": {"nom": supplier_name},
                "librairie": {
                    "nom": company_name,
                    "contact_nom": contact_name,
                    "contact_email": contact_email,
                },
            },
            attachments=[{
                "filename": f"{order_ref}.pdf",
                "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                "content_type": "application/pdf",
            }],
        )

        try:
            smtp_result = send_mail(
                to=mail_payload.to,
                cc=mail_payload.cc,
                bcc=mail_payload.bcc,
                subject=mail_payload.subject,
                template_name=mail_payload.template,
                data=mail_payload.data,
                attachments=[{
                    "filename": att.filename,
                    "content": base64.b64decode(att.content),
                    "content_type": att.content_type,
                } for att in mail_payload.attachments or []],
            )
        except Exception as exc:
            logger.exception(
                "Erreur réelle d'envoi du bon de commande fournisseur %s",
                order_ref,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de l'envoi du mail : {exc}",
            ) from exc

        logger.info(
            "Retour SMTP pour bon de commande %s -> %s",
            order_ref,
            smtp_result,
        )
        return {
            "status": smtp_result.get("status", "accepted_by_smtp"),
            "message": smtp_result.get(
                "message",
                "Le bon de commande a été accepté par le serveur SMTP. La livraison finale n'est " + \
                "pas confirmée par ce retour.",
            ),
            "smtp_result": smtp_result,
        }

@router.post("/create",
             responses={
                 200: {"description": "Mail créé avec succès."},
                 500: {"description": "Erreur lors de la création du mail."}
             })
def create_mail(payload: MailSchema):
    """
    Création d'un nouvel e-mail basé sur un template + données dynamiques.
    Args:
        payload (MailSchema): Les données nécessaires pour créer l'e-mail, incluant
        le template, les destinataires, le sujet, et les données dynamiques.
    """
    try:
        # Converti les pièces jointes base64 -> bytes
        attachments = []
        if payload.attachments:
            for att in payload.attachments:
                attachments.append({
                    "filename": att.filename,
                    "content": base64.b64decode(att.content),
                    "content_type": att.content_type
                })
        # Appel utilitaire pour créer le mail
        smtp_result = send_mail(
            to=payload.to,
            cc=payload.cc,
            bcc=payload.bcc,
            subject=payload.subject,
            template_name=payload.template,
            data=payload.data,
            attachments=attachments
        )
        logger.info("Retour SMTP pour mail générique -> %s", smtp_result)
        return {
            "status": smtp_result.get("status", "accepted_by_smtp"),
            "message": smtp_result.get(
                "message",
                "Le mail a été accepté par le serveur SMTP. La livraison finale n'est pas " + \
                "confirmée par ce retour.",
            ),
            "smtp_result": smtp_result,
        }
    except Exception as exc:
        logger.exception("Erreur SMTP lors de l'envoi générique du mail")
        message = f"Erreur lors de l'envoi du mail : {exc}"
        raise HTTPException(status_code=500, detail=message) from exc
