"""Module utilitaire pour l'ensemble des services."""

import unicodedata
import re

def slugify(value: str) -> str:
    """Convertit une chaîne de caractères en un slug compatible avec les URL.
    Cette fonction normalise la chaîne en ASCII, la convertit en minuscules,
    remplace les caractères non alphanumériques par des tirets, et nettoie les tirets multiples.
    Args:
        value (str): La chaîne de caractères à convertir en slug.
    Returns:
        str: La chaîne de caractères convertie en slug.
    """
    # Normalisation Unicode → ASCII
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    value = value.lower()

    # Remplacement de tout ce qui n'est pas alphanumérique par des tirets
    value = re.sub(r"[^a-z0-9]+", "-", value)

    # Nettoyage des tirets multiples
    value = re.sub(r"-+", "-", value).strip("-")

    return value
