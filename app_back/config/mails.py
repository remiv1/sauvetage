"""Module de configuration pour l'envoi d'e-mails."""

from os import getenv
from dataclasses import dataclass

@dataclass
class MailConfig:
    """Classe de configuration pour les paramètres d'envoi d'e-mails."""

    # Paramètres SMTP
    smtp_server: str = getenv("SMTP_SERVER", "smtp.example.com")
    smtp_port: int = int(getenv("SMTP_PORT", "587"))
    smtp_password: str = getenv("SMTP_PASSWORD", "")
    smtp_username: str = getenv("SMTP_USERNAME", "your_username")
    smtp_use_tls: bool = getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
    smtp_use_ssl: bool = getenv("SMTP_USE_SSL", "False").lower() in ("true", "1", "yes")
    mail_default_sender: str = getenv("MAIL_DEFAULT_SENDER", "Your Name <your_email@example.com>")
