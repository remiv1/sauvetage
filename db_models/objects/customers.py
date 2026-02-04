"""Database model for Customers table."""

from typing import Any, Dict, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Text, Boolean, ForeignKey
from db_models import Base

CUSTOMER_PK = "customers.id"

class Customers(Base):
    """Modèle de base de données pour la table client.
    
    Cette base de données est source unique de vérité.
    Synchronisé avec deux systèmes externes :
    - WordPress/WooCommerce (e-commerce)
    - Henrri (Facturation/Comptabilité)
    """

    __tablename__ = "customers"

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
    mails = relationship("CustomerMails", back_populates="customer", uselist=True)
    phones = relationship("CustomerPhones", back_populates="customer", uselist=True)
    sync_logs = relationship("CustomerSyncLog", back_populates="customer", uselist=True)

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
            "mails": [mail.to_dict() for mail in self.mails] if self.mails else None,
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

        return {
            "customer": customer,
            "part": part,
            "pro": pro,
            "addresses": addresses,
        }

    @classmethod
    def get_by(cls, *, session: Any, filter_tuple: Tuple[str, Any]) -> "Customers | None":
        """Récupère un client par son WPWC ID."""
        if not filter_tuple or len(filter_tuple) != 2:
            return None
        return session.query(cls).filter_by(**{filter_tuple[0]: filter_tuple[1]}).first()

    @classmethod
    def get_all(cls, *, session: Any) -> list["Customers"]:
        """Récupère tous les clients."""
        return session.query(cls).all()

class CustomerParts(Base):
    """Database model for Customer Parts table."""

    __tablename__ = "customer_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK),
                                             nullable=False, unique=True,
                                             comment="Identifiant du client associé")

    # Données personnelles
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

class CustomerPros(Base):
    """Database model for Customer Pros table."""

    __tablename__ = "customer_pros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique")
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey(CUSTOMER_PK), nullable=False,
                                             unique=True, comment="Identifiant du client associé")
    company_name: Mapped[str] = mapped_column(String(200), nullable=False,
                                              comment="Nom de l'entreprise")
    siret_number: Mapped[str | None] = mapped_column(String(14), nullable=False, unique=True,
                                                     comment="Numéro SIRET de l'entreprise")
    vat_number: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True,
                                                  comment="Numéro de TVA intracommunautaire")

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

class CustomerAddresses(Base):
    """Database model for Customer Addresses table."""

    __tablename__ = "customer_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    address_line1: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line2: Mapped[str] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customers", back_populates="addresses")

    def __repr__(self) -> str:
        return f"<CustomerAddress(id={self.id}, customer_id={self.customer_id}, " \
            + f"city={self.city}, country={self.country})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerAddress en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerAddresses":
        """Crée un objet CustomerAddress à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            address_line1=data.get("address_line1", ""),
            address_line2=data.get("address_line2", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", "")
        )

    @classmethod
    def get_by_customer_id(cls, session: Any, customer_id: int) -> list["CustomerAddresses"]:
        """Récupère les adresses d'un client par son ID."""
        return session.query(cls).filter_by(customer_id=customer_id).all()

    @classmethod
    def get_all(cls, session: Any) -> list["CustomerAddresses"]:
        """Récupère toutes les adresses des clients."""
        return session.query(cls).all()

class CustomerMails(Base):
    """Database model for Customer Mails table."""

    __tablename__ = "customer_mails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customers", back_populates="mails")

    def __repr__(self) -> str:
        return f"<CustomerMail(id={self.id}, customer_id={self.customer_id}, email={self.email})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerMail en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerMails":
        """Crée un objet CustomerMail à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            email=data.get("email", "")
        )

    @classmethod
    def get_by_customer_id(cls, session: Any, customer_id: int) -> list["CustomerMails"]:
        """Récupère les mails d'un client par son ID."""
        return session.query(cls).filter_by(customer_id=customer_id).all()

    @classmethod
    def get_all(cls, session: Any) -> list["CustomerMails"]:
        """Récupère tous les mails des clients."""
        return session.query(cls).all()

class CustomerPhones(Base):
    """Database model for Customer Phones table."""

    __tablename__ = "customer_phones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customers", back_populates="phones")

    def __repr__(self) -> str:
        return f"<CustomerPhone(id={self.id}, customer_id={self.customer_id}, "\
            + f"phone_number={self.phone_number})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPhone en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "phone_number": self.phone_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerPhones":
        """Crée un objet CustomerPhone à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            phone_number=data.get("phone_number", "")
        )

    @classmethod
    def get_by_customer_id(cls, session: Any, customer_id: int) -> list["CustomerPhones"]:
        """Récupère les numéros de téléphone d'un client par son ID."""
        return session.query(cls).filter_by(customer_id=customer_id).all()

    @classmethod
    def get_all(cls, session: Any) -> list["CustomerPhones"]:
        """Récupère tous les numéros de téléphone des clients."""
        return session.query(cls).all()


class CustomerSyncLog(Base):
    """Database model for Customer Synchronization Log.
    
    Tracks all synchronization events between the main database and external systems
    (WordPress/WooCommerce, Henrri).
    """

    __tablename__ = "customer_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)

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

    @classmethod
    def get_by_customer_id(cls, session: Any, customer_id: int) -> list["CustomerSyncLog"]:
        """Récupère les logs de synchronisation d'un client."""
        return session.query(cls).filter_by(customer_id=customer_id).all()

    @classmethod
    def get_by_external_id(cls, session: Any, external_id: str,
                           external_system: str) -> list["CustomerSyncLog"]:
        """Récupère les logs de synchronisation par ID externe et système."""
        return session.query(cls).filter_by(
            external_id=external_id,
            external_system=external_system
        ).all()

    @classmethod
    def get_all(cls, session: Any) -> list["CustomerSyncLog"]:
        """Récupère tous les logs de synchronisation."""
        return session.query(cls).all()
