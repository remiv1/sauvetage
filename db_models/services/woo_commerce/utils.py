"""
Module utilitaire pour les services WooCommerce.
Contient des fonctions d'aide pour la manipulation des données liées à WooCommerce,
comme la fusion de dictionnaires de listes sans doublons.
"""
from typing import Any
from decimal import Decimal


def _serialize_decimals(obj: Any) -> Any:
    """
    Remplace les objets Decimal par des chaînes dans une structure récursive.

    Args:
        obj: structure (dict/list/primitive) pouvant contenir des Decimal

    Returns:
        même structure avec les Decimal convertis en str
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _serialize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_decimals(v) for v in obj]
    return obj


def _find_identity_key(item: dict, merged: list[dict]) -> str | None:
    """
    Trouve la clé d'identité commune entre un élément et la liste fusionnée.
    
    Args:
        item: Élément à vérifier
        merged: Liste d'éléments fusionnés
        
    Returns:
        La clé d'identité trouvée, ou None
    """
    id_keys = ['name', 'key', 'slug']
    return next((k for k in id_keys if k in item and any(k in m for m in merged)), None)


def _item_exists(item: Any, merged: list[Any], id_key: str | None) -> bool:
    """
    Vérifie si un élément existe déjà dans la liste fusionnée.
    
    Args:
        item: Élément à vérifier
        merged: Liste d'éléments fusionnés
        id_key: Clé d'identité à utiliser (pour les dictionnaires)
        
    Returns:
        True si l'élément existe déjà, False sinon
    """
    if id_key and isinstance(item, dict):
        return any(m.get(id_key) == item.get(id_key) for m in merged)
    return item in merged


def _merge_attribute_lists(list1: list[Any], list2: list[Any]) -> list[Any]:
    """
    Fusionne deux listes d'attributs WooCommerce en évitant les doublons.
    
    Gère les cas:
    - Listes de dictionnaires: utilise une clé d'identité ('name', 'key', 'slug')
    - Listes simples: vérifie l'égalité directe
    
    Args:
        list1: Première liste d'attributs
        list2: Deuxième liste d'attributs
        
    Returns:
        Liste fusionnée sans doublons
    """
    if not list1 and not list2:
        return []
    if not list1:
        return list2.copy()
    if not list2:
        return list1.copy()

    merged = list1.copy()
    is_dict_list = merged and isinstance(merged[0], dict)

    for item in list2:
        id_key = _find_identity_key(item, merged) \
            if is_dict_list and isinstance(item, dict) else None

        if not _item_exists(item, merged, id_key):
            merged.append(item)

    return merged


def merge_dicts_no_duplicates(d1: dict[str, Any], d2: dict[str, Any]) -> dict[str, Any]:
    """
    Fusionne deux dictionnaires en évitant les doublons dans les valeurs.
    
    Gère les cas:
    - Dictionnaires simples: fusion des clés
    - Listes de valeurs simples: fusion avec vérification d'égalité
    - Listes de dictionnaires: fusion avec clé d'identité (name, key, slug)
    
    Args:
        d1: Premier dictionnaire à fusionner
        d2: Deuxième dictionnaire à fusionner
        
    Returns:
        Dictionnaire fusionné avec valeurs sans doublons
    """
    # Normaliser les paramètres pour s'assurer qu'ils sont des dictionnaires
    if not isinstance(d1, dict):
        d1 = {}
    if not isinstance(d2, dict):
        d2 = {}

    result = {}
    for key in set(d1.keys()) | set(d2.keys()):
        val1 = d1.get(key, [])
        val2 = d2.get(key, [])

        # Si les deux valeurs sont des listes
        if isinstance(val1, list) and isinstance(val2, list):
            result[key] = _merge_attribute_lists(val1, val2)
        # Si une seule valeur est une liste
        elif isinstance(val1, list):
            result[key] = val1
        elif isinstance(val2, list):
            result[key] = val2
        # Sinon, prendre la première valeur non-vide
        else:
            result[key] = val1 if val1 else val2

    return result
