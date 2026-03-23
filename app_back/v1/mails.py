"""Module de routage pour la gestion des mails de l'application Sauvetage."""

import base64
from fastapi import APIRouter, HTTPException
from app_back.utils import send_mail
from app_back.v1.schems.mails import MailSchema

router = APIRouter(
    prefix="/mails",
    tags=["documents", "admin", "auth", "mails"],
)


@router.get("/create",
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
        send_mail(
            to=payload.to,
            cc=payload.cc,
            bcc=payload.bcc,
            subject=payload.subject,
            template_name=payload.template,
            data=payload.data,
            attachments=attachments
        )
        return {"status": "success", "message": "Mail envoyé avec succès."}
    except Exception as exc:
        message = f"Erreur lors de l'envoi du mail : {exc}"
        raise HTTPException(status_code=500, detail=message) from exc
