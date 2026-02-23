"""Ce module contient des fonctions utilitaires liées aux pages front-end."""

from os.path import join, dirname, abspath
from typing import Dict, Any
from flask import render_template
import toml

def load_page_params(page_name: str) -> Dict[str, Any]:
    """Charge les paramètres d'une page à partir du fichier de configuration.
    Args:
        page_name (str): Le nom de la page pour laquelle charger les paramètres.
    Returns:
        dict: Un dictionnaire contenant les paramètres de la page, fusionnés avec les
              paramètres par défaut.
    """
    # Chargement du fichier de base et des liens vers la page spécifique
    base = toml.load("config/pages/pages.toml")
    links = base.get("links", {})

    # Récupération du chemin du fichier de configuration de la page
    file_path = links.get(page_name)

    # Si aucun chemin n'est trouvé pour la page, retourner les paramètres par défaut
    if not file_path:
        return base.get("default", {})

    # Récupération du chemin absolu du fichier de configuration de la page et chargement
    full_path = join(abspath(join(dirname(__file__), "..")), "config", "pages", file_path)
    config = toml.load(full_path)

    return config

def render_page(page_name: str, **context: Any) -> str:
    """Renders a page with its parameters and additional context."""
    params = load_page_params(page_name)
    return render_template(params.get("layout", {}).get("main_layout", "index.html"), **context)
