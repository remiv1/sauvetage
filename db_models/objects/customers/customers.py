"""Modèle principal des clients."""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
from db_models import WorkingBase
from db_models.objects.common import QueryMixin
from db_models.objects.customers.constants import CASCADE_ALL
from db_models.objects.customers.addresses import CustomerAddresses


class Customers(WorkingBase, QueryMixin):
    """
    Modèle de base de données pour la table client.
    """

    __tablename__ = "customers"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du client",
    )
    wpwc_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, comment="Identifiant WooCommerce"
    )
    henrri_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, comment="Identifiant Henrri"
    )
    customer_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="part", comment="Type de client : part/pro"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Statut actif/inactif du client"
    )
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

    part = relationship(
        "CustomerParts",
        back_populates="customer",
        uselist=False,
        cascade=CASCADE_ALL,
    )
    pro = relationship(
        "CustomerPros",
        back_populates="customer",
        uselist=False,
        cascade=CASCADE_ALL,
    )
    addresses = relationship(
        "CustomerAddresses",
        back_populates="customer",
        uselist=True,
        cascade=CASCADE_ALL,
    )
    emails = relationship(
        "CustomerMails",
        back_populates="customer",
        uselist=True,
        cascade=CASCADE_ALL,
    )
    phones = relationship(
        "CustomerPhones",
        back_populates="customer",
        uselist=True,
        cascade=CASCADE_ALL,
    )
    sync_logs = relationship(
        "CustomerSyncLog",
        back_populates="customer",
        uselist=True,
        cascade=CASCADE_ALL,
    )
    orders = relationship(
        "Order",
        back_populates="customer",
        uselist=True,
        cascade=CASCADE_ALL,
    )
    invoices = relationship(
        "Invoice",
        back_populates="customer",
        uselist=True,
        cascade=CASCADE_ALL,
    )

    @hybrid_property
    def full_name(self) -> str:
        """Nom complet du client."""
        if self.part:
            return f"{self.part.first_name} {self.part.last_name}"
        if self.pro:
            return self.pro.company_name
        return f"Client #{self.id}"

    def __repr__(self) -> str:
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

    def to_dict_henrri(self, with_contact: bool = True) -> dict[str, Any]:
        """Convertit l'objet Customer en dictionnaire Henrri.

        Args:
            with_contact: Inclut le contact dans le payload lorsque True.

        Returns:
            dict[str, Any]: Dictionnaire client au format attendu par Henrri.

        Raises:
            ValueError: Si aucune adresse de facturation active n'est disponible
                ou si celle-ci est incomplète.
        """
        date_now = str(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        address = self.get_henrri_billing_address()
        address_payload = address.to_dict_henrri()
        email = next(
            (e.email for e in self.emails if e.is_active),
            None
        ) if self.emails else None
        phone = next(
            (p.phone_number for p in self.phones if p.is_active and len(p.phone_number) > 0),
            None
        ) if self.phones else None
        mobile = next(
            (p.phone_number for p in self.phones if p.is_active),
            None
        ) if self.phones else None
        phone = self._normalize_henrri_phone(phone)
        mobile = self._normalize_henrri_phone(mobile)

        if self.henrri_id is not None:
            customer_id = int(self.henrri_id)
        else:
            customer_id = None

        if self.pro:
            siret = self.pro.siret_number
            vat_number = self.pro.vat_number or None
            customer = {
                "name": self.full_name,
                "type": "professional",
                "company_identifier_type": "Siret" if siret and len(siret) == 14 else "Unknown",
                "creation_date": date_now,
                "siret": siret,
                "trade_name": self.pro.company_name,
                "company_name": self.pro.company_name,
                "ict": vat_number,
                "vat_number": vat_number,
                "customer_type_alert_enabled": False,
                "address": address_payload,
            }
        else:
            customer = {
                "name": self.full_name,
                "type": "individual",
                "creation_date": date_now,
                "customer_type_alert_enabled": False,
                "address": address_payload,
            }

        if customer_id is not None:
            customer["id"] = customer_id
        if with_contact:
            customer["contacts"] = [self._build_henrri_contact(email, phone, mobile)]
        return customer

    def _build_henrri_contact(
        self,
        email: str | None,
        phone: str | None,
        mobile: str | None,
    ) -> dict[str, Any]:
        """Construit le contact principal dans le format attendu par Henrri."""
        if self.pro:
            first_name = ""
            last_name = self.pro.company_name
            contact_id = self.pro.contact_henrri_id
        else:
            first_name, last_name = self._get_names()
            contact_id = self.part.contact_henrri_id if self.part else None

        return {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "id": contact_id,
            "is_primary": True,
            "mobile": mobile,
            "phone": phone,
            "role": "administrateur",
            "show_on_document": True,
        }

    def get_henrri_billing_address(self) -> "CustomerAddresses":
        """Retourne l'adresse de facturation active et complète du client.

        Returns:
            CustomerAddresses: L'adresse de facturation prête à être envoyée chez Henrri.

        Raises:
            ValueError: Si aucune adresse n'est à la fois de facturation, active et complète.
        """
        address = next(
            (
                addr
                for addr in (self.addresses or [])
                if addr.is_billing
                and addr.is_active
                and all(
                    (
                        (getattr(addr, "address_line1", "") or "").strip(),
                        (getattr(addr, "city", "") or "").strip(),
                        (getattr(addr, "postal_code", "") or "").strip(),
                    )
                )
            ),
            None,
        )
        if address is None:
            raise ValueError(
                f"Client {self.id} sans adresse de facturation active et complète "
                "(rue, ville, code postal), synchronisation Henrri impossible."
            )
        return address

    @staticmethod
    def _normalize_henrri_phone(phone: str | None) -> str | None:
        """Retourne un téléphone compatible avec les contraintes de l'API Henrri."""
        if not phone:
            return None
        normalized = "".join(char for char in phone if char.isdigit() or char in "+-()")
        return normalized if any(char.isdigit() for char in normalized) else None

    def _get_names(self) -> tuple[str | None, str | None]:
        if self.pro:
            return "", self.pro.company_name
        if self.part:
            return self.part.first_name, self.part.last_name
        return None, None

    def get_wpwc_mail(self) -> Optional[str]:
        """Récupère l'email du client à utiliser pour WooCommerce."""
        return next((
            e.email for e in self.emails if "WooCommerce" in e.email_name),
            next((e.email for e in self.emails if e.is_active), None))

    def get_wpwc_phone(self) -> Optional[str]:
        """Récupère le téléphone du client à utiliser pour WooCommerce."""
        return next((
            p.phone_number for p in self.phones if "WooCommerce" in p.phone_name),
            next((p.phone_number for p in self.phones if p.is_active), None))

    def get_wpwc_billing_address(self) -> Optional[CustomerAddresses]:
        """Récupère l'adresse de facturation du client à utiliser pour WooCommerce."""
        return next((
            a for a in self.addresses if a.is_billing and "WooCommerce" in a.address_name),
            next((a for a in self.addresses if a.is_billing and a.is_active), None))

    def get_wpwc_shipping_address(self) -> Optional[CustomerAddresses]:
        """Récupère l'adresse de livraison du client à utiliser pour WooCommerce."""
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
            "first_name": first_name,
            "last_name": last_name,
            "address_1": billing_address.address_line1 if billing_address else None,
            "address_2": billing_address.address_line2 if billing_address else None,
            "city": billing_address.city if billing_address else None,
            "state": billing_address.state if billing_address else None,
            "postcode": billing_address.postal_code if billing_address else None,
            "country": billing_address.country if billing_address else None,
            "email": email,
            "phone": phone,
        }
        shipping = {
            "first_name": first_name,
            "last_name": last_name,
            "address_1": shipping_address.address_line1 if shipping_address else None,
            "address_2": shipping_address.address_line2 if shipping_address else None,
            "city": shipping_address.city if shipping_address else None,
            "state": shipping_address.state if shipping_address else None,
            "postcode": shipping_address.postal_code if shipping_address else None,
            "country": shipping_address.country if shipping_address else None,
        }
        return billing, shipping

    def to_dict_for_wpwc(self, update: bool = False) -> dict[str, Any]:
        """Convertit les données du client pour WooCommerce."""
        first_name, last_name = self._get_names()
        billing, shipping = self._wpwc_dispatch_addresses()
        meta_data = []
        if self.customer_type == "pro":
            meta_data.append({"key": "billing_wooccm10", "value": "Professionnel"})
            meta_data.append({"key": "billing_wooccm11", "value": self.pro.company_name})
            meta_data.append({"key": "billing_wooccm12", "value": self.pro.siret_number})
            username = self.pro.company_name
        else:
            meta_data.append({"key": "billing_wooccm10", "value": "Particulier"})
            username = f"{self.part.first_name} {self.part.last_name}"
        final_dict = {
            "email": billing["email"],
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "billing": billing,
            "shipping": shipping,
            "meta_data": meta_data,
        }
        if update:
            final_dict = {key: value for key, value in final_dict.items() if value}
            final_dict["date_modified_gmt"] = self.sync_logs[-1].created_at.isoformat() \
                if self.sync_logs else None
        return final_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Customers":
        """Crée un objet Customer à partir d'un dictionnaire."""
        return cls(**data)
