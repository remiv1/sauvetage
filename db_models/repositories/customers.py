"""Repository pour les opérations sur les clients."""

from typing import Sequence, Tuple
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.customers import Customers

class CustomersRepository(BaseRepository):
    """Repository pour les opérations sur les clients."""
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

    def get_part(self, complete: bool = False) -> Sequence[Customers]:
        """Récupère tous les clients qui ont une relation avec la table 'part'.
        Returns:
            Sequence[Customers]: La liste des clients ayant une relation avec 'part'.
        """
        if complete:
            stmt = self._get_complete_query().where(Customers.customer_type == 'part')
        else:
            stmt = Customers.by(customer_type = 'part')

        return self.session.execute(stmt).scalars().all()

    def _get_complete_query(self) -> Select[Tuple[Customers]]:
        """Récupère un client avec toutes ses relations (emails, phones, etc.) en fonction de son ID.
        Args:
            customer_id (int): L'ID du client à rechercher.
        Returns:
            List[Customers] | None: Le clt complet correspondant à l'ID ou None s'il n'existe pas.
        """
        return (
            select(Customers)
            .options(
                joinedload(Customers.part),
                joinedload(Customers.pro),
                selectinload(Customers.addresses),
                selectinload(Customers.emails),
                selectinload(Customers.phones)
            )
        )
