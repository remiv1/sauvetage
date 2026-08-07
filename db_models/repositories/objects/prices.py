"""Repository de gestion de l'historique des prix des objets."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db_models.objects import ObjectPrices
from db_models.repositories.base_repo import BaseRepository


class PricesRepository(BaseRepository):
    """Repository pour la gestion des lignes de prix (`ObjectPrices`)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.model = ObjectPrices
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def get_by_object_id(self, general_object_id: int) -> Sequence[ObjectPrices]:
        """Retourne l'historique de prix d'un objet, trie par date de debut."""
        stmt = (
            select(self.model)
            .where(self.model.general_object_id == general_object_id)
            .order_by(self.model.from_date.asc(), self.model.id.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def upsert_price(
        self,
        general_object_id: int,
        price: Decimal | float | int,
        from_date: date,
        to_date: Optional[date] = None,
    ) -> ObjectPrices:
        """Cree ou met a jour le prix pour une date de debut donnee."""
        stmt = select(self.model).where(
            self.model.general_object_id == general_object_id,
            self.model.from_date == from_date,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()

        try:
            if existing is not None:
                existing.price = Decimal(str(price))
                existing.to_date = to_date
                self.session.flush()
                return existing

            row = self.model(
                general_object_id=general_object_id,
                price=Decimal(str(price)),
                from_date=from_date,
                to_date=to_date,
            )
            self.session.add(row)
            self.session.flush()
            return row
        except SQLAlchemyError as err:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la sauvegarde du prix pour l'objet {general_object_id}: {err}"
            ) from err
