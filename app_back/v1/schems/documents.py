"""Module de routage pour la gestion des mails de l'application Sauvetage."""

from typing import Dict, Any, Optional
from pydantic import BaseModel

class DocumentSchema(BaseModel):
    """Schéma de données pour la création d'un document."""
    template: str
    data: Dict[str, Any]
    base_url: Optional[str] = None
