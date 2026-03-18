"""Modules de gestion des sous-objets Livres liés aux objets généraux de la librairie."""

from typing import Any, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Books


class BooksRepository(BaseRepository):
    """
    Repository pour la gestion des livres liés aux objets généraux.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = Books()
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, book_data: Dict[str, Any]) -> Books:
        """
        Crée un nouvel objet de type livre.
        Les champs requis pour créer un livre sont :
        - general_object_id,
        - author,
        - publisher,
        - diffuser,
        - editor,
        - genre,
        - publication_year,
        - pages
        """
        # Levée d'une exception si des champs diffèrent des champs attendus pour un livre
        extra_keys = set(book_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Création du livre
        new_book = Books(**book_data)
        try:
            self.session.add(new_book)
            self.session.flush()
            return new_book
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création du livre : {str(e)}") from e

    def update(
        self,
        book_data: Dict[str, Any],
        book: Optional[Books] = None,
        book_id: Optional[int] = None,
    ) -> Books:
        """
        Met à jour un livre existant avec les données fournies.
        Les champs pouvant être mis à jour pour un livre sont :
            - author,
            - publisher,
            - diffuser,
            - editor,
            - genre,
            - publication_year,
            - pages
        Raise:
            - ValueError: Si des champs diffèrent des champs attendus pour un livre
                          ou si aucun livre ou id de livre n'est fourni pour la mise à jour.
        """
        # Levée d'une exception si des champs diffèrent des champs attendus pour un livre
        # ou si aucun livre ou id de livre n'est fourni pour la mise à jour
        extra_keys = set(book_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")
        if not book and not book_id:
            raise ValueError("Passer un objet ou un id pour la mise à jour du livre")
        if not book and book_id:
            book = self.session.get(Books, book_id)
            if not book:
                raise ValueError(f"Livre avec id {book_id} non trouvé")

        # Mise à jour du livre
        for key, value in book_data.items():
            setattr(book, key, value)

        try:
            self.session.flush()
            return book
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour du livre : {str(e)}"
            ) from e

    def save_from_form(
        self, form: Any, general_object_id: int, instance: Optional[Books] = None
    ) -> Books:
        """
        Met à jour un livre à partir des données d'un formulaire.
        Les champs pouvant être mis à jour pour un livre sont :
            - author,
            - publisher,
            - diffuser,
            - editor,
            - genre,
            - publication_year,
            - pages
        """
        if instance is None:
            instance = Books()
            self.session.add(instance)
        instance.general_object_id = general_object_id
        instance.author = form.author.data
        instance.diffuser = form.diffuser.data
        instance.editor = form.editor.data
        instance.genre = form.genre.data
        instance.publication_year = form.publication_year.data
        instance.pages = form.pages.data
        self.session.flush()
        return instance
