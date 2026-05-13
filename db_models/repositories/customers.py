"""Repository pour les opérations sur les clients."""

from typing import Tuple, Sequence, Optional, Any
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select, and_
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import (
    Customers,
    CustomerParts,
    CustomerPros,
    CustomerAddresses,
    CustomerMails,
    CustomerPhones,
)
from db_models.models.woo import WCCustomerGet

UPDATE_FIELDS = {
    "part": ("civil_title", "first_name", "last_name", "date_of_birth"),
    "pro": ("company_name", "siret_number", "vat_number"),
}

class CustomersRepository(BaseRepository):
    """Repository pour les opérations sur les clients."""

    def get_by_name_like(
        self, name: str, complete: bool = False
    ) -> Optional[Sequence[Customers]]:
        """Récupère les clients dont le nom correspond à une recherche de type "like".
        Args:
            name (str): Le nom à rechercher (peut être partiel).
        Returns:
            Optional[Sequence[Customers]]: Une liste de clients correspondant à la recherche
                                        ou None s'il n'y en a pas.
        """
        pattern = f"%{name}%"
        if complete:
            stmt = self._get_complete_query().where(
                (Customers.part.has(CustomerParts.first_name.ilike(pattern)))
                | (Customers.part.has(CustomerParts.last_name.ilike(pattern)))
                | (Customers.pro.has(CustomerPros.company_name.ilike(pattern)))
            )
        else:
            stmt = select(Customers).where(
                (Customers.part.has(CustomerParts.first_name.ilike(pattern)))
                | (Customers.part.has(CustomerParts.last_name.ilike(pattern)))
                | (Customers.pro.has(CustomerPros.company_name.ilike(pattern)))
            )

        result = self.session.execute(stmt).scalars().all()
        return result if result else None

    def get_by_email(self, email: str, complete: bool = False) -> Customers | None:
        """Récupère un client en fonction de son adresse e-mail.
        Args:
            email (str): L'adresse e-mail du client à rechercher.
        Returns:
            Customers | None: Le client correspondant à l'adresse e-mail ou None s'il n'existe pas.
        """
        if complete:
            stmt = self._get_complete_query().where(Customers.emails.any(email=email))
        else:
            stmt = select(Customers).where(Customers.emails.any(email=email))

        return self.session.execute(stmt).scalars().first()

    def get_by_phone(self, phone: str, complete: bool = False) -> Customers | None:
        """Récupère un client en fonction de son numéro de téléphone.
        Args:
            phone (str): Le numéro de téléphone du client à rechercher.
        Returns:
            Customers | None: Le client correspondant au numéro de téléphone ou None
            s'il n'existe pas.
        """
        if complete:
            stmt = self._get_complete_query().where(Customers.phones.any(phone=phone))
        else:
            stmt = select(Customers).where(Customers.phones.any(phone=phone))

        return self.session.execute(stmt).scalars().first()

    def get_by_id(self, customer_id: int, complete: bool = False) -> Customers | None:
        """Récupère un client en fonction de son ID.
        Args:
            customer_id (int): L'ID du client à rechercher.
        Returns:
            Customers | None: Le client correspondant à l'ID ou None s'il n'existe pas.
        """
        if complete:
            stmt = self._get_complete_query().where(Customers.id == customer_id)
        else:
            stmt = select(Customers).where(Customers.id == customer_id)

        return self.session.execute(stmt).scalars().first()

    def get_by_wpwc_id(
            self,
            wpwc_customer_id: int | str,
            complete: bool = True
        ) -> Customers | None:
        """Récupère un client en fonction de son ID WooCommerce.
        Args:
            wpwc_customer_id (int | str): L'ID WooCommerce du client à rechercher.
        Returns:
            Customers | None: Le client correspondant à l'ID WooCommerce ou None s'il n'existe pas.
        """
        if complete:
            stmt = self._get_complete_query().where(
                Customers.wpwc_customer_id == str(wpwc_customer_id)
            )
        else:
            stmt = select(Customers).where(
                Customers.wpwc_customer_id == str(wpwc_customer_id)
            )

        return self.session.execute(stmt).scalars().first()

    def _get_complete_query(self) -> Select[Tuple[Customers]]:
        """
        Récupère un client avec toutes ses relations (emails, phones, etc.) en fonction de son ID.
        Args:
            customer_id (int): L'ID du client à rechercher.
        Returns:
            List[Customers] | None: Le clt complet correspondant à l'ID ou None s'il n'existe pas.
        """
        return select(Customers).options(
            joinedload(Customers.part),
            joinedload(Customers.pro),
            selectinload(Customers.addresses),
            selectinload(Customers.emails),
            selectinload(Customers.phones),
        )

    def _apply_updates(self, target, data, allowed_fields):
        for field in allowed_fields:
            if field in data:
                setattr(target, field, data[field])


    def update_info(self, customer_id: int, data: dict) -> Customers:
        """Met à jour les informations d'un client.
        Cette méthode permet de mettre à jour les informations d'un client en fonction de son ID.
        Args:
            customer_id (int): L'ID du client à mettre à jour.
            data (dict): Un dictionnaire avec les champs à mettre à jour et leurs nv valeurs.
        Returns:
            Customers: Le client mis à jour.
        Raises:
            ValueError: Si le client n'existe pas ou si une erreur survient lors de la mise à jour.
        """
        customer = self.get_by_id(customer_id, complete=True)
        if not customer:
            raise ValueError(f"Client #{customer_id} introuvable.")

        customer_type = customer.customer_type
        target = getattr(customer, customer_type, None)

        if not target:
            raise ValueError(f"Le client #{customer_id} n'a pas de données '{customer_type}'.")

        self._apply_updates(target, data, UPDATE_FIELDS[customer_type])

        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc

        return customer


    def create(self, customer_data: dict) -> Customers:
        """Crée un nouveau client à partir d'un dictionnaire de données.
        Args:
            customer_data (dict): Un dictionnaire contenant les données du client à créer.
        Returns:
            Customers: Le client nouvellement créé.
        """
        if customer_data.get("customer_type") == "part" and "part" in customer_data:
            customer_data["part"] = CustomerParts(**customer_data["part"])
        elif customer_data.get("customer_type") == "pro" and "pro" in customer_data:
            customer_data["pro"] = CustomerPros(**customer_data["pro"])
        else:
            message = "Le type client doit être 'part' ou 'pro' et les données fournies."
            raise ValueError(message)
        if "addresses" in customer_data:
            customer_data["addresses"] = [
                CustomerAddresses(**addr) for addr in customer_data["addresses"]
            ]
        if "emails" in customer_data:
            customer_data["emails"] = [
                CustomerMails(**mail) for mail in customer_data["emails"]
            ]
        if "phones" in customer_data:
            customer_data["phones"] = [
                CustomerPhones(**phone) for phone in customer_data["phones"]
            ]
        new_customer = Customers(**customer_data)
        self.session.add(new_customer)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc
        return new_customer

    def create_from_woo_commerce(self, wpwc_customer_data: Optional[dict[str, Any]]) -> Customers:
        """Crée un client à partir des données d'un client WooCommerce.
        Args:
            wpwc_customer_data (dict): Un dictionnaire contenant les données du client WooCommerce.
        Returns:
            Customers: Le client nouvellement créé.
        """
        if not wpwc_customer_data:
            raise ValueError("Données du client WooCommerce manquantes.")
        # Création des objets liés en fonction des données WooCommerce
        woo_customer = WCCustomerGet(**wpwc_customer_data)
        cust: Customers = Customers().from_dict(woo_customer.to_dict_customer_for_erp())
        c_part, c_pro = woo_customer.to_dict_customer_part_pro_for_erp()
        cust_part = CustomerParts().from_dict(c_part if c_part else {})
        cust_pro = CustomerPros().from_dict(c_pro if c_pro else {})
        ad = [CustomerAddresses().from_dict(addr) \
              for addr in woo_customer.to_dict_customer_address_for_erp()]
        for address in woo_customer.to_dict_customer_address_for_erp():
            ad.append(CustomerAddresses().from_dict(address))
        ph = CustomerPhones().from_dict(woo_customer.to_dict_customer_phone_for_erp())
        mail = CustomerMails().from_dict(woo_customer.to_dict_customer_mail_for_erp())

        # Association des objets liés au client
        cust.part = cust_part
        cust.pro = cust_pro
        cust.addresses = ad
        if ph:
            cust.phones = [ph]
        cust.emails = [mail]
        self.session.add(cust)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc
        return cust

class CustomerAddressesRepository(BaseRepository):
    """Repository pour les opérations sur les adresses des clients."""

    def get_by_id(self, address_id: int) -> CustomerAddresses | None:
        """Récupère une adresse de client en fonction de son ID.
        Args:
            address_id (int): L'ID de l'adresse à rechercher.
        Returns:
            CustomerAddresses | None: L'adresse correspondant à l'ID ou None s'il n'existe pas.
        """
        return self.session.get(CustomerAddresses, address_id)

    def get_by_customer_id(
            self,
            customer_id: int,
            is_active: Optional[bool] = None
        ) -> Sequence[CustomerAddresses]:
        """Récupère toutes les adresses d'un client en fonction de son ID.
        Args:
            customer_id (int): L'ID du client dont on veut récupérer les adresses.
            is_active (bool, optional): Filtre par statut actif/inactif.
        Returns:
            list[CustomerAddresses]: Une liste d'adresses correspondant au client.
        """
        stmt = select(CustomerAddresses).where(CustomerAddresses.customer_id == customer_id)
        if is_active is not None:
            stmt = stmt.where(CustomerAddresses.is_active == is_active)
        return self.session.execute(stmt).scalars().all()

    def get_billing_address(self, customer_id: int) -> Optional[CustomerAddresses]:
        """Récupère l'adresse de facturation d'un client.
        Args:
            customer_id (int): L'ID du client dont on veut récupérer l'adresse de facturation.
        Returns:
            Optional[CustomerAddresses]: L'adresse de facturation du client ou None s'il n'en a pas
        """
        stmt = select(CustomerAddresses).where(
            and_(
                CustomerAddresses.customer_id == customer_id,
                CustomerAddresses.is_billing == True,  # pylint: disable=singleton-comparison
                CustomerAddresses.is_active == True  # pylint: disable=singleton-comparison
            )
        )
        return self.session.execute(stmt).scalars().first()

    def get_shipping_address(self, customer_id: int) -> Optional[CustomerAddresses]:
        """Récupère l'adresse de livraison d'un client.
        Args:
            customer_id (int): L'ID du client dont on veut récupérer l'adresse de livraison.
        Returns:
            Optional[CustomerAddresses]: L'adresse de livraison du client ou None s'il n'en a pas.
        """
        stmt = select(CustomerAddresses).where(
            and_(
                CustomerAddresses.customer_id == customer_id,
                CustomerAddresses.is_shipping == True,  # pylint: disable=singleton-comparison
                CustomerAddresses.is_active == True  # pylint: disable=singleton-comparison
            )
        )
        return self.session.execute(stmt).scalars().first()

    def add_address(self, address_data: dict) -> CustomerAddresses:
        """Ajoute une nouvelle adresse à un client.
        Args:
            address_data (dict): Un dictionnaire contenant les champs de la nouvelle adresse.
        Returns:
            CustomerAddresses: L'adresse nouvellement créée.
        Raises:
            ValueError: Si le client n'existe pas.
        """
        customer_id = address_data.get("customer_id", None)
        if not customer_id:
            raise ValueError(
                "L'ID du client doit être fourni dans les données de l'adresse."
            )
        customer = (
            self.session.query(Customers).filter(Customers.id == customer_id).first()
        )
        if not customer:
            raise ValueError(f"Client #{customer_id} introuvable.")

        new_address = CustomerAddresses(**address_data, customer=customer)
        self.session.add(new_address)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc
        return new_address

    def update_address(
        self, customer_id: int, address_id: int, address_data: dict
    ) -> CustomerAddresses:
        """Met à jour une adresse d'un client.
        Args:
            customer_id (int): L'ID du client auquel appartient l'adresse.
            address_id (int): L'ID de l'adresse à mettre à jour.
            address_data (dict): Un dictionnaire contenant les champs de l'adresse à modifier.
        Returns:
            CustomerAddresses: L'adresse mise à jour.
        Raises:
            ValueError: Si l'adresse n'existe pas.
        """
        address = (
            self.session.query(CustomerAddresses)
            .filter(
                and_(
                    CustomerAddresses.id == address_id,
                    CustomerAddresses.customer_id == customer_id,
                    CustomerAddresses.is_active == True,  # pylint: disable=singleton-comparison
                )
            )
            .first()
        )
        if not address:
            raise ValueError(f"Adresse #{address_id} introuvable.")

        # Mise à jour des champs de l'adresse
        for field, value in address_data.items():
            setattr(address, field, value)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc

        return address

    def delete_address(self, address_id: int) -> None:
        """Soft-supprime une adresse d'un client.
        Args:
            address_id (int): L'ID de l'adresse à supprimer.
        Raises:
            ValueError: Si l'adresse n'existe pas.
        """
        address = (
            self.session.query(CustomerAddresses)
            .filter(
                and_(
                    CustomerAddresses.id == address_id,
                    CustomerAddresses.is_active == True,  # pylint: disable=singleton-comparison
                )
            )
            .first()
        )
        if not address:
            raise ValueError(f"Adresse #{address_id} introuvable.")

        address.is_active = False
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc


class CustomerMailsRepository(BaseRepository):
    """Repository pour les opérations sur les e-mails des clients."""

    def add_email(self, email_data: dict) -> CustomerMails:
        """Ajoute une nouvelle adresse e-mail à un client.
        Args:
            email_data (dict): Un dictionnaire contenant les champs du nouvel e-mail.
        Returns:
            CustomerMails: L'e-mail nouvellement créé.
        Raises:
            ValueError: Si le client n'existe pas.
        """
        customer_id = email_data.get("customer_id", None)
        if not customer_id:
            raise ValueError(
                "L'ID du client doit être fourni dans les données de l'e-mail."
            )
        customer = self.session.get(Customers, customer_id)
        if not customer:
            raise ValueError(f"Client #{customer_id} introuvable.")

        new_email = CustomerMails(**email_data)
        self.session.add(new_email)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc
        return new_email

    def update_email(
        self, customer_id: int, email_id: int, email_data: dict
    ) -> CustomerMails:
        """Met à jour une adresse e-mail d'un client.
        Args:
            customer_id (int): L'ID du client auquel appartient l'e-mail.
            email_id (int): L'ID de l'e-mail à mettre à jour.
            email_data (dict): Un dictionnaire contenant les champs de l'e-mail à modifier.
        Returns:
            CustomerMails: L'e-mail mis à jour.
        Raises:
            ValueError: Si l'e-mail n'existe pas.
        """
        email = (
            self.session.query(CustomerMails)
            .filter(
                and_(
                    CustomerMails.id == email_id,
                    CustomerMails.is_active == True,  # pylint: disable=singleton-comparison
                    CustomerMails.customer_id == customer_id,
                )
            )
            .first()
        )
        if not email:
            raise ValueError(f"E-mail #{email_id} introuvable.")

        # Mise à jour des champs de l'e-mail
        for field, value in email_data.items():
            setattr(email, field, value)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc

        return email

    def delete_email(self, email_id: int) -> None:
        """Soft-supprime une adresse e-mail d'un client.
        Args:
            email_id (int): L'ID de l'e-mail à supprimer.
        Raises:
            ValueError: Si l'e-mail n'existe pas.
        """
        email = (
            self.session.query(CustomerMails)
            .filter(
                and_(
                    CustomerMails.id == email_id,
                    CustomerMails.is_active == True  # pylint: disable=singleton-comparison
                )
            )
            .first()
        )
        if not email:
            raise ValueError(f"E-mail #{email_id} introuvable.")

        email.is_active = False
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc


class CustomerPhonesRepository(BaseRepository):
    """Repository pour les opérations sur les téléphones des clients."""

    def add_phone(self, phone_data: dict) -> CustomerPhones:
        """Ajoute un nouveau numéro de téléphone à un client.
        Args:
            phone_data (dict): Un dictionnaire contenant les champs du nouveau téléphone.
        Returns:
            CustomerPhones: Le téléphone nouvellement créé.
        Raises:
            ValueError: Si le client n'existe pas.
        """
        customer_id = phone_data.get("customer_id", None)
        if not customer_id:
            raise ValueError(
                "L'ID du client doit être fourni dans les données du téléphone."
            )
        customer = self.session.get(Customers, customer_id)
        if not customer:
            raise ValueError(f"Client #{customer_id} introuvable.")

        new_phone = CustomerPhones(**phone_data)
        self.session.add(new_phone)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc
        return new_phone

    def update_phone(
        self, customer_id: int, phone_id: int, phone_data: dict
    ) -> CustomerPhones:
        """Met à jour un numéro de téléphone d'un client.
        Args:
            customer_id (int): L'ID du client auquel appartient le téléphone.
            phone_id (int): L'ID du téléphone à mettre à jour.
            phone_data (dict): Un dictionnaire contenant les champs du téléphone à modifier.
        Returns:
            CustomerPhones: Le téléphone mis à jour.
        Raises:
            ValueError: Si le téléphone n'existe pas.
        """
        phone = (
            self.session.query(CustomerPhones)
            .filter(
                and_(
                    CustomerPhones.id == phone_id,
                    CustomerPhones.customer_id == customer_id,
                    CustomerPhones.is_active == True,  # pylint: disable=singleton-comparison
                )
            )
            .first()
        )
        if not phone:
            raise ValueError(f"Téléphone #{phone_id} introuvable.")

        # Mise à jour des champs du téléphone
        for field, value in phone_data.items():
            setattr(phone, field, value)

        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc

        return phone

    def delete_phone(self, phone_id: int) -> None:
        """Soft-supprime un numéro de téléphone d'un client.
        Args:
            phone_id (int): L'ID du téléphone à supprimer.
        Raises:
            ValueError: Si le téléphone n'existe pas.
        """
        phone = (
            self.session.query(CustomerPhones)
            .filter(
                and_(
                    CustomerPhones.id == phone_id,
                    CustomerPhones.is_active == True  # pylint: disable=singleton-comparison
                )
            )
            .first()
        )
        if not phone:
            raise ValueError(f"Téléphone #{phone_id} introuvable.")

        phone.is_active = False
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ValueError(str(exc)) from exc
