"""Repository de base pour les opérations sur les modèles de la base de données."""

from typing import Any, Dict, Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session


class BaseRepository:
    """Repository de base pour les opérations sur les modèles de la base de données."""

    def __init__(self, session: Session):
        self.session = session

    def get_one(self, model: type, **filters: Dict[str, Any]) -> Any | None:
        """Récupère un enregistrement unique en fonction de filtres dynamiques.
        Args:
            model (type): Le modèle de la base de données à interroger.
            **filters (Dict[str, Any]): Dictionnaire contenant le/les filtres sous la forme
            {champ: valeur}.
        Returns:
            Any | None: L'enregistrement correspondant aux filtres ou None s'il n'existe pas.
        """
        stmt = select(model).filter_by(**filters)
        return self.session.execute(stmt).scalars().first()

    def get_many(self, model: type, **filters: Dict[str, Any]) -> Sequence[Any] | None:
        """Récupère plusieurs enregistrements en fonction de filtres dynamiques.
        Args:
            model (type): Le modèle de la base de données à interroger.
            **filters (Dict[str, Any]): Dictionnaire contenant le/les filtres sous la forme
            {champ: valeur}.
        Returns:
            Sequence[Any] | None: La liste des enregistrements correspondant aux filtres ou
            None s'il n'en existe pas.
        """
        stmt = select(model).filter_by(**filters)
        return self.session.execute(stmt).scalars().all()
