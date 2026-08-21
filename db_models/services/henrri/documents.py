"""
Module de gestion des documents pour les échanges avec Henrri.

Ce module fournit la classe de service pour la gestion des documents dans l'intégration
avec Henrri comme les devis, factures, etc.

Classes:
- ``HenrriDocumentsService``: Service de gestion des documents pour Henrri.
"""

from typing import Any, Sequence
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
    @staticmethod
    def _as_document(document: Document | Any) -> Document:
        """Convertit un objet local ou un modèle SDK Henri en Document."""
        if isinstance(document, Document):
            return document
        if hasattr(document, "to_dict_henrri"):
            return Document(**document.to_dict_henrri())
        raise TypeError(
            "Le document fourni n'est ni un Document Henri ni un objet local sérialisable."
        )

    @staticmethod
    def _as_document_line(line: DocumentLine | Any) -> DocumentLine:
        """Convertit un objet local ou un modèle SDK Henri en DocumentLine."""
        if isinstance(line, DocumentLine):
            return line
        if hasattr(line, "to_dict_henrri"):
            return DocumentLine(**line.to_dict_henrri())
        raise TypeError(
            "La ligne de document fournie n'est ni une DocumentLine Henri ni un objet sérialisable."
        )

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
            document: Document | Any,
        ) -> Document:
        """
        Crée un nouveau document sur Henrri (sans lignes, non finalisé).

        Arguments:
        - document (Document | Any): Le document local ou le modèle SDK Henri à créer.

        Returns:
        - Document: Le document créé avec son ID Henrri.
        """
        remote_document = self._as_document(document)
        response = self.client.documents.add(remote_document)
        return response

    def get_document(self, document_id: int) -> Document:
        """Récupère un document Henrri par son identifiant."""
        return self.client.documents.get(document_id)

    def modify_document(self, document_id: int, document: Document | Any) -> Document:
        """Met à jour l'en-tête d'un document Henrri non finalisé.

        Arguments:
            document_id: L'identifiant Henrri du document.
            document: Le document local ou le modèle SDK Henrri mis à jour.

        Returns:
            Document: Le document mis à jour.

        Raises:
            ValueError: Si le document fourni est marqué comme finalisé.
        """
        remote_document = self._as_document(document)
        if remote_document.finalized:
            raise ValueError("Impossible de modifier une facture finalisée")
        return self.client.documents.modify(document_id, remote_document)

    def add_line(self, document_id: int, line: DocumentLine | Any) -> DocumentLine:
        """
        Ajoute une ligne à un document existant sur Henrri.

        Arguments:
        - document_id (int): L'identifiant Henrri du document.
        - line (DocumentLine | Any): La ligne locale ou le modèle SDK Henri à ajouter.

        Returns:
        - DocumentLine: La ligne créée avec son ID Henrri.
        """
        remote_line = self._as_document_line(line)
        return self.client.document_lines.add(document_id, remote_line)

    def finalize_document(self, document_id: int) -> Document:
        """
        Finalise un document sur Henrri.

        Arguments:
        - document_id (int): L'identifiant Henrri du document à finaliser.

        Returns:
        - Document: Le document finalisé.
        """
        return self.client.documents.finalize(document_id)

    def get_pdf_bytes(self, document_id: int) -> bytes:
        """Récupère le PDF binaire d'un document Henrri."""
        return self.client.documents.get_pdf_bytes(document_id)

    def update_document(
            self,
            document_id: int,
            updated_document: Document | Any,
            updated_lines: Sequence[DocumentLine | Any],
        ) -> tuple[Document, Sequence[DocumentLine]]:
        """
        Met à jour un document existant sur Henrri.
        Les factures finalisées ne peuvent pas être modifiées.
        
        Arguments:
        - document_id (str): L'identifiant du produit à mettre à jour.
        - updated_document (Document | Any): Le document local ou le modèle SDK Henri mis à jour.
        - updated_lines (Sequence[DocumentLine | Any]): La liste des lignes mises à jour.

        Returns:
        - tuple[Document, list[DocumentLine]]:
        Le document mis à jour au format de la bibliothèque henrri-connect.
        """
        remote_document = self._as_document(updated_document)
        check = any(
            line.id is None
            for line in [self._as_document_line(line) for line in updated_lines]
        )
        if check:
            raise ValueError("Toutes les lignes doivent avoir un id")

        if remote_document.finalized:
            raise ValueError("Impossible de modifier une facture finalisée")

        response = self.client.documents.modify(document_id, remote_document)
        responses = []
        for line in [self._as_document_line(line) for line in updated_lines]:
            if line.id is None:
                raise ValueError("Toutes les lignes doivent avoir un id")
            document_line = self.client.document_lines.modify(document_id, line.id, line)
            responses.append(document_line)
        return response, responses
