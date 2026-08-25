"""Constantes de sérialisation des produits WooCommerce."""

import os

FRONT_BASE_URL = os.environ.get("FRONT_BASE_URL", "")
PROTOCOL = "http"

OBJECT_TYPE_MAPPING: dict[str, list[int]] = {
    "book": [20],
    "cd": [22, 23],
    "dvd": [22, 24],
    "games": [21, 26],
    "spiritual_object": [21, 25],
    "other": [15],
}