"""
Module de gestion des documents pour les échanges avec Henrri.

Ce module fournit la classe de service pour la gestion des documents dans l'intégration
avec Henrri comme les devis, factures, etc.

Classes:
- ``HenrriDocumentsService``: Service de gestion des documents pour Henrri.
"""

from typing import Sequence
from henrri_connect.models import Document, DocumentLine, DocumentQuery
from .base import HenrriService

class HenrriDocumentsService(HenrriService):
    """
    Service de gestion des documents pour Henrri.
    
    Arguments:
    - None

    Methodes:
    - get_documents(from_date, to_date, search): Récupère la liste des documents depuis Henrri.
    - create_document(document): Crée un nouveau produit sur Henrri.
    - create_documents_batch(documents): Crée plusieurs produits en une seule requête sur Henrri.
    - update_document(document_id, updated_document): Met à jour un produit existant sur Henrri.
    """

    def get_documents(self, from_date: str, to_date: str, search: str) -> Sequence[Document]:
        """
        Récupère la liste des documents depuis Henrri.
        
        Arguments:
        - from_date: Date de commencement de la recherche.
        - to_date: Date de fin de la recherche.
        - search: Chaine de recherche.

        Returns:
        - List[Document]: La liste des documents au format de la bibliothèque henrri-connect.
        """
        request: DocumentQuery = DocumentQuery(
            min_id=1,
            search=search,
            from_date=from_date,
            to_date=to_date
        )
        response = self.client.documents.list_documents(request=request)
        return response.elements or []

    def create_document(
            self,
            document: Document,
        ) -> Document:
        """
        Crée un nouveau document sur Henrri (sans lignes, non finalisé).

        Arguments:
        - document (Document): Le document à créer.

        Returns:
        - Document: Le document créé avec son ID Henrri.
        """
        response = self.client.documents.add(document)
        return response

    def add_line(self, document_id: int, line: DocumentLine) -> DocumentLine:
        """
        Ajoute une ligne à un document existant sur Henrri.

        Arguments:
        - document_id (int): L'identifiant Henrri du document.
        - line (DocumentLine): La ligne à ajouter.

        Returns:
        - DocumentLine: La ligne créée avec son ID Henrri.
        """
        return self.client.document_lines.add(document_id, line)

    def finalize_document(self, document_id: int) -> Document:
        """
        Finalise un document sur Henrri.

        Arguments:
        - document_id (int): L'identifiant Henrri du document à finaliser.

        Returns:
        - Document: Le document finalisé.
        """
        return self.client.documents.finalize(document_id)

    def update_document(
            self,
            document_id: int,
            updated_document: Document,
            updated_lines: Sequence[DocumentLine],
        ) -> tuple[Document, Sequence[DocumentLine]]:
        """
        Met à jour un document existant sur Henrri.
        Les factures finalisées ne peuvent pas être modifiées.
        
        Arguments:
        - document_id (str): L'identifiant du produit à mettre à jour.
        - updated_document (Document): Le produit mis à jour.
        - updated_lines (Sequence[DocumentLine]): La liste des lignes mis à jour.

        Returns:
        - tuple[Document, list[DocumentLine]]:
        Le document mis à jour au format de la bibliothèque henrri-connect.
        """
        check = any(line.id is None for line in updated_lines)  # Pour la cohérence métier
        if check:
            raise ValueError("Toutes les lignes doivent avoir un id")

        if updated_document.finalized:
            raise ValueError("Impossible de modifier une facture finalisée")

        response = self.client.documents.modify(document_id, updated_document)
        responses = []
        for line in updated_lines:
            if line.id is None: # Pour le type checker
                raise ValueError("Toutes les lignes doivent avoir un id")
            document_line = self.client.document_lines.modify(document_id, line.id, line)
            responses.append(document_line)
        return response, responses
