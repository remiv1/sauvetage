"""
Module utilitaire pour les services WooCommerce.
Contient des fonctions d'aide pour la manipulation des données liées à WooCommerce,
comme la fusion de dictionnaires de listes sans doublons.
"""

def merge_dicts_no_duplicates(d1: dict, d2: dict) -> dict:
    """
    Fusionne deux dictionnaires de listes en évitant les doublons dans les listes.
    Les clés présentes dans les deux dictionnaires auront leurs listes fusionnées sans doublons.
    Args:
    - d1 (dict): Premier dictionnaire à fusionner.
    - d2 (dict): Deuxième dictionnaire à fusionner.
    Returns:
    - dict: Dictionnaire fusionné avec des listes sans doublons.
    """
    result = {}

    for key in set(d1.keys()) | set(d2.keys()):
        list1 = d1.get(key, [])
        list2 = d2.get(key, [])

        # Fusionner les deux listes
        merged = list1.copy()

        for item in list2:
            if item not in merged:
                merged.append(item)

        result[key] = merged

    return result
