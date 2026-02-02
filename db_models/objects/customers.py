"""Database model for Customers table."""

from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Text
from db_models import Base

class Customers(Base):
    """Database model for Customers table.
    
    Single source of truth for customer data.
    Synchronizes with:
    - WordPress/WooCommerce (e-commerce)
    - Henrri (billing/invoicing)
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # External system identifiers
    wpwc_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    henrri_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    # Core customer information
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    orders = relationship("Orders", back_populates="customer")
    addresses = relationship("CustomerAddresses", back_populates="customer")
    mails = relationship("CustomerMails", back_populates="customer")
    phones = relationship("CustomerPhones", back_populates="customer")
    sync_logs = relationship("CustomerSyncLog", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, first_name={self.first_name}, " \
            + f"last_name={self.last_name})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet Customer en dictionnaire."""
        return {
            "id": self.id,
            "wpwc_id": self.wpwc_id,
            "henrri_id": self.henrri_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "customer_type": self.customer_type,
            "is_active": self.is_active,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Customers":
        """Crée un objet Customer à partir d'un dictionnaire."""
        return cls(
            wpwc_id=data.get("wpwc_id"),
            henrri_id=data.get("henrri_id"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            company_name=data.get("company_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            customer_type=data.get("customer_type", "individual"),
            is_active=data.get("is_active", True),
            notes=data.get("notes")
        )

    @classmethod
    def get_by_wpwc_id(cls, session: Any, wpwc_id: str) -> "Customers | None":
        """Récupère un client par son WPWC ID."""
        return session.query(cls).filter_by(wpwc_id=wpwc_id).first()

    @classmethod
    def get_all(cls, session: Any) -> list["Customers"]:
        """Récupère tous les clients."""
        return session.query(cls).all()

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
