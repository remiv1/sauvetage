"""
Dépôt de données pour les fournisseurs. Ceci ne contient que d'une classe :
    - SuppliersRepository : Contient les méthodes pour interagir avec les données des fournisseurs,
        notamment la validation des données, la création de nouveaux fournisseurs, et la
        gestion des fournisseurs.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import and_
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Suppliers

logger = logging.getLogger("app_back.repositories.suppliers")

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

    def get_by_gln13(self, gln13: str) -> "Suppliers | None":
        """Récupère un fournisseur par son code GLN13.
        Args:
            gln13 (str): Le code GLN13 du fournisseur à récupérer.
        Returns:
            Suppliers | None: Le fournisseur correspondant au code GLN13,
                             ou None s'il n'existe pas.
        """
        stmt = select(Suppliers).where(Suppliers.gln13 == gln13)
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

    def create_supplier(self, *, supplier: Suppliers, commit: bool = True) -> Suppliers:
        """Crée un nouveau fournisseur.
        Args:
            supplier (Suppliers): Le fournisseur à créer.
            commit (bool): Indique si la transaction doit être commise immédiatement.
        Returns:
            Suppliers: Le fournisseur créé mais pas encore commité en base de données.
        """
        self.session.add(supplier)
        if commit:
            self.commit()
        return supplier

    def update_supplier(
        self,
        supplier: Suppliers,
        commit: bool = True,
        existing_id: Optional[int] = None,
    ) -> Suppliers:
        """Met à jour les informations d'un fournisseur existant.
        Args:
            supplier (Suppliers): Le fournisseur à mettre à jour.
        Returns:
            Suppliers: Le fournisseur mis à jour mais pas encore commité en base de données.
        """
        if existing_id:
            supplier.id = existing_id
        else:
            old_supplier = self.get_by_gln13(supplier.gln13)
            if old_supplier is None:
                raise ValueError("Fournisseur à mettre à jour introuvable")
            supplier.id = old_supplier.id  # Assure que l'ID reste le même pour la mise à jour
        supplier = self.session.merge(supplier)
        if commit:
            self.commit()
        return supplier

    def sync_supplier(self, suppliers: list[Suppliers]) -> None:
        """Synchronise la liste des fournisseurs avec la base de données.
        Cette méthode compare la liste des fournisseurs fournie avec les fournisseurs
        existants en base de données, et effectue les opérations nécessaires pour
        créer, mettre à jour ou désactiver les fournisseurs afin que la base de données
        reflète exactement la liste fournie.
        
        param :
            - suppliers: liste des fournisseurs à synchroniser avec la base de données.
        """
        ex, nex = 0, 0
        for supplier in suppliers:
            existing = self.get_by_gln13(supplier.gln13)
            if existing is None:
                ex += 1
                self.create_supplier(supplier=supplier, commit=False)
            else:
                nex += 1
                self.update_supplier(supplier=supplier, commit=False)
        logger.info(
            "Synchronisation des fournisseurs terminée: %d créés, %d mis à jour.",
            ex,
            nex,
        )
        self.commit()

    def toggle_active(self, supplier: Suppliers) -> Suppliers:
        """Active ou désactive un fournisseur (bascule).
        Args:
            supplier (Suppliers): Le fournisseur à activer/désactiver.
        Returns:
            Suppliers: Le fournisseur avec le statut inversé.
        """
        supplier.is_active = not supplier.is_active
        self.commit()
        return supplier

    def commit(self) -> None:
        """Commit les changements en base de données."""
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors du commit en base de données : {e.orig}"
            ) from e
