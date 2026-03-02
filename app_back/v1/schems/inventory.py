"""Schémas Pydantic pour le workflow d'inventaire."""

from typing import List, Optional
from pydantic import BaseModel, Field

# =========================================================================== #
#  Fournisseurs                                                              #
# =========================================================================== #

class SupplierSearchResponse(BaseModel):
    """Résultat d'une recherche de fournisseurs."""
    id: int
    name: str

class SupplierCreate(BaseModel):
    """Données minimales pour créer un fournisseur depuis la modale produit."""
    name: str = Field(..., min_length=1, max_length=255)

class SupplierCreateResponse(BaseModel):
    """Confirmation de création d'un fournisseur."""
    id: int
    name: str

# =========================================================================== #
#  Inventaire                                                                #
# =========================================================================== #

class ParseRequest(BaseModel):
    """Requête de parsing des EAN13 bruts."""
    raw: str = Field(..., description="Texte brut contenant les EAN13")
    inventory_type: str = Field("complete", description="complete | partial | single")
    category: Optional[str] = Field(None, description="Catégorie/rayon (inventaire partiel)")

class ParseResponse(BaseModel):
    """Réponse du parsing : EAN13 valides, connus et inconnus."""
    ean13: List[str]
    unknown: List[str]
    known: List[str]

class UnknownRequest(BaseModel):
    """Liste d'EAN13 à vérifier."""
    ean13: List[str]

class UnknownResponse(BaseModel):
    """Liste des EAN13 absents de la base."""
    unknown: List[str]

class ProductCreate(BaseModel):
    """Données de création d'un produit (GeneralObjects + Books ou OtherObjects)."""
    ean13: str = Field(..., min_length=13, max_length=13)
    name: str
    product_type: str = Field("book", description="Type de produit : 'book' ou 'other'")
    supplier_id: int = Field(..., description="ID du fournisseur")
    author: Optional[str] = None
    category: Optional[str] = None
    price: float = Field(..., ge=0)
    publisher: Optional[str] = None

class ProductCreateResponse(BaseModel):
    """Confirmation de création."""
    status: str
    ean13: str
    general_object_id: int

class PrepareRequest(BaseModel):
    """Liste d'EAN13 scannés (doublons = quantité)."""
    ean13: List[str]
    inventory_type: Optional[str] = Field(
        "partial",
        description="Type d'inventaire : 'complete', 'partial' ou 'single'")

class ReconciliationLine(BaseModel):
    """Ligne de conciliation théorique vs réel."""
    ean13: str
    title: str
    stock_theorique: int
    stock_reel: int
    difference: int

class ValidateLine(BaseModel):
    """Ligne validée par l'utilisateur avec motifs."""
    ean13: str
    stock_theorique: int
    stock_reel: int
    motifs: List[str] = Field(default_factory=list)
    commentaire: Optional[str] = None

class PlannedMovement(BaseModel):
    """Mouvement de stock planifié."""
    general_object_id: int
    ean13: str
    quantity: int
    movement_type: str
    motifs: List[str]
    commentaire: Optional[str] = None

class ValidateResponse(BaseModel):
    """Résultat de la validation : mouvements planifiés."""
    planned: List[PlannedMovement]

class CommitRequest(BaseModel):
    """Liste des mouvements planifiés à appliquer."""
    planned: List[PlannedMovement]

class CommitResponse(BaseModel):
    """Confirmation de lancement de la tâche."""
    status: str

class StatusResponse(BaseModel):
    """État de la tâche asynchrone de commit."""
    running: bool = False
    status: Optional[str] = None
    progress: Optional[int] = None
    started_at: Optional[str] = None
    message: Optional[str] = None
