"""Database model for Customers table."""

from typing import Any, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Text, Boolean, ForeignKey
from db_models import WorkingBase
from db_models.objects import QueryMixin

CUSTOMER_PK = "app_schema.customers.id"

class Customers(WorkingBase, QueryMixin):
    """Modèle de base de données pour la table client.
    
    Cette base de données est source unique de vérité.
    Synchronisé avec deux systèmes externes :
    - WordPress/WooCommerce (e-commerce)
    - Henrri (Facturation/Comptabilité)
    """

    __tablename__ = "customers"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique du client")

    # Identifiants des systèmes externes
    wpwc_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True,
                                                comment="Identifiant WooCommerce")
    henrri_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True,
                                                  comment="Identifiant Henrri")

    # Données client
    customer_type: Mapped[str] = mapped_column(String(20), nullable=False, default="part",
                                               comment="Type de client : part/pro")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                            comment="Statut actif/inactif du client")

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date de création du client")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date de dernière mise à jour du client")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True,
                                                            comment="Dernière synchronisation")

    # Relations avec d'autres tables
    part = relationship("CustomerParts", back_populates="customer", uselist=False)
    pro = relationship("CustomerPros", back_populates="customer", uselist=False)
    addresses = relationship("CustomerAddresses", back_populates="customer", uselist=True)
    emails = relationship("CustomerMails", back_populates="customer", uselist=True)
    phones = relationship("CustomerPhones", back_populates="customer", uselist=True)
    sync_logs = relationship("CustomerSyncLog", back_populates="customer", uselist=True)
    orders = relationship("Order", back_populates="customer", uselist=True)

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
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "part": self.part.to_dict() if self.part else None,
            "pro": self.pro.to_dict() if self.pro else None,
            "addresses": [addr.to_dict() for addr in self.addresses] if self.addresses else None,
            "emails": [email.to_dict() for email in self.emails] if self.emails else None,
            "phones": [phone.to_dict() for phone in self.phones] if self.phones else None,
            "sync_logs": [log.to_dict() for log in self.sync_logs] if self.sync_logs else None
        }

    @classmethod
    def from_dict(cls, *, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un dictionnaire d'objets Customer à partir d'un dictionnaire pur.
        Args:
            data (Dict[str, Any]): Dictionnaire contenant les données du client.
        Returns:
            Dict[str, Any]: Dictionnaire avec les objets Customer, CustomerParts, CustomerPros
                            et des listes d'objets CustomerAddresses, CustomerMails, CustomerPhones,
                            CustomerSyncLog.
        """
        customer = cls(
            wpwc_id=data.get("wpwc_id"),
            henrri_id=data.get("henrri_id"),
            customer_type=data.get("customer_type", "part"),
            is_active=data.get("is_active", True),
            last_synced_at=datetime.fromisoformat(data.get("last_synced_at", "")) \
                                    if data.get("last_synced_at") else None
        )

        part = CustomerParts.from_dict(data["part"]) if data.get("part") else None
        pro = CustomerPros.from_dict(data["pro"]) if data.get("pro") else None

        addresses = [
            CustomerAddresses.from_dict(a) for a in data.get("addresses", [])
        ]

        emails = [
            CustomerMails.from_dict(e) for e in data.get("emails", [])
        ]

        return {
            "customer": customer,
            "part": part,
            "pro": pro,
            "addresses": addresses,
            "emails": emails,
        }

class CustomerParts(WorkingBase, QueryMixin):
    """Database model for Customer Parts table."""

    __tablename__ = "customer_parts"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant Part unique")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK),
                                             nullable=False, unique=True,
                                             comment="Id client associé à part")

    # Données personnelles
    civil_title: Mapped[str | None] = mapped_column(String(20), nullable=True,
                                                   comment="Civilité (ex: M., Mme, Dr)")
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relations
    customer = relationship("Customers", back_populates="part", uselist=False)

    def __repr__(self) -> str:
        """Représentation en chaîne de l'objet CustomerPart."""
        return f"<CustomerPart(id={self.id}, customer_id={self.customer_id}, "\
            + f"first_name={self.first_name}, last_name={self.last_name})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPart en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "civil_title": self.civil_title,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerParts":
        """Crée un objet CustomerPart à partir d'un dictionnaire."""
        date_of_birth = data.get("date_of_birth")
        return cls(
            customer_id=data.get("customer_id", 0),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            date_of_birth=datetime.fromisoformat(date_of_birth) if date_of_birth else None
        )

class CustomerPros(WorkingBase, QueryMixin):
    """Database model for Customer Pros table."""

    __tablename__ = "customer_pros"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK), nullable=False,
                                             unique=True, comment="Identifiant du client associé")

    # Données professionnelles
    company_name: Mapped[str] = mapped_column(String(200), nullable=False,
                                              comment="Nom de l'entreprise")
    siret_number: Mapped[str | None] = mapped_column(String(14), nullable=False, unique=True,
                                                     comment="Numéro SIRET de l'entreprise")
    vat_number: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True,
                                                  comment="Numéro de TVA intracommunautaire")

    # Relations
    customer = relationship("Customers", back_populates="pro", uselist=False)

    def __repr__(self) -> str:
        """Représentation en chaîne de l'objet CustomerPro."""
        return f"<CustomerPro(id={self.id}, customer_id={self.customer_id}, " \
            + f"company_name={self.company_name})>"

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
            vat_number=data.get("vat_number")
        )

class CustomerAddresses(WorkingBase, QueryMixin):
    """Database model for Customer Addresses table."""

    __tablename__ = "customer_addresses"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK), nullable=False,
                                             comment="Identifiant du client associé")

    # Données d'adresse
    address_name: Mapped[str | None] = mapped_column(String(100), nullable=True,
                                                     comment="Nom d'adresse (ex: home, work)")
    address_line1: Mapped[str] = mapped_column(String(200), nullable=False,
                                               comment="Ligne d'adresse 1")
    address_line2: Mapped[str] = mapped_column(String(200), nullable=True,
                                               comment="Ligne d'adresse 2")
    city: Mapped[str] = mapped_column(String(100), nullable=False, comment="Ville")
    state: Mapped[str] = mapped_column(String(100), nullable=False, comment="État/Région")
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="Code postal")
    country: Mapped[str] = mapped_column(String(100), nullable=False, comment="Pays",
                                         default="France")

    # Données de facturation/livraison
    is_billing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                              comment="Indique si c'est une adresse de facturation")
    is_shipping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                               comment="Indique si c'est une adresse de livraison")

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                            comment="Indique si l'adresse est active ou supprimée")

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création de l'adresse")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière mise à jour")

    customer = relationship("Customers", back_populates="addresses")

    def __repr__(self) -> str:
        return f"<CustomerAddress(id={self.id}, customer_id={self.customer_id}, " \
            + f"address_name={self.address_name}, " \
            + f"address_line1={self.address_line1}, address_line2={self.address_line2}, " \
            + f"city={self.city}, country={self.country})>"

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
            is_shipping=data.get("is_shipping", False)
        )

class CustomerMails(WorkingBase, QueryMixin):
    """Database model for Customer Mails table."""

    __tablename__ = "customer_mails"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant email unique")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK),
                                             nullable=False,
                                             comment="Id client associé à cet email")

    # Données d'e-mail
    email_name: Mapped[str | None] = mapped_column(String(100), nullable=True,
                                                  comment="Nom de l'e-mail (ex: perso, pro)")
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False,
                                       comment="Adresse e-mail du client")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                            comment="Indique si l'e-mail est actif ou supprimé")

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création de l'e-mail")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière mise à jour de l'e-mail")

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
            is_active=data.get("is_active", True)
        )

class CustomerPhones(WorkingBase, QueryMixin):
    """Database model for Customer Phones table."""

    __tablename__ = "customer_phones"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant téléphone unique")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK),
                                             nullable=False,
                                             comment="Id client associé à ce téléphone")

    # Données de téléphone
    phone_name: Mapped[str | None] = mapped_column(String(100), nullable=True,
                                                  comment="Nom du téléphone (ex: mobile, fixe)")
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False,
                                              comment="Numéro de téléphone du client")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                            comment="Indique si le téléphone est actif ou supprimé")

    # Metadonnées audit
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création du téléphone")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière MàJ du téléphone")

    # Relations
    customer = relationship("Customers", back_populates="phones")

    def __repr__(self) -> str:
        return f"<CustomerPhone(id={self.id}, customer_id={self.customer_id}, " \
            + f"phone_name={self.phone_name}, phone_number={self.phone_number})>"

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
            is_active=data.get("is_active", True)
        )

class CustomerSyncLog(WorkingBase):
    """Database model for Customer Synchronization Log.
    
    Tracks all synchronization events between the main database and external systems
    (WordPress/WooCommerce, Henrri).
    """
    __tablename__ = "customer_sync_logs"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK),
                                             nullable=False)

    # Synchronization details
    sync_source: Mapped[str] = mapped_column(String(50), nullable=False)  # wpwc, henrri
    sync_direction: Mapped[str] = mapped_column(String(20), nullable=False)  # in/out bound, 2dir
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, failed, pending

    # External system info
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_system: Mapped[str] = mapped_column(String(50), nullable=False)  # wordpress, henrri

    # Sync details
    fields_synced: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of sync
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    synced_at: Mapped[datetime] = mapped_column(DateTime,
                                               default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customers", back_populates="sync_logs")

    def __repr__(self) -> str:
        return f"<CustomerSyncLog(id={self.id}, customer_id={self.customer_id}, " \
            + f"sync_source={self.sync_source}, sync_status={self.sync_status})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerSyncLog en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "sync_source": self.sync_source,
            "sync_direction": self.sync_direction,
            "sync_status": self.sync_status,
            "external_id": self.external_id,
            "external_system": self.external_system,
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
            sync_source=data.get("sync_source", ""),
            sync_direction=data.get("sync_direction", "inbound"),
            sync_status=data.get("sync_status", "pending"),
            external_id=data.get("external_id"),
            external_system=data.get("external_system", ""),
            fields_synced=data.get("fields_synced"),
            error_message=data.get("error_message")
        )
