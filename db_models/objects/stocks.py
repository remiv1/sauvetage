"""Modèle de données pour les stocks."""

from typing import Dict, Any
from decimal import Decimal
from sqlalchemy import Integer, String, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from db_models.objects import QueryMixin

class OrderIn(WorkingBase, QueryMixin):
    """Database model for OrderIn table."""

    __tablename__ = "order_in"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_ref: Mapped[str] = mapped_column(String, nullable=False,
                                           comment="Numéro de commande")
    external_ref: Mapped[int] = mapped_column(Integer, nullable=True,
                                              comment="Ref externe")
    supplier_id: Mapped[int] = mapped_column(Integer,
                                          ForeignKey("app_schema.suppliers.id"),
                                          nullable=False,
                                          comment="ID du fournisseur de la commande")
    value: Mapped[Numeric] = mapped_column(Numeric(10, 2), default=0.00, nullable=False,
                                           comment="Valeur totale de la commande")
    order_state: Mapped[str] = mapped_column(String, default="draft", nullable=False,
                                             comment="État de la commande")

    # Relations
    orderin_lines = relationship("OrderInLine", back_populates="order_in")
    supplier = relationship("Suppliers", back_populates="orderin")

    def __repr__(self) -> str:
        return f"<OrderIn(id={self.id}, external_ref={self.external_ref}, " \
                + f"order_ref={self.order_ref}, supplier_id={self.supplier_id}, " \
                + f"value={self.value}) + order_state={self.order_state}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet OrderIn en dictionnaire."""
        return {
            "id": self.id,
            "order_ref": self.order_ref,
            "external_ref": self.external_ref,
            "supplier_id": self.supplier_id,
            "value": (float(self.value) if isinstance(self.value, (int, float, Decimal)) else None),
            "order_state": self.order_state
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderIn":
        """Crée un objet OrderIn à partir d'un dictionnaire."""
        return cls(**data)

class OrderInLine(WorkingBase, QueryMixin):
    """Database model for OrderInLine table."""

    __tablename__ = "order_in_lines"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_in_id: Mapped[int] = mapped_column(Integer,
                                             ForeignKey("app_schema.order_in.id"),
                                             nullable=False,
                                             comment="ID de la commande d'entrée")
    general_object_id: Mapped[int] = mapped_column(Integer,
                                                   ForeignKey("app_schema.general_objects.id"),
                                                   nullable=False,
                                                   comment="ID de l'objet")
    inventory_movement_id: Mapped[int] = mapped_column(Integer,
                                                    ForeignKey("app_schema.inventory_movements.id"),
                                                    nullable=True,
                                                    comment="ID du mouvement de stock associé")
    qty_ordered: Mapped[int] = mapped_column(Integer,
                                             nullable=False,
                                             comment="Quantité commandée")
    qty_received: Mapped[int] = mapped_column(Integer,
                                              default=0,
                                              nullable=False,
                                              comment="Quantité reçue")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2, True, True), nullable=False,
                                                comment="Prix unitaire en centimes d'euro")
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(10, 3, True, True), nullable=False,
                                                comment="Taux de TVA en pourcentage")
    line_state: Mapped[str] = mapped_column(String, default="pending", nullable=False,
                                            comment="État de la ligne de commande")

    # Relations
    order_in = relationship("OrderIn", back_populates="orderin_lines")
    general_object = relationship("GeneralObjects", back_populates="orderin_lines")
    inventory_movement = relationship("InventoryMovements", back_populates="orderin_line")

    def __repr__(self) -> str:
        return f"<OrderInLine(id={self.id}, order_in_id={self.order_in_id}, " \
                + f"general_object_id={self.general_object_id}, qty_ordered={self.qty_ordered}, " \
                + f"qty_received={self.qty_received}, unit_price={self.unit_price}, " \
                + f"vat_rate={self.vat_rate}, line_state={self.line_state})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet OrderInLine en dictionnaire."""
        return {
            "id": self.id,
            "order_in_id": self.order_in_id,
            "general_object_id": self.general_object_id,
            "qty_ordered": self.qty_ordered,
            "qty_received": self.qty_received,
            "unit_price": (float(self.unit_price)
                           if isinstance(self.unit_price, (int, float, Decimal))
                           else None),
            "vat_rate": (float(self.vat_rate)
                         if isinstance(self.vat_rate, (int, float, Decimal))
                         else None),
            "line_state": self.line_state
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderInLine":
        """Crée un objet OrderInLine à partir d'un dictionnaire."""
        return cls(**data)

class DilicomReferencial(WorkingBase, QueryMixin):
    """Database model for Dilicom Referential table."""

    __tablename__ = "dilicom_referential"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isbn: Mapped[str] = mapped_column(String,
                                      nullable=False,
                                      comment="ISBN de l'objet")
    gln13: Mapped[str] = mapped_column(String,
                                       ForeignKey("app_schema.suppliers.gln13"),
                                       nullable=False,
                                       comment="GLN13 du fournisseur")
    create_ref: Mapped[bool] = mapped_column(Boolean, default=False,
                                             comment="Indique si l'objet doit être créé")
    delete_ref: Mapped[bool] = mapped_column(Boolean, default=False,
                                             comment="Indique si l'objet doit être supprimé")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True,
                                            comment="Indique si la référence est active")

    # Métadonnées de suivi
    created_at: Mapped[str] = mapped_column(String, nullable=False,
                                            comment="Date de création de la référence")
    updated_at: Mapped[str] = mapped_column(String, nullable=False,
                                            comment="Date de dernière MàJ de la référence")

    def __repr__(self) -> str:
        return f"<DilicomReferencial(id={self.id}, isbn={self.isbn}, gln13={self.gln13}, " \
               f"create_ref={self.create_ref}, delete_ref={self.delete_ref}, " \
               f"is_active={self.is_active})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet DilicomReferencial en dictionnaire."""
        return {
            "id": self.id,
            "isbn": self.isbn,
            "gln13": self.gln13,
            "create_ref": self.create_ref,
            "delete_ref": self.delete_ref,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def to_pipe(self) -> str:
        """Création du pipe de commandes pour Dilicom."""
        direction = "c" if self.create_ref else "d"
        return f"{direction}|{self.isbn}|{self.gln13}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DilicomReferencial":
        """Crée un objet DilicomReferencial à partir d'un dictionnaire."""
        return cls(**data)
