"""
Dépôt de données pour les fournisseurs. Ceci ne contient que d'une classe :
    - SuppliersRepository : Contient les méthodes pour interagir avec les données des fournisseurs,
        notamment la validation des données, la création de nouveaux fournisseurs, et la
        gestion des fournisseurs.
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Suppliers

class SuppliersRepository(BaseRepository):
    """
    Dépôt de données pour les fournisseurs.
    Contient les méthodes :
    - get_by_id : pour récupérer un fournisseur par son identifiant.
    - create_supplier : pour créer un nouveau fournisseur.
    - update_supplier : pour mettre à jour les informations d'un fournisseur existant.
    - deactivate_supplier : pour désactiver un fournisseur (soft delete).
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
            raise ValueError(f"Erreur lors de la création du fournisseur : {e.orig}") from e

    def update_supplier(self, supplier: Suppliers, *, name: str | None = None,
                        email: str | None = None, phone: str | None = None) -> Suppliers:
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
            raise ValueError(f"Erreur lors de la mise à jour du fournisseur : {e.orig}") from e

    def deactivate_supplier(self, supplier: Suppliers) -> Suppliers:
        """Désactive un fournisseur (Soft delete).
        Args:
            supplier (Suppliers): Le fournisseur à désactiver.
        Returns:
            Suppliers: Le fournisseur désactivé.
        """
        supplier.is_active = False
        try:
            self.session.commit()
            return supplier
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la désactivation du fournisseur : {e.orig}") from e
