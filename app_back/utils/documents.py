"""Module utilitaire pour la gestion des documents (génération de PDF, etc.)."""

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from . import TEMPLATES_DIR

def create_document_buffer(template_name: str, data: dict) -> bytes:
    """
    Génère un document (PDF ou autre) en mémoire et retourne un buffer (bytes).
    Args:
        template_name: Le nom du template à utiliser pour générer le document.
        data: Un dictionnaire de données à passer au template pour le rendu.
    """
    # 1. Charger le template (HTML, Jinja2, etc.)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template(template_name)
    html = template.render(**data)

    # 2. Convertir en PDF (ou autre format)
    pdf_bytes = render_html_to_pdf(html)

    # 3. Retourner le buffer
    return pdf_bytes


def render_html_to_pdf(html: str) -> bytes:
    """
    Convertit un contenu HTML en PDF et retourne le résultat sous forme de bytes.
    Utilise une bibliothèque comme WeasyPrint, xhtml2pdf, ou wkhtmltopdf.
    """
    # Exemple avec WeasyPrint (assurez-vous d'avoir installé la bibliothèque)
    pdf = HTML(string=html).write_pdf()
    if not pdf:
        raise ValueError("La génération du PDF a échoué.")
    return pdf
