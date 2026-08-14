"""Module utilitaire pour la gestion des documents (génération de PDF, etc.)."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

def create_document_buffer(
    template_name: str,
    data: dict,
    base_url: str | None = None,
) -> bytes:
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
    pdf_bytes = render_html_to_pdf(html, base_url=base_url)

    # 3. Retourner le buffer
    return pdf_bytes


def render_html_to_pdf(html: str, base_url: str | None = None) -> bytes:
    """
    Convertit un contenu HTML en PDF et retourne le résultat sous forme de bytes.
    Utilise WeasyPrint et exige les dépendances système associées.
    """
    try:
        from weasyprint import HTML # pylint: disable=C0415
    except (ImportError, OSError, RuntimeError) as exc:
        raise RuntimeError(
            "WeasyPrint n'est pas disponible : installez les dépendances système requises "
            "(libpango, libharfbuzz, libcairo, etc.)."
        ) from exc

    pdf = HTML(string=html, base_url=base_url).write_pdf()
    if not pdf:
        raise ValueError("La génération du PDF a échoué.")
    return pdf
