"""Module de routage pour la gestion des mails de l'application Sauvetage."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr

class AttachmentSchema(BaseModel):
    """Schéma de données pour une pièce jointe d'e-mail."""
    filename: str
    content: str  # base64
    content_type: Optional[str] = "application/octet-stream"

class MailSchema(BaseModel):
    """Schéma de données pour la création d'un e-mail."""
    to: List[EmailStr]
    subject: str
    template: str
    data: Dict[str, Any]

    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None

    attachments: Optional[List[AttachmentSchema]] = None
