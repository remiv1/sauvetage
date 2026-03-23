"""Module utilitaire pour l'envoi d'e-mails."""

from typing import List, Dict, Optional
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.utils import formataddr
from email import encoders
import smtplib
from jinja2 import Environment, FileSystemLoader
from app_back.config.mails import MailConfig
from . import TEMPLATES_DIR

def send_mail(
    to: List[str],
    subject: str,
    template_name: str,
    data: Dict,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[Dict[str, str]]] = None
) -> None:
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
        bcc=bcc,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        attachments=attachments
    )

    # 4. Envoyer via SMTP
    smtp_send(message)

def strip_html(html: str) -> str:
    """Supprime les balises HTML pour générer une version texte du contenu."""
    # Implémentation simple, à améliorer selon les besoins (ex: utiliser BeautifulSoup)
    text = re.sub(r'<[^>]+>', '', html)
    return text.strip()

def build_mime_message(
    to: List[str],
    cc: Optional[List[str]],
    bcc: Optional[List[str]],
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
    if bcc:
        message['Bcc'] = ', '.join(bcc)
    message['Subject'] = subject

    # Ajouter les parties texte et HTML
    message.attach(MIMEText(text_body, 'plain'))
    message.attach(MIMEText(html_body, 'html'))

    # Ajouter les pièces jointes
    if attachments:
        for attachment in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment["filename"]}"'
                )
            part.add_header(
                'Content-Type',
                attachment.get('content_type', 'application/octet-stream')
                )
            message.attach(part)

    return message

def smtp_send(message: MIMEMultipart) -> None:
    """
    Envoie le message MIME via SMTP.
    Cette fonction doit être implémentée pour se connecter à votre serveur SMTP
    et envoyer le message. Vous pouvez utiliser smtplib ou une bibliothèque tierce.
    """
    # Exemple d'implémentation avec smtplib (à adapter selon votre configuration)

    sender_email = MailConfig.smtp_username
    sender_name = MailConfig.mail_default_sender
    smtp_server = MailConfig.smtp_server
    smtp_port = MailConfig.smtp_port
    smtp_username = MailConfig.smtp_username
    smtp_password = MailConfig.smtp_password
    recipients = []
    recipients += message['To'].split(', ')
    if message.get('Cc'):
        recipients += message['Cc'].split(', ')
    if message.get('Bcc'):
        recipients += message['Bcc'].split(', ')


    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(
            formataddr((sender_name, sender_email)),
            recipients,
            message.as_string()
        )
