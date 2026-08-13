"""Modèles principaux pour les objets généraux et leur historique de prix."""

from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import (
    Integer,
    String,
    Numeric,
    DateTime,
    Date,
    ForeignKey,
    Boolean,
    func,
    and_,
    or_,
    select,
    literal,
)
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.elements import SQLColumnExpression
from db_models import WorkingBase
from db_models.services.utils import slugify
from ..common import QueryMixin
from .object_constants import CASCADE_OPTIONS, GENERAL_OBJECT_PK, DESCRIPTION_FK


class GeneralObjects(WorkingBase, QueryMixin):
    """
    Modèle pour les objets généraux mis en vente.
    
    Attributs :
    - id : Identifiant unique de l'objet (clé primaire)
    - wpwc_id : Identifiant de l'objet dans WooCommerce (nullable, unique)
    - supplier_id : Identifiant du fournisseur de l'objet (clé étrangère vers suppliers.id)
    - general_object_type : Type d'objet (ex: book, other)
    - ean13 : Code EAN13 de l'objet (unique, non nullable)
    - name : Nom de l'objet (non nullable)
    - description : Description de l'objet (nullable)
    - price : Prix de l'objet (non nullable, valeur par défaut = 0.0)
    - purchase_price : Prix d'achat de l'objet (nullable, valeur par défaut = 0.0)
    - vat_rate_id : Code TVA associé à l'objet (nullable, référence la table vat_rates)
    - created_at : Date de création de l'objet
    - updated_at : Date de dernière mise à jour de l'objet
    - last_inventory_timestamp : Dernier inventaire
    - is_active : Indique si l'objet est actif pour la vente
    """

    __tablename__ = "general_objects"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de l'objet",
    )
    wpwc_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant de l'objet dans WooCommerce (si synchronisé)",
    )
    henrri_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant de l'objet chez Henrri (si synchronisé)",
    )

    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.suppliers.id"),
        nullable=False,
        comment="Identifiant du fournisseur de l'objet",
    )
    general_object_type: Mapped[str] = mapped_column(
        String, nullable=False, comment="Type d'objet"
    )
    ean13: Mapped[str] = mapped_column(
        String, unique=True, nullable=False,
        comment="Code EAN13 de l'objet"
    )
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Nom de l'objet")
    description: Mapped[str] = mapped_column(String, comment="Description de l'objet")
    purchase_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=True, default=0.0,
        comment="Prix d'achat de l'objet"
    )
    vat_rate_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app_schema.vat_rates.id"),
        nullable=True,
        comment="Code TVA associé à l'objet (référence la table vat_rates)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'objet",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour de l'objet",
    )
    last_inventory_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Dernier inventaire",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Indique si l'objet est actif pour la vente"
    )

    supplier = relationship("Suppliers", back_populates="objects")
    vat_rate = relationship("VatRate", back_populates="general_objects")
    prices = relationship(
        "ObjectPrices",
        back_populates="general_object",
        cascade=CASCADE_OPTIONS,
        order_by="ObjectPrices.from_date",
    )
    book = relationship(
        "Books",
        uselist=False,
        back_populates="general_object",
        cascade=CASCADE_OPTIONS,
    )
    other_object = relationship(
        "OtherObjects",
        uselist=False,
        back_populates="general_object",
        cascade=CASCADE_OPTIONS,
    )
    inventory_movements = relationship(
        "InventoryMovements", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    obj_metadatas = relationship(
        "ObjMetadatas", back_populates="general_object", cascade=CASCADE_OPTIONS, uselist=False
    )
    object_tags = relationship(
        "ObjectTags", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    media_files = relationship(
        "MediaFiles", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    object_variations = relationship(
        "ObjectVariations", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    order_lines = relationship(
        "OrderLine", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    orderin_lines = relationship(
        "OrderInLine", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    dilicom_referencial = relationship(
        "DilicomReferencial",
        uselist=False,
        back_populates="general_object",
        cascade=CASCADE_OPTIONS,
    )

    def _current_price_row(self) -> Optional["ObjectPrices"]:
        """Retourne la ligne de prix courante ou la plus proche disponible."""
        today = date.today()
        valid_prices = [
            price
            for price in self.prices
            if price.from_date <= today and (price.to_date is None or price.to_date >= today)
        ]
        if valid_prices:
            return max(valid_prices, key=lambda price: (price.from_date, price.id or 0))

        past_prices = [price for price in self.prices if price.from_date <= today]
        if past_prices:
            return max(past_prices, key=lambda price: (price.from_date, price.id or 0))

        future_prices = [price for price in self.prices if price.from_date > today]
        if future_prices:
            return min(future_prices, key=lambda price: (price.from_date, price.id or 0))

        return None

    def get_valid_prices(self, at: date | None = None) -> list["ObjectPrices"]:
        """Retourne les lignes de prix valides à la date donnée."""
        ref_date = at or date.today()
        return [
            price
            for price in self.prices
            if price.from_date <= ref_date
            and (price.to_date is None or price.to_date >= ref_date)
        ]

    def get_price(self) -> Decimal:
        """Retourne le prix courant calculé depuis l'historique."""
        current_price = self._current_price_row()
        if current_price is None:
            return Decimal("0.00")
        return current_price.price or Decimal("0.00")

    def set_price(self, value: float | int | str | Decimal | None) -> None:
        """Met à jour le prix courant en créant une ligne historique si besoin."""
        if value is None:
            return
        decimal_value = Decimal(str(value))
        current_price = self._current_price_row()
        if current_price is None:
            self.prices.append(
                ObjectPrices(price=decimal_value, from_date=date.today(), to_date=None)
            )
            return
        current_price.price = decimal_value

    def __repr__(self) -> str:
        return (
            f"<GeneralObject(id={self.id}, supplier_id={self.supplier_id}, "
            f"general_object_type={self.general_object_type}, ean13={self.ean13}, "
            f"name={self.name}, price={self.get_price()})>"
        )

    def to_dict_for_woo_commerce(self) -> Dict[str, Any]:
        """Convertit l'objet GeneralObject en dictionnaire formaté pour WooCommerce."""
        return {
            "name": self.name,
            "slug": slugify(self.name),
            "type": "simple" if not self.object_variations else "variable",
            "status": "publish" if self.is_active else "draft",
            "description": self.description,
            "short_description": self.description[:50] if self.description else "",
            "sku": self.id,
            "global_unique_id": self.ean13,
            "regular_price": str(self.get_price()),
            "sale_price": str(self.get_price()) if self.get_price() > 0 else None,
            "tax_class": self.vat_rate.label if self.vat_rate else None,
            "manage_stock": True,
            "stock_quantity": 0,
            "stock_status": "onbackorder",
            "backorders": "notify",
        }

    def to_dict_henrri(self) -> Dict[str, Any]:
        """Convertit l'objet GeneralObject en dictionnaire formaté pour Henrri."""
        now_datetime = str(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        return {
            "vat_percent": self.vat_rate.rate,
            "creation_date": now_datetime,
            "description": self.name,
            "id": self.henrri_id,
            "is_a_group": False,
            "is_tax_included": False,
            "item_category_id": 17,
            "reference": self.ean13,
            "selling_price_without_tax": self.get_price(),
            "selling_price_with_tax": self.get_price() * (1 + self.vat_rate.rate / 100),
            "unit_id": 16,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet GeneralObject en dictionnaire."""
        return {
            "id": self.id,
            "supplier_id": self.supplier_id,
            "general_object_type": self.general_object_type,
            "ean13": self.ean13,
            "name": self.name,
            "description": self.description,
            "price": self.get_price(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_inventory_timestamp": (
                self.last_inventory_timestamp.isoformat()
                if self.last_inventory_timestamp
                else None
            ),
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneralObjects":
        """Crée un objet GeneralObject à partir d'un dictionnaire."""
        return cls(**data)


class ObjectPrices(WorkingBase, QueryMixin):
    """
    Modèle pour les prix des objets.
    Attributs :
    - id : Identifiant unique du prix (clé primaire)
    - general_object_id : Identifiant de l'objet général associé
    - price : Prix de l'objet
    - from_date : Date de début de validité du prix
    - to_date : Date de fin de validité du prix
    """

    __tablename__ = "object_prices"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du prix",
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(GENERAL_OBJECT_PK),
        nullable=False,
        comment=DESCRIPTION_FK,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2, asdecimal=True), nullable=False, default=Decimal("0.00"),
        comment="Prix de l'objet"
    )
    vat_rate_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app_schema.vat_rates.id"),
        nullable=True,
        comment="Taux de TVA associé au prix de vente",
    )
    from_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
        comment="Date de début de validité du prix",
    )
    to_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date de fin de validité du prix",
    )

    general_object = relationship("GeneralObjects", back_populates="prices")
    vat_rate = relationship("VatRate", back_populates="object_prices")

    @hybrid_property
    def is_current(self) -> bool:
        """Indique si le prix est actuellement valide."""
        today = date.today()
        if self.to_date is None:
            return today >= self.from_date
        return self.from_date <= today <= self.to_date

    @is_current.expression
    def is_current(cls):  # type: ignore # pylint: disable=E0213
        """Expression SQL pour filtrer les prix actuellement valides."""
        today = func.current_date()  # pylint: disable=E1102 # type: ignore
        return or_(
            and_(cls.to_date.is_(None), cls.from_date <= today),
            and_(
                cls.to_date.isnot(None),
                cls.from_date <= today,
                cls.to_date >= today,
            ),
        )


def _general_object_price_expression(cls) -> SQLColumnExpression[Decimal]:
    """Expression SQL du prix courant pour GeneralObjects."""
    today = func.current_date()  # pylint: disable=E1102 # type: ignore
    current_price = (
        select(ObjectPrices.price)
        .where(
            ObjectPrices.general_object_id == cls.id,
            or_(
                and_(ObjectPrices.to_date.is_(None), ObjectPrices.from_date <= today),
                and_(
                    ObjectPrices.to_date.isnot(None),
                    ObjectPrices.from_date <= today,
                    ObjectPrices.to_date >= today,
                ),
            ),
        )
        .order_by(ObjectPrices.from_date.desc(), ObjectPrices.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    fallback_price = (
        select(ObjectPrices.price)
        .where(
            ObjectPrices.general_object_id == cls.id,
            ObjectPrices.from_date <= today,
        )
        .order_by(ObjectPrices.from_date.desc(), ObjectPrices.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    return func.coalesce(current_price, fallback_price, literal(Decimal("0.00")))


GeneralObjects.price = hybrid_property(
    GeneralObjects.get_price,
    GeneralObjects.set_price,
    expr=_general_object_price_expression,
)
