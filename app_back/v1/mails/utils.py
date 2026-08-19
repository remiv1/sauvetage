"""Utilitaires de préparation et d'envoi des e-mails."""

import base64
import logging
import smtplib
from datetime import datetime
from pathlib import Path
from typing import Any

import toml
from fastapi import HTTPException

from app_back.utils.documents import create_document_buffer
from app_back.utils.mails import send_mail
from app_back.v1.schems.mails import (
    AttachmentSchema,
    MailSchema,
    SupplierOrderMailSchema,
)
from db_models.objects.stocks import OrderIn

logger = logging.getLogger(__name__)


def _get_company_config() -> dict[str, Any]:
    """Charge la configuration entreprise depuis le fichier partagé du projet."""
    company_file = Path(__file__).resolve().parents[3] / "app_back" / "config" / "company.toml"
    if not company_file.exists():
        return {}
    data = toml.load(company_file)
    return data.get("company", {})


def _build_order_lines(order: OrderIn) -> tuple[list[dict[str, Any]], float]:
    """Prépare les lignes actives d'une commande pour le bon de commande PDF."""
    lines: list[dict[str, Any]] = []
    total_ht = 0.0
    for line in order.orderin_lines or []:
        if getattr(line, "line_state", None) == "cancelled":
            continue
        unit_price = float(getattr(line, "unit_price", 0) or 0)
        quantity = float(getattr(line, "qty_ordered", 0) or 0)
        line_total = quantity * unit_price
        total_ht += line_total
        general_object = getattr(line, "general_object", None)
        lines.append(
            {
                "article_name": getattr(general_object, "name", None)
                or f"Article #{getattr(line, 'general_object_id', '?')}",
                "ean13": getattr(general_object, "ean13", None) or "-",
                "quantity": int(quantity),
                "unit_price": f"{unit_price:.2f} EUR",
                "line_total_ht": f"{line_total:.2f} EUR",
            }
        )
    return lines, total_ht


def build_supplier_order_mail(
    order: OrderIn,
    payload: SupplierOrderMailSchema,
) -> tuple[MailSchema, str]:
    """Construit le message et le PDF associés à une commande fournisseur."""
    supplier = order.supplier
    supplier_email = payload.supplier_email or (
        supplier.contact_email if supplier else None
    )
    if not supplier_email:
        raise HTTPException(status_code=400, detail="Aucun email fournisseur renseigné.")

    company = _get_company_config()
    company_name = str(company.get("name", "Sauvetage"))
    contact_name = company.get("contact_name") or company_name or "Service achats"
    contact_email = company.get("mail") or company.get("email") or ""
    order_ref = payload.order_ref or order.order_ref or f"CMD-{order.id}"
    supplier_name = payload.supplier_name or (
        supplier.name if supplier else "Fournisseur"
    )
    order_date = datetime.now().strftime("%d/%m/%Y")
    lines, total_ht = _build_order_lines(order)
    pdf_data = {
        "order": {
            "reference": order_ref,
            "external_ref": order.external_ref or "-",
            "supplier_name": supplier_name,
            "state": order.order_state,
            "date": order_date,
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
        "lines": lines,
        "total_ht": f"{total_ht:.2f} EUR",
        "internal": False,
        "qr_code_data_uri": "",
    }
    try:
        pdf_bytes = create_document_buffer(
            template_name="pdf/supplier_order_slip.html",
            data=pdf_data,
        )
    except Exception as exc:
        logger.exception("Erreur de génération du PDF de commande %s", order_ref)
        raise HTTPException(
            status_code=500,
            detail="Impossible de générer le bon de commande.",
        ) from exc

    return MailSchema(
        to=[supplier_email],
        subject=f"Bon de commande fournisseur {order_ref}",
        template="emails/purchase_order_email.html",
        data={
            "commande": {
                "numero": order_ref,
                "date": order_date,
            },
            "fournisseur": {"nom": supplier_name},
            "librairie": {
                "nom": company_name,
                "contact_nom": contact_name,
                "contact_email": contact_email,
            },
        },
        attachments=[
            AttachmentSchema(
                filename=f"{order_ref}.pdf",
                content=base64.b64encode(pdf_bytes).decode("ascii"),
                content_type="application/pdf",
            )
        ],
    ), order_ref


def _decode_attachments(payload: MailSchema) -> list[dict[str, Any]]:
    """Convertit les pièces jointes base64 validées en contenu binaire."""
    try:
        return [
            {
                "filename": attachment.filename,
                "content": base64.b64decode(attachment.content, validate=True),
                "content_type": attachment.content_type,
            }
            for attachment in payload.attachments or []
        ]
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Une pièce jointe est encodée de manière invalide.",
        ) from exc


def send_mail_payload(payload: MailSchema, context: str) -> dict[str, Any]:
    """Envoie un message et transforme les erreurs SMTP en réponse HTTP cohérente."""
    try:
        smtp_result = send_mail(
            to=[str(address) for address in payload.to],
            cc=[str(address) for address in payload.cc] if payload.cc else None,
            bcc=[str(address) for address in payload.bcc] if payload.bcc else None,
            subject=payload.subject,
            template_name=payload.template,
            data=payload.data,
            attachments=_decode_attachments(payload),
        )
    except HTTPException:
        raise
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Erreur SMTP lors de l'envoi de %s", context)
        raise HTTPException(
            status_code=502,
            detail="Le serveur SMTP n'a pas pu accepter le message.",
        ) from exc
    except Exception as exc:
        logger.exception("Erreur de préparation du message pour %s", context)
        raise HTTPException(
            status_code=500,
            detail="Impossible de préparer le message à envoyer.",
        ) from exc

    logger.info("Retour SMTP pour %s -> %s", context, smtp_result)
    return {
        "status": smtp_result.get("status", "accepted_by_smtp"),
        "message": smtp_result.get(
            "message",
            "Le message a été accepté par le serveur SMTP ; "
            "sa livraison finale n'est pas confirmée.",
        ),
        "smtp_result": smtp_result,
    }
