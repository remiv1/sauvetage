"""
Module de configuration pour l'application.
"""

from .mails import MailConfig
from .security import get_security_token

__all__ = [
    "MailConfig",
    "get_security_token",
]
