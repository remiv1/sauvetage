"""Modèle de données pour les envois."""

from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, Integer, DateTime
from db_models import WorkingBase
from db_models.objects import QueryMixin

CASCADE_OPTIONS = "all, delete-orphan"

class Shipment(WorkingBase, QueryMixin):
    """Modèle de données pour un envoi."""

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    carrier: Mapped[str] = mapped_column(String(50), nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(50), nullable=True)

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source de l'envoi")
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date de création de l'envoi")
    update_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source de la dernière mise à jour")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date dernière mise à jour de l'envoi")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True,
                                                            comment="Dernière synchronisation")

    # Relations
    order_lines = relationship("OrderLine", back_populates="shipment")
