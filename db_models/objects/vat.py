"""Module contenant le modèle de taux de TVA."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Integer, String, Numeric, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from db_models.objects import QueryMixin


class VatRate(WorkingBase, QueryMixin):
    """Référentiel des codes et taux de TVA avec historique de validité.

    Codes :
      0 → taux super-réduit (2,1 % — ex. médicaments, presse)
      1 → taux réduit       (5,5 % — ex. alimentation, livres)
      2 → taux intermédiaire(10 %  — ex. restauration)
      3 → taux normal       (20 %  — taux standard)
    """

    __tablename__ = "vat_rates"
    __table_args__ = (
        UniqueConstraint("code", "date_start", name="uq_vat_rates_code_date_start"),
        {"schema": "app_schema"},
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du taux de TVA",
    )
    code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Code TVA (0=super-réduit, 1=réduit, 2=intermédiaire, 3=normal)",
    )
    rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Taux de TVA en pourcentage (ex: 5.50)",
    )
    label: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Libellé du taux (ex: Taux réduit)",
    )
    date_start: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Date de début de validité du taux",
    )
    date_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date de fin de validité (NULL = taux actuellement en vigueur)",
    )

    # Relations
    general_objects = relationship("GeneralObjects", back_populates="vat_rate")

    def __repr__(self) -> str:
        return (
            f"<VatRate(id={self.id}, code={self.code}, "
            f"rate={self.rate}%, label={self.label!r})>"
        )

    def is_current(self, at: Optional[datetime] = None) -> bool:
        """Retourne True si ce taux est en vigueur à la date donnée (défaut : maintenant)."""
        ref = at or datetime.now(timezone.utc)
        if self.date_start > ref:
            return False
        if self.date_end is not None and self.date_end <= ref:
            return False
        return True
