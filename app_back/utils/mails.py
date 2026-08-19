"""Module utilitaire pour l'envoi d'e-mails."""

import logging
import re
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from app_back.config.mails import MailConfig
from .documents import TEMPLATES_DIR

logger = logging.getLogger(__name__)


def send_mail(
    to: List[str],
    subject: str,
    template_name: str,
    data: Dict,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Envoie un email basé sur un template + données, avec pièces jointes optionnelles.
    Args:
        to: Liste des adresses e-mail des destinataires.
        subject: Sujet de l'e-mail.
        template_name: Nom du template à utiliser pour le corps de l'e-mail.
        data: Dictionnaire de données à passer au template.
        cc: Liste optionnelle d'adresses e-mail en copie.
        bcc: Liste optionnelle d'adresses e-mail en copie cachée.
        attachments: Liste optionnelle de pièces jointes, chaque pièce jointe étant un dict
                        avec les clés 'filename' et 'content' (bytes) et 'content_type' (str).
    """
    # 1. Générer le contenu HTML
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template(template_name)
    html_body = template.render(**data)

    # 2. Générer la version texte (fallback)
    text_body = strip_html(html_body)

    # 3. Construire le message MIME
    message = build_mime_message(
        to=to,
        cc=cc,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        attachments=attachments
    )

    # 4. Envoyer via SMTP
    result = smtp_send(message, bcc=bcc)
    logger.info(
        "Envoi mail terminé - destinataires=%s, sujet=%s, template=%s, pièces_jointes=%s, " +
        "smtp_result=%s",
        to,
        subject,
        template_name,
        len(attachments or []),
        result,
    )
    return result

def strip_html(html: str) -> str:
    """Supprime les balises HTML pour générer une version texte du contenu."""
    # Implémentation simple, à améliorer selon les besoins (ex: utiliser BeautifulSoup)
    text = re.sub(r'<[^>]+>', '', html)
    return text.strip()

def build_mime_message(
    to: List[str],
    cc: Optional[List[str]],
    subject: str,
    html_body: str,
    text_body: str,
    attachments: Optional[List[Dict[str, str]]]
):
    """
    Construit un message MIME multipart avec les différentes parties (texte, HTML, pièces jointes).
    Args:
        to: Liste des destinataires.
        cc: Liste des destinataires en copie.
        bcc: Liste des destinataires en copie cachée.
        subject: Sujet de l'e-mail.
        html_body: Contenu HTML de l'e-mail.
        text_body: Contenu texte de l'e-mail.
        attachments: Liste de pièces jointes.
    Returns:
        Un objet MIMEMultipart prêt à être envoyé.
    """
    message = MIMEMultipart("mixed")
    message['To'] = ', '.join(to)
    if cc:
        message['Cc'] = ', '.join(cc)
    message['Subject'] = subject
    sender_name, sender_email = parseaddr(MailConfig.mail_default_sender)
    if not sender_email:
        sender_email = MailConfig.smtp_username
    if not sender_name:
        sender_name = "Editions Sauvetage"
    message['From'] = formataddr((sender_name, sender_email))

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(text_body, "plain", "utf-8"))
    alternative.attach(MIMEText(html_body, "html", "utf-8"))
    message.attach(alternative)

    # Ajouter les pièces jointes
    if attachments:
        for attachment in attachments:
            content_type = attachment.get('content_type', 'application/octet-stream')
            maintype, separator, subtype = content_type.partition('/')
            if not separator or not maintype or not subtype:
                maintype, subtype = 'application', 'octet-stream'
            part = MIMEBase(maintype, subtype)
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment["filename"]}"'
                )
            message.attach(part)

    return message

def smtp_send(
    message: MIMEMultipart,
    bcc: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Envoie le message MIME via SMTP et retourne le résultat réel de l'API SMTP.
    Le succès de sendmail ne garantit pas la livraison au destinataire final,
    seulement que le serveur SMTP a accepté le message pour la file d'envoi.
    """
    sender_name, sender_email = parseaddr(MailConfig.mail_default_sender)
    if not sender_email:
        sender_email = MailConfig.smtp_username
    if not sender_name:
        sender_name = "Editions Sauvetage"

    display_from = formataddr((sender_name, sender_email))
    envelope_from = MailConfig.smtp_username or sender_email

    smtp_server = MailConfig.smtp_server
    smtp_port = MailConfig.smtp_port
    smtp_username = MailConfig.smtp_username
    smtp_password = MailConfig.smtp_password
    recipients = []
    recipients += message['To'].split(', ')
    if message.get('Cc'):
        recipients += message['Cc'].split(', ')
    recipients += bcc or []
    recipients = [recipient for recipient in recipients if recipient]

    logger.info(
        "Tentative d'envoi SMTP - serveur=%s:%s, destinataires=%s, expéditeur_affiché=%s, "
        "mail_from=%s",
        smtp_server,
        smtp_port,
        recipients,
        display_from,
        envelope_from,
    )

    try:
        if MailConfig.smtp_use_ssl:
            smtp_client = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            smtp_client = smtplib.SMTP(smtp_server, smtp_port)

        with smtp_client as server:
            if MailConfig.smtp_use_tls and not MailConfig.smtp_use_ssl:
                server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            smtp_result = server.sendmail(
                envelope_from,
                recipients,
                message.as_string(),
            )
            logger.info(
                "SMTP a accepté la commande d'envoi - destinataires=%s, result=%s, "
                "note=ce retour confirme l'acceptation par le relay SMTP, pas la livraison finale",
                recipients,
                smtp_result,
            )
            return {
                "status": "accepted_by_smtp",
                "delivery_status": "smtp_accepted_not_confirmed",
                "recipients": recipients,
                "result": smtp_result,
                "message": "Le message a été accepté par le serveur SMTP ; " + \
                    "la livraison finale dans la messagerie du destinataire n'est pas confirmée " + \
                    "par ce retour.",
            }
    except Exception:
        logger.exception(
            "Erreur SMTP réelle lors de l'envoi à %s",
            recipients,
        )
        raise
