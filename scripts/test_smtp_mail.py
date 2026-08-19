#!/usr/bin/env python3
"""Script de test d'envoi SMTP autonome.

Charge les variables de config/env/.env.fast puis envoie un e-mail simple
sans passer par le flux métier de l'application.
"""

from __future__ import annotations

import argparse
import logging
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "config" / "env" / ".env.fast"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")


def load_env_file(path: Path) -> None:
    """Charge les variables d'environnement depuis le fichier .env.fast."""
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_message(sender: str, recipients: list[str], subject: str, body: str) -> MIMEMultipart:
    """Construit un message MIME minimal."""
    message = MIMEMultipart("alternative")
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    logger.debug("Message construit: De=%s, À=%s, Sujet=%s", sender, recipients, subject)
    logger.debug("Corps du message: %s", body)
    return message


def main() -> int:
    """Point d'entrée du script de test SMTP."""
    parser = argparse.ArgumentParser(
        description="Tester un envoi SMTP à partir de config/env/.env.fast"
    )
    parser.add_argument(
        "--to",
        nargs="+",
        required=True,
        help="Adresse(s) e-mail destinataire(s)",
    )
    parser.add_argument(
        "--subject",
        default="Test SMTP Sauvetage",
        help="Sujet du message",
    )
    parser.add_argument(
        "--body",
        default="Ceci est un test SMTP direct depuis le script de test.",
        help="Corps du message",
    )
    parser.add_argument(
        "--env-file",
        default=str(ENV_FILE),
        help="Chemin vers le fichier .env à charger (par défaut: config/env/.env.fast)",
    )
    args = parser.parse_args()

    try:
        load_env_file(Path(args.env_file))
    except FileNotFoundError as exc:
        logger.exception("Erreur: %s", exc)
        return 2

    smtp_server = os.getenv("SMTP_SERVER", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_use_tls = _parse_bool(os.getenv("SMTP_USE_TLS"), default=True)
    smtp_use_ssl = _parse_bool(os.getenv("SMTP_USE_SSL"), default=False)

    if len(smtp_server) == 0 or len(smtp_username) == 0:
        logger.exception(
            "Erreur: la variable SMTP_SERVER est absente dans config/env/.env.fast : %s",
            str(sys.stderr),
        )
        return 2

    envelope_from = smtp_username

    recipients = args.to
    message = build_message(smtp_username, recipients, args.subject, args.body)

    logger.debug(
        "Envoi de test vers %s via %s:%s",
        ", ".join(recipients),
        smtp_server,
        smtp_port,
    )
    logger.debug("Header From: %s", smtp_username)
    logger.debug("MAIL FROM: %s", envelope_from)

    try:
        if smtp_use_ssl:
            smtp_client = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            smtp_client = smtplib.SMTP(smtp_server, smtp_port)

        with smtp_client as server:
            if smtp_use_tls and not smtp_use_ssl:
                server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.sendmail(envelope_from, recipients, message.as_string())

        logger.info("✅ E-mail envoyé avec succès.")
        return 0
    except smtplib.SMTPException as exc:
        logger.exception("Erreur SMTP: %s", exc)
        return 1
    except OSError as exc:
        logger.exception("Erreur réseau / socket: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
