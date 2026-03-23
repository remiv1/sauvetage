"""Schémas Pydantic pour le workflow de commandes Dilicom."""

from pydantic import BaseModel

# =========================================================================== #
#  Fournisseurs                                                              #
# =========================================================================== #


class DilicomReferencialSchema(BaseModel):
    """Résultat d'une recherche de fournisseurs."""

    pass
