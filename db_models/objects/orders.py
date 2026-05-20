"""Module des modèles de données pour les commandes."""

from typing import Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, Numeric, Text, event
from db_models import WorkingBase
from db_models.objects import QueryMixin, Customers  # pylint: disable=unused-import


_ALL_DELETE_ORPHAN = "all, delete-orphan"


class Order(WorkingBase, QueryMixin):
    """
    Modèle de données pour une commande.
    
    Attr :
    - id (int) : Identifiant unique de la commande.
    - wpwc_id (int | None) : ID de la commande dans WooCommerce, null si non synchronisée.
    - reference (str) :
        Référence de la commande, format "CMD-<YYMM>-00001" ou "RET-<YYMM>-00001".
    - customer_id (int) : ID du client associé à la commande.
    - invoice_address_id (int | None) : ID de l'adresse de facturation.
    - delivery_address_id (int | None) : ID de l'adresse de livraison.
    - status (str) :
        Statut de la commande (draft, partial_invoiced, invoiced, partial_shipped,
        shipped, canceled, returned).
    - create_source (str) : Source de création de la commande.
    - created_at (datetime) : Date de création de la commande.
    - update_source (str | None) : Source de la dernière mise à jour de la commande.
    - updated_at (datetime) : Date de la dernière mise à jour de la commande.
    - last_synced_at (datetime | None) :
        Date de la dernière synchronisation avec un système externe.
    Relations :
    - customer : Relation vers le client associé à la commande.
    - invoice_address : Relation vers l'adresse de facturation.
    - delivery_address : Relation vers l'adresse de livraison.
    - order_lines : Relation vers les lignes de commande associées.
    - invoices : Relation vers les factures associées à la commande.
    - shipments : Relation vers les expéditions associées à la commande.
    - sync_logs : Relation vers les logs de synchronisation de la commande.
    """

    __tablename__ = "orders"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wpwc_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, unique=True, comment="ID de la commande dans WooCommerce"
    )
    # Format de référence :
    # - "CMD-<YYMM>-00001" pour les commandes
    # - "RET-<YYMM>-00001" pour les retours
    reference: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_schema.customers.id"), nullable=False
    )
    invoice_address_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("app_schema.customer_addresses.id"),
        nullable=True,
        comment="Adresse de facturation",
    )
    delivery_address_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("app_schema.customer_addresses.id"),
        nullable=True,
        comment="Adresse de livraison",
    )
    # Sept états principaux : "draft", "partial_invoiced", "invoiced", "partial_shipped", "shipped",
    # "canceled", "returned". "canceled" (CMD) et "returned" (RET) sont des états finaux,
    # les autres sont des états de travail
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Source de la commande"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de création de la commande",
    )
    update_source: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Source de la dernière mise à jour"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date dernière mise à jour de la commande",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Dernière synchronisation"
    )

    # Relations
    customer = relationship("Customers", back_populates="orders")
    invoice_address = relationship(
        "CustomerAddresses", foreign_keys=[invoice_address_id]
    )
    delivery_address = relationship(
        "CustomerAddresses", foreign_keys=[delivery_address_id]
    )
    order_lines = relationship(
        "OrderLine", back_populates="order", cascade=_ALL_DELETE_ORPHAN
    )
    invoices = relationship(
        "Invoice", back_populates="order", cascade=_ALL_DELETE_ORPHAN
    )
    shipments = relationship(
        "Shipment", back_populates="order", cascade=_ALL_DELETE_ORPHAN
    )
    sync_logs = relationship("OrderSyncLog", back_populates="order", uselist=True)

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, reference={self.reference}, status={self.status})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet Order en dictionnaire."""
        return {
            "id": self.id,
            "reference": self.reference,
            "customer_id": self.customer_id,
            "invoice_address_id": self.invoice_address_id,
            "delivery_address_id": self.delivery_address_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def _get_wc_metadata(self) -> dict[str, Any]:
        """Récupère les métadonnées spécifiques à WooCommerce pour la commande."""
        customer_type = 'Particulier' if self.customer.customer_type == 'part' else 'Professionnel'
        rs = self.customer.pro.company_name if self.customer.pro else ''
        siret = self.customer.pro.siret if self.customer.pro else ''
        return {
            '_billing_wooccm10': customer_type,
            '_billing_wooccm11': rs,
            '_billing_wooccm12': siret,
        }

    def __get_customer_name_parts(self) -> tuple[str, str]:
        """Récupère les parties prénom et nom du client pour la commande."""
        if self.customer.customer_type == 'part' and self.customer.part:
            return self.customer.part.first_name, self.customer.part.last_name
        elif self.customer.customer_type == 'pro' and self.customer.pro:
            return '', self.customer.pro.company_name
        else:
            return '', ''

    def __get_customer_email(self) -> str:
        """
        Récupère l'email du client pour la commande, en privilégiant l'email marqué "WooCommerce".
        """
        if not self.customer.emails:
            raise ValueError("Le client doit avoir au moins une adresse email pour un compte.")
        wc_email = next(
            (e.email for e in self.customer.emails if "WooCommerce" in e.email_name),
            None
        )
        if wc_email:
            return wc_email
        return self.customer.emails[0].email

    def __get_customer_phone(self) -> Optional[str]:
        """
        Récupère le numéro de téléphone du client pour la commande, en privilégiant le téléphone
        marqué "WooCommerce".
        """
        if not self.customer.phones:
            return None
        wc_phone = next(
            (p.phone_number for p in self.customer.phones if "WooCommerce" in p.phone_name),
            None
        )
        if wc_phone:
            return wc_phone
        return self.customer.phones[0].phone_number if self.customer.phones else None

    def to_dict_for_woo_commerce(self) -> dict[str, Any]:
        """Convertit l'objet Order en dictionnaire au format attendu par WooCommerce."""
        first_name, last_name = self.__get_customer_name_parts()
        email = self.__get_customer_email()
        phone = self.__get_customer_phone()
        billing = {
            "first_name": first_name,
            "last_name": last_name,
            "address_1": self.invoice_address.address_line1 if self.invoice_address else "",
            "address_2": self.invoice_address.address_line2 if self.invoice_address else "",
            "city": self.invoice_address.city if self.invoice_address else "",
            "state": self.invoice_address.state if self.invoice_address else "",
            "postcode": self.invoice_address.postal_code if self.invoice_address else "",
            "country": self.invoice_address.country if self.invoice_address else "",
            "email": email,
            "phone": phone,
        }
        shipping = {
            "first_name": first_name,
            "last_name": last_name,
            "address_1": self.delivery_address.address_line1 if self.delivery_address else "",
            "address_2": self.delivery_address.address_line2 if self.delivery_address else "",
            "city": self.delivery_address.city if self.delivery_address else "",
            "state": self.delivery_address.state if self.delivery_address else "",
            "postcode": self.delivery_address.postal_code if self.delivery_address else "",
            "country": self.delivery_address.country if self.delivery_address else "",
        }
        metadata = self._get_wc_metadata()
        line_items = []
        for line in self.order_lines:
            if not line:
                continue
            if line.status == "canceled":
                # Ligne annulée localement : demander à WooCommerce de la supprimer
                if line.wpwc_id:
                    line_items.append({"id": line.wpwc_id, "quantity": 0})
            else:
                line_items.append(line.to_dict_for_woo_commerce())
        return {
            "customer_id": self.customer.wpwc_id,
            "payment_method": "bacs",
            "payment_method_title": "Direct Bank Transfer",
            "set_paid": False,
            "billing": billing,
            "shipping": shipping,
            "line_items": line_items,
            "metadata": metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Order":
        """Crée un objet Order à partir d'un dictionnaire."""
        return cls(
            reference=data.get("reference", ""),
            wpwc_id=data.get("wpwc_id"),
            customer_id=data.get("customer_id"),
            invoice_address_id=data.get("invoice_address_id"),
            delivery_address_id=data.get("delivery_address_id"),
            status=data.get("status", ""),
        )


class OrderLine(WorkingBase, QueryMixin):
    """
    Modèle de données pour une ligne de commande.
    Attr :
    - id (int) : Identifiant unique de la ligne de commande.
    - wpwc_id (int | None) : ID de la ligne de commande dans WooCommerce, null si non synchronisée.
    - order_id (int) : ID de la commande associée.
    - general_object_id (int) : ID de l'objet général associé à la ligne de commande.
    - quantity (int) : Quantité commandée.
    - status (str) : Statut de la ligne de commande (draft, invoiced, shipped, canceled, returned).
    - unit_price (float) : Prix unitaire HT en euros.
    - discount (float) : Remise en pourcentage.
    - vat_rate (float) : Taux de TVA en pourcentage.
    - create_source (str) : Source de la ligne de commande.
    - created_at (datetime) : Date de création de la ligne de commande.
    - update_source (str | None) : Source last MaJ de la ligne de commande.
    - updated_at (datetime) : Date last MaJ de la ligne de commande.
    Relations :
    - order : Relation vers la commande associée à la ligne de commande.
    - general_object : Relation vers l'objet général associé à la ligne de commande.
    - invoice_lines : Relation vers les lignes de facture associées à la ligne de commande.
    - shipment_lines : Relation vers les lignes d'expédition associées à la ligne de commande.
    """

    __tablename__ = "order_lines"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de la ligne de commande",
    )
    wpwc_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="ID de la ligne de commande dans WooCommerce",
    )
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_schema.orders.id"), nullable=False
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_schema.general_objects.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Quantité commandée"
    )
    # Sept états : draft, invoiced, shipped, canceled, returned
    # partial_invoiced et partial_shipped sont calculés au niveau de la commande
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", comment="État de la ligne"
    )
    unit_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Prix unitaire HT en euros"
    )
    discount: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, comment="Remise en pourcentage"
    )
    vat_rate: Mapped[float] = mapped_column(
        Numeric(10, 3), nullable=False, comment="Taux de TVA en pourcentage"
    )

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Source de la ligne de commande"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de la ligne de commande",
    )
    update_source: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Source last MaJ de la ligne de commande"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date last MaJ de la ligne de commande",
    )

    object_variation_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app_schema.object_variations.id"),
        nullable=True,
        comment="Variation de produit sélectionnée pour cette ligne",
    )

    # Relations
    order = relationship("Order", back_populates="order_lines")
    general_object = relationship("GeneralObjects", back_populates="order_lines")
    object_variation = relationship("ObjectVariations")
    invoice_lines = relationship("InvoiceLine", back_populates="order_line")
    shipment_lines = relationship("ShipmentLine", back_populates="order_line")

    def __repr__(self) -> str:
        return (
            f"<OrderLine(id={self.id}, order_id={self.order_id}, "
            f"general_object_id={self.general_object_id}, quantity={self.quantity}, "
            f"unit_price={self.unit_price}, vat_rate={self.vat_rate})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet OrderLine en dictionnaire."""
        return {
            "id": self.id,
            "wpwc_id": self.wpwc_id,
            "order_id": self.order_id,
            "general_object_id": self.general_object_id,
            "object_variation_id": self.object_variation_id,
            "quantity": self.quantity,
            "status": self.status,
            "unit_price": self.unit_price,
            "discount": self.discount,
            "vat_rate": self.vat_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_for_woo_commerce(self) -> dict[str, Any]:
        """Convertit l'objet OrderLine en dictionnaire au format attendu par WooCommerce."""
        vat_rate_obj = self.general_object.vat_rate if self.general_object else None
        subtotal_ht = round(float(self.unit_price) * self.quantity, 4)
        discount_ratio = 1 - float(self.discount) / 100
        total_ht = round(subtotal_ht * discount_ratio, 4)

        value_dict: dict[str, Any] = {
            "name": self.general_object.name if self.general_object else "Unknown Product",
            "product_id": int(self.general_object.id_wpwc),
            "quantity": self.quantity,
            "subtotal": str(subtotal_ht),
            "total": str(total_ht),
        }

        # Classe de taxe WooCommerce : WC recalcule les montants de taxe automatiquement
        if vat_rate_obj and vat_rate_obj.wpwc_slug:
            value_dict["tax_class"] = vat_rate_obj.wpwc_slug

        # Inclure l'ID WooCommerce de la ligne pour que le PUT mette à jour au lieu de dupliquer
        if self.wpwc_id:
            value_dict["id"] = self.wpwc_id
        if self.object_variation and self.object_variation.id_wpwc:
            value_dict["variation_id"] = int(self.object_variation.id_wpwc)
        return value_dict

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrderLine":
        """Crée un objet OrderLine à partir d'un dictionnaire."""
        return cls(
            order_id=data.get("order_id"),
            general_object_id=data.get("general_object_id"),
            quantity=data.get("quantity", 0),
            status=data.get("status", "draft"),
            unit_price=data.get("unit_price", 0.0),
            discount=data.get("discount", 0.0),
            vat_rate=data.get("vat_rate", 0.0),
        )


@event.listens_for(OrderLine, "before_delete")
def _prevent_non_draft_order_line_delete(
    _mapper: Any, _connection: Any, target: "OrderLine"  # type: ignore
) -> None:
    if target.status != "draft":
        raise ValueError("Seules les lignes en brouillon peuvent être supprimées.")


class OrderSyncLog(WorkingBase):
    """Journal de synchronisation WooCommerce pour les commandes."""

    __tablename__ = "order_sync_logs"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.orders.id"),
        nullable=False,
        comment="Commande associée",
    )

    # Système externe et direction
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="ID de la commande dans le système externe",
    )
    external_system: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Système externe : wpwc, …",
    )
    sync_direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Direction : inbound, outbound",
    )
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Opération : create, update, delete",
    )

    # Résultat
    sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Statut : success, failed, pending",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Message d'erreur en cas d'échec",
    )

    # Horodatage
    synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date et heure de la synchronisation",
    )

    order = relationship("Order", back_populates="sync_logs")

    def __repr__(self) -> str:
        return (
            f"<OrderSyncLog(id={self.id}, order_id={self.order_id}, "
            f"external_system={self.external_system}, operation={self.operation}, "
            f"sync_status={self.sync_status})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet OrderSyncLog en dictionnaire."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "external_id": self.external_id,
            "external_system": self.external_system,
            "sync_direction": self.sync_direction,
            "operation": self.operation,
            "sync_status": self.sync_status,
            "error_message": self.error_message,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
