"""Module des modèles de données pour les commandes."""

from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, Numeric, event
from db_models import WorkingBase
from db_models.objects import QueryMixin

class Order(WorkingBase, QueryMixin):
    """Modèle de données pour une commande."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    invoice_address_id: Mapped[int] = mapped_column(Integer, ForeignKey("customer_addresses.id"),
                                                    nullable=False, comment="Adresse de facturat°")
    delivery_address_id: Mapped[int] = mapped_column(Integer, ForeignKey("customer_addresses.id"),
                                                     nullable=False, comment="Adresse de livraison")
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source de la commande")
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date de création de la commande")
    update_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source de la dernière mise à jour")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date dernière mise à jour de la commande")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True,
                                                            comment="Dernière synchronisation")

    # Relations
    customer = relationship("Customers", back_populates="orders")
    invoice_address = relationship("CustomerAddresses", foreign_keys=[invoice_address_id])
    delivery_address = relationship("CustomerAddresses", foreign_keys=[delivery_address_id])
    order_lines = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="order")

class OrderLine(WorkingBase, QueryMixin):
    """Modèle de données pour une ligne de commande."""

    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique de la ligne de commande")
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("invoices.id"), nullable=True,
                                            comment="Facture associée à la ligne de commande")
    shipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("shipments.id"), nullable=True,
                                             comment="Envoi associé à la ligne de commande")
    general_object_id: Mapped[int] = mapped_column(Integer, ForeignKey("general_objects.id"),
                                                   nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False,
                                          comment="Quantité commandée")
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False,
                                            comment="Prix unitaire en centimes d'euro")
    vat_rate: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False,
                                          comment="Taux de TVA en pourcentage")

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source de la ligne de commande")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création de la ligne de commande")
    update_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source last MaJ de la ligne de commande")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date last MaJ de la ligne de commande")

    # Relations
    order = relationship("Order", back_populates="order_lines")
    general_object = relationship("GeneralObjects", back_populates="order_lines")
    invoice = relationship("Invoice", back_populates="order_lines")
    shipment = relationship("Shipment", back_populates="order_lines")


@event.listens_for(OrderLine, "before_delete")
def _prevent_invoiced_order_line_delete(_mapper: Any, _connection: Any, # type: ignore
                                        target: "OrderLine") -> None:
    if target.invoice_id is not None:   # type: ignore
        raise ValueError("Une suppression de ligne facturee est interdite.")
