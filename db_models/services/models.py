"""Modèles de données pour les services."""

from typing import Optional
from dataclasses import dataclass
from db_models.objects.suppliers import Suppliers

@dataclass
class Book:
    """Représente un livre."""
    title: str
    isbn: Optional[str] = None
    editor: Optional[Suppliers] = None
    editor_gln: Optional[str] = None
    editor_name: Optional[str] = None
    supplier: Optional[Suppliers] = None
    supplier_gln: Optional[str] = None
    supplier_name: Optional[str] = None
    description: Optional[str] = None
    price_ht: Optional[float] = None
    price_ttc: Optional[float] = None
    vat_rate: Optional[float] = None
    vat_rate_id: Optional[int] = None
    authors: Optional[str] = None
    year: Optional[str] = None
    pages: Optional[int] = None
