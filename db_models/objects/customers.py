"""Database model for Customers table."""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Text, Boolean, ForeignKey
from db_models import WorkingBase
from db_models.objects import QueryMixin

CUSTOMER_PK = "app_schema.customers.id"
_CASCADE_ALL = "all, delete-orphan"

class Customers(WorkingBase, QueryMixin):
    """
    Modèle de base de données pour la table client.

    Cette base de données est source unique de vérité.
    Synchronisé avec deux systèmes externes :
    - WordPress/WooCommerce (e-commerce)
    - Henrri (Facturation/Comptabilité)

    Attributs :
    - id (int) : Identifiant unique du client.
    - wpwc_id (str | None) : Identifiant du client dans WooCommerce.
    - henrri_id (str | None) : Identifiant du client dans Henrri.
    - customer_type (str) : Type de client ("part" ou "pro").
    - is_active (bool) : Indique si le client est actif ou inactif.
    - created_at (datetime) : Date de création du client.
    - updated_at (datetime) : Date de la dernière mise à jour du client.
    - last_synced_at (datetime | None) : Date de dernière synchronisation avec un système externe.
    Relations :
    - part : Relation vers les données spécifiques aux clients particuliers.
    - pro : Relation vers les données spécifiques aux clients professionnels.
    - addresses : Relation vers les adresses associées au client.
    - emails : Relation vers les emails associés au client.
    - phones : Relation vers les téléphones associés au client.
    - sync_logs : Relation vers les logs de synchronisation du client.
    - orders : Relation vers les commandes associées au client.
    """

    __tablename__ = "customers"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du client",
    )

    # Identifiants des systèmes externes
    wpwc_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, comment="Identifiant WooCommerce"
    )
    henrri_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, comment="Identifiant Henrri"
    )

    # Données client
    customer_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="part", comment="Type de client : part/pro"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Statut actif/inactif du client"
    )

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de création du client",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de dernière mise à jour du client",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Dernière synchronisation"
    )

    # Relations avec d'autres tables
    part = relationship(
        "CustomerParts",
        back_populates="customer",
        uselist=False,
        cascade=_CASCADE_ALL,
        )
    pro = relationship(
        "CustomerPros",
        back_populates="customer",
        uselist=False,
        cascade=_CASCADE_ALL,
        )
    addresses = relationship(
        "CustomerAddresses",
        back_populates="customer",
        uselist=True,
        cascade=_CASCADE_ALL
    )
    emails = relationship(
        "CustomerMails",
        back_populates="customer",
        uselist=True,
        cascade=_CASCADE_ALL
    )
    phones = relationship(
        "CustomerPhones",
        back_populates="customer",
        uselist=True,
        cascade=_CASCADE_ALL
    )
    sync_logs = relationship(
        "CustomerSyncLog",
        back_populates="customer",
        uselist=True,
        cascade=_CASCADE_ALL
    )
    orders = relationship(
        "Order",
        back_populates="customer",
        uselist=True,
        cascade=_CASCADE_ALL
    )

    def __repr__(self) -> str:
        """
        Représentation en chaîne de l'objet Customer.
        """
        return f"<Customer(id={self.id}, type={self.customer_type}, active={self.is_active})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet Customer en dictionnaire."""
        return {
            "id": self.id,
            "wpwc_id": self.wpwc_id,
            "henrri_id": self.henrri_id,
            "customer_type": self.customer_type,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_synced_at": (
                self.last_synced_at.isoformat() if self.last_synced_at else None
            ),
            "part": self.part.to_dict() if self.part else None,
            "pro": self.pro.to_dict() if self.pro else None,
            "addresses": (
                [addr.to_dict() for addr in self.addresses] if self.addresses else None
            ),
            "emails": (
                [email.to_dict() for email in self.emails] if self.emails else None
            ),
            "phones": (
                [phone.to_dict() for phone in self.phones] if self.phones else None
            ),
            "sync_logs": (
                [log.to_dict() for log in self.sync_logs] if self.sync_logs else None
            ),
        }

    def _get_names(self) -> tuple[str | None, str | None]:
        first_name = self.part.first_name if self.part else None
        last_name = self.part.last_name if self.part else None
        return first_name, last_name

    def get_wpwc_mail(self) -> Optional[str]:
        """
        Récupère l'email du client à utiliser pour WooCommerce.
        Priorise les emails avec "WooCommerce" dans le nom, puis les emails actifs.
        """
        return next((
            e.email for e in self.emails if "WooCommerce" in e.email_name),
            next((e.email for e in self.emails if e.is_active), None))

    def get_wpwc_phone(self) -> Optional[str]:
        """
        Récupère le téléphone du client à utiliser pour WooCommerce.
        Priorise les téléphones avec "WooCommerce" dans le nom, puis les téléphones actifs.
        """
        return next((
            p.phone_number for p in self.phones if "WooCommerce" in p.phone_name),
            next((p.phone_number for p in self.phones if p.is_active), None))

    def get_wpwc_billing_address(self) -> Optional[CustomerAddresses]:
        """
        Récupère l'adresse de facturation du client à utiliser pour WooCommerce.
        Priorise les adresses de facturation avec "WooCommerce" dans le nom,
        puis les adresses de facturation actives.
        """
        return next((
            a for a in self.addresses if a.is_billing and "WooCommerce" in a.address_name),
            next((a for a in self.addresses if a.is_billing and a.is_active), None))

    def get_wpwc_shipping_address(self) -> Optional[CustomerAddresses]:
        """
        Récupère l'adresse de livraison du client à utiliser pour WooCommerce.
        Priorise les adresses de livraison avec "WooCommerce" dans le nom,
        puis les adresses de livraison actives.
        """
        return next((
            a for a in self.addresses if a.is_shipping and "WooCommerce" in a.address_name),
            next((a for a in self.addresses if a.is_shipping and a.is_active), None))

    def _wpwc_dispatch_addresses(self) -> tuple[dict[str, Any], dict[str, Any]]:
        first_name, last_name = self._get_names()
        billing_address = self.get_wpwc_billing_address()
        shipping_address = self.get_wpwc_shipping_address()
        email = self.get_wpwc_mail()
        if not email:
            raise ValueError(f"Aucun email actif trouvé pour le client {self.id}")
        phone = self.get_wpwc_phone()
        billing = {
            'first_name': first_name,
            'last_name': last_name,
            'address_1': billing_address.address_line1 if billing_address else None,
            'address_2': billing_address.address_line2 if billing_address else None,
            'city': billing_address.city if billing_address else None,
            'state': billing_address.state if billing_address else None,
            'postcode': billing_address.postal_code if billing_address else None,
            'country': billing_address.country if billing_address else None,
            'email': email,
            'phone': phone,
        }
        shipping = {
            'first_name': first_name,
            'last_name': last_name,
            'address_1': shipping_address.address_line1 if shipping_address else None,
            'address_2': shipping_address.address_line2 if shipping_address else None,
            'city': shipping_address.city if shipping_address else None,
            'state': shipping_address.state if shipping_address else None,
            'postcode': shipping_address.postal_code if shipping_address else None,
            'country': shipping_address.country if shipping_address else None,
        }
        return billing, shipping

    def to_dict_for_wpwc(self, update: bool = False) -> dict[str, Any]:
        """
        Convertit les données du client en un format structuré pour WooCommerce.
        """
        first_name, last_name = self._get_names()
        billing, shipping = self._wpwc_dispatch_addresses()
        meta_data = []
        if self.customer_type == "pro":
            meta_data.append({'key': 'billing_wooccm10', 'value': 'Professionnel'})
            meta_data.append({'key': 'billing_wooccm11', 'value': self.pro.company_name})
            meta_data.append({'key': 'billing_wooccm12', 'value': self.pro.siret_number})
            username = self.pro.company_name
        else:
            meta_data.append({'key': 'billing_wooccm10', 'value': 'Particulier'})
            username = f"{self.part.first_name} {self.part.last_name}"
        final_dict =  {
            "email": billing["email"],
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "billing": billing,
            "shipping": shipping,
            "meta_data": meta_data,
        }
        if update:
            # Ne pas envoyer les champs vides pour éviter d'écraser
            final_dict = {k: v for k, v in final_dict.items() if v}
            final_dict["date_modified_gmt"] = self.sync_logs[-1].created_at.isoformat() \
                if self.sync_logs else None
        return final_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Customers':
        """
        Crée un objets Customer à partir d'un dictionnaire pur.
        Args:
            data (Dict[str, Any]): Dictionnaire contenant les données du client.
        Returns:
            Customers: L'objet Customers créé à partir du dictionnaire.
        """
        return cls(**data)


class CustomerParts(WorkingBase, QueryMixin):
    """
    Database model for Customer Parts table.
    Attributs :
    - id (int) : Identifiant unique de la partie client.
    - customer_id (int) : Identifiant du client associé.
    - civil_title (str | None) : Civilité (ex: M., Mme, Dr).
    - first_name (str) : Prénom du client.
    - last_name (str) : Nom du client.
    - date_of_birth (datetime | None) : Date de naissance du client.
    """

    __tablename__ = "customer_parts"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Identifiant Part unique"
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        unique=True,
        comment="Id client associé à part",
    )

    # Données personnelles
    civil_title: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Civilité (ex: M., Mme, Dr)"
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relations
    customer = relationship("Customers", back_populates="part", uselist=False)

    def __repr__(self) -> str:
        """Représentation en chaîne de l'objet CustomerPart."""
        return (
            f"<CustomerPart(id={self.id}, customer_id={self.customer_id}, "
            + f"first_name={self.first_name}, last_name={self.last_name})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPart en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "civil_title": self.civil_title,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerParts":
        """Crée un objet CustomerPart à partir d'un dictionnaire."""
        date_of_birth = data.get("date_of_birth")
        return cls(
            customer_id=data.get("customer_id", 0),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            date_of_birth=(
                datetime.fromisoformat(date_of_birth) if date_of_birth else None
            ),
        )


class CustomerPros(WorkingBase, QueryMixin):
    """Database model for Customer Pros table."""

    __tablename__ = "customer_pros"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Identifiant unique"
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        unique=True,
        comment="Identifiant du client associé",
    )

    # Données professionnelles
    company_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Nom de l'entreprise"
    )
    siret_number: Mapped[str | None] = mapped_column(
        String(14), nullable=False, unique=True, comment="Numéro SIRET de l'entreprise"
    )
    vat_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        comment="Numéro de TVA intracommunautaire",
    )

    # Relations
    customer = relationship("Customers", back_populates="pro", uselist=False)

    def __repr__(self) -> str:
        """Représentation en chaîne de l'objet CustomerPro."""
        return (
            f"<CustomerPro(id={self.id}, customer_id={self.customer_id}, "
            + f"company_name={self.company_name})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPro en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "company_name": self.company_name,
            "siret_number": self.siret_number,
            "vat_number": self.vat_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerPros":
        """Crée un objet CustomerPro à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            company_name=data.get("company_name", ""),
            siret_number=data.get("siret_number"),
            vat_number=data.get("vat_number"),
        )


class CustomerAddresses(WorkingBase, QueryMixin):
    """Database model for Customer Addresses table."""

    __tablename__ = "customer_addresses"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Identifiant unique"
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        comment="Identifiant du client associé",
    )

    # Données d'adresse
    address_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Nom d'adresse (ex: home, work)"
    )
    address_line1: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Ligne d'adresse 1"
    )
    address_line2: Mapped[str] = mapped_column(
        String(200), nullable=True, comment="Ligne d'adresse 2"
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False, comment="Ville")
    state: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="État/Région"
    )
    postal_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Code postal"
    )
    country: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Pays", default="France"
    )

    # Données de facturation/livraison
    is_billing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si c'est une adresse de facturation",
    )
    is_shipping: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Indique si c'est une adresse de livraison",
    )

    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si l'adresse est active ou supprimée",
    )

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'adresse",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour",
    )

    customer = relationship("Customers", back_populates="addresses")

    def __repr__(self) -> str:
        return (
            f"<CustomerAddress(id={self.id}, customer_id={self.customer_id}, "
            + f"address_name={self.address_name}, "
            + f"address_line1={self.address_line1}, address_line2={self.address_line2}, "
            + f"city={self.city}, country={self.country})>"
        )

    def __hash__(self) -> int:
        return hash((
            self.customer_id,
            self.address_name,
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CustomerAddresses):
            return False
        return (
            self.customer_id == other.customer_id
            and self.address_name == other.address_name
            and self.address_line1 == other.address_line1
            and self.address_line2 == other.address_line2
            and self.city == other.city
            and self.state == other.state
            and self.postal_code == other.postal_code
            and self.country == other.country
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerAddress en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "address_name": self.address_name,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "is_active": self.is_active,
            "is_billing": self.is_billing,
            "is_shipping": self.is_shipping,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerAddresses":
        """Crée un objet CustomerAddress à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            address_name=data.get("address_name"),
            address_line1=data.get("address_line1", ""),
            address_line2=data.get("address_line2", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", ""),
            is_billing=data.get("is_billing", True),
            is_shipping=data.get("is_shipping", False),
        )


class CustomerMails(WorkingBase, QueryMixin):
    """Database model for Customer Mails table."""

    __tablename__ = "customer_mails"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant email unique",
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        comment="Id client associé à cet email",
    )

    # Données d'e-mail
    email_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Nom de l'e-mail (ex: perso, pro)"
    )
    email: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, comment="Adresse e-mail du client"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si l'e-mail est actif ou supprimé",
    )

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'e-mail",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour de l'e-mail",
    )

    # Relations
    customer = relationship("Customers", back_populates="emails")

    def __repr__(self) -> str:
        return f"<CustomerMail(id={self.id}, customer_id={self.customer_id}, email={self.email})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerMail en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "email_name": self.email_name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerMails":
        """Crée un objet CustomerMail à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            email_name=data.get("email_name"),
            email=data.get("email", ""),
            is_active=data.get("is_active", True),
        )


class CustomerPhones(WorkingBase, QueryMixin):
    """Database model for Customer Phones table."""

    __tablename__ = "customer_phones"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant téléphone unique",
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        comment="Id client associé à ce téléphone",
    )

    # Données de téléphone
    phone_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Nom du téléphone (ex: mobile, fixe)"
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="Numéro de téléphone du client"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si le téléphone est actif ou supprimé",
    )

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du téléphone",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ du téléphone",
    )

    # Relations
    customer = relationship("Customers", back_populates="phones")

    def __repr__(self) -> str:
        return (
            f"<CustomerPhone(id={self.id}, customer_id={self.customer_id}, "
            + f"phone_name={self.phone_name}, phone_number={self.phone_number})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPhone en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "phone_name": self.phone_name,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerPhones":
        """Crée un objet CustomerPhone à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            phone_name=data.get("phone_name"),
            phone_number=data.get("phone_number", ""),
            is_active=data.get("is_active", True),
        )


class CustomerSyncLog(WorkingBase):
    """Database model for Customer Synchronization Log.

    Tracks all synchronization events between the main database and external systems
    (WordPress/WooCommerce, Henrri).
    """

    __tablename__ = "customer_sync_logs"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(CUSTOMER_PK), nullable=False
    )

    # Synchronization details
    sync_direction: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Direction : inbound, outbound"
    )
    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Statut : success, failed, pending"
    )
    operation: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Opération : create, update, delete"
    )

    # External system info
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_system: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Système externe : wpwc, henrri, …"
    )

    # Sync details
    fields_synced: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of sync
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    customer = relationship("Customers", back_populates="sync_logs")

    def __repr__(self) -> str:
        return (
            f"<CustomerSyncLog(id={self.id}, customer_id={self.customer_id}, "
            + f"external_system={self.external_system}, operation={self.operation}, "
            + f"sync_status={self.sync_status})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerSyncLog en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "external_system": self.external_system,
            "sync_direction": self.sync_direction,
            "operation": self.operation,
            "sync_status": self.sync_status,
            "external_id": self.external_id,
            "fields_synced": self.fields_synced,
            "error_message": self.error_message,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerSyncLog":
        """Crée un objet CustomerSyncLog à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            external_system=data.get("external_system", ""),
            sync_direction=data.get("sync_direction", "inbound"),
            operation=data.get("operation", "create"),
            sync_status=data.get("sync_status", "pending"),
            external_id=data.get("external_id"),
            fields_synced=data.get("fields_synced"),
            error_message=data.get("error_message"),
        )
