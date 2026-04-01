"""
Dépôt de données pour les fournisseurs. Ceci ne contient que d'une classe :
    - SuppliersRepository : Contient les méthodes pour interagir avec les données des fournisseurs,
        notamment la validation des données, la création de nouveaux fournisseurs, et la
        gestion des fournisseurs.
"""

from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import and_
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Suppliers


class SuppliersRepository(BaseRepository):
    """
    Dépôt de données pour les fournisseurs.
    Contient les méthodes :
    - get_by_id : pour récupérer un fournisseur par son identifiant.
    - search_paginated : pour rechercher des fournisseurs avec pagination et filtres.
    - create_supplier : pour créer un nouveau fournisseur.
    - update_supplier : pour mettre à jour les informations d'un fournisseur existant.
    - toggle_active : pour activer/désactiver un fournisseur (soft delete).
    """

    def get_by_id(self, supplier_id: int) -> "Suppliers | None":
        """Récupère un fournisseur par son identifiant.
        Args:
            supplier_id (int): L'identifiant du fournisseur à récupérer.
        Returns:
            Suppliers | None: Le fournisseur correspondant à l'identifiant,
                             ou None s'il n'existe pas.
        """
        stmt = select(Suppliers).where(Suppliers.id == supplier_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def search_paginated(
        self,
        *,
        name: str | None = None,
        gln13: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """Recherche paginée des fournisseurs avec filtres.
        Args:
            name: Filtre par nom (ILIKE).
            gln13: Filtre par code GLN (ILIKE).
            is_active: Filtre par statut actif/inactif (None = tous).
            page: Numéro de page (1-indexed).
            per_page: Nombre d'éléments par page.
        Returns:
            Dict avec clés: items, total, page, per_page.
        """
        conditions = []
        if name:
            conditions.append(Suppliers.name.ilike(f"%{name}%"))
        if gln13:
            conditions.append(Suppliers.gln13.ilike(f"%{gln13}%"))
        if is_active is not None:
            conditions.append(Suppliers.is_active.is_(is_active))

        where_clause = and_(*conditions) if conditions else True

        total = self.session.execute(
            select(func.count(Suppliers.id)).where(where_clause)    # type: ignore pylint: disable=not-callable
        ).scalar()

        offset = (page - 1) * per_page
        items = (
            self.session.execute(
                select(Suppliers)
                .where(where_clause)    # type: ignore
                .order_by(Suppliers.name)
                .offset(offset)
                .limit(per_page)
            )
            .scalars()
            .all()
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def create_supplier(self, *, name: str, email: str, phone: str) -> Suppliers:
        """Crée un nouveau fournisseur.
        Args:
            name (str): Le nom du fournisseur.
            email (str): L'adresse e-mail du fournisseur.
            phone (str): Le numéro de téléphone du fournisseur.
        Returns:
            Suppliers: Le fournisseur créé mais pas encore commité en base de données.
        """
        supplier = Suppliers(name=name, contact_email=email, contact_phone=phone)
        try:
            self.session.add(supplier)
            self.session.commit()
            return supplier
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création du fournisseur : {e.orig}"
            ) from e

    def update_supplier(
        self,
        supplier: Suppliers,
        *,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> Suppliers:
        """Met à jour les informations d'un fournisseur existant.
        Args:
            supplier (Suppliers): Le fournisseur à mettre à jour.
            name (str | None): Le nouveau nom du fournisseur (optionnel).
            email (str | None): La nouvelle adresse e-mail du fournisseur (optionnel).
            phone (str | None): Le nouveau numéro de téléphone du fournisseur (optionnel).
        Returns:
            Suppliers: Le fournisseur mis à jour mais pas encore commité en base de données.
        """
        if name is not None:
            supplier.name = name
        if email is not None:
            supplier.contact_email = email
        if phone is not None:
            supplier.contact_phone = phone
        try:
            self.session.commit()
            return supplier
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour du fournisseur : {e.orig}"
            ) from e

    def toggle_active(self, supplier: Suppliers) -> Suppliers:
        """Active ou désactive un fournisseur (bascule).
        Args:
            supplier (Suppliers): Le fournisseur à activer/désactiver.
        Returns:
            Suppliers: Le fournisseur avec le statut inversé.
        """
        supplier.is_active = not supplier.is_active
        try:
            self.session.commit()
            return supplier
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors du changement de statut du fournisseur : {e.orig}"
            ) from e
