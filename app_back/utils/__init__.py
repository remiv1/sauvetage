""""Module d'initialisation pour les utilitaires de l'application Sauvetage."""

from pathlib import Path
from .documents import create_document_buffer
from .mails import send_mail

TEMPLATES_DIR = Path(__file__).parent / "templates"
