"""Modules de gestion des variations d'objets liés aux objets généraux de la librairie."""

from typing import Any, Dict, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import ObjectVariations


class VariationsRepository(BaseRepository):
    """
    Repository pour la gestion des variations d'objets liés aux objets généraux.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = ObjectVariations
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def get_all(self, general_object_id: int) -> Sequence[ObjectVariations]:
        """Récupère toutes les variations d'un objet général donné."""
        stmt = select(self.model).where(
            self.model.general_object_id == general_object_id
        ).order_by(self.model.id)
        return self.session.execute(stmt).scalars().all()

    def get_by_id(self, variation_id: int) -> Optional[ObjectVariations]:
        """Récupère une variation par son identifiant."""
        return self.session.get(self.model, variation_id)

    def delete(self, variation_id: int) -> None:
        """Désactive une variation (soft delete via is_active=False)."""
        variation = self.get_by_id(variation_id)
        if not variation:
            raise ValueError(f"Variation avec id {variation_id} non trouvée.")
        variation.is_active = False
        try:
            self.session.flush()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la suppression de la variation : {str(e)}"
            ) from e

    def create(self, variation_data: Dict[str, Any]) -> ObjectVariations:
        """
        Crée un nouvel objet de type variation.
        Les champs attendus sont :
        - general_object_id (requis),
        - name (requis),
        - description, price, purchase_price, vat_rate_id, is_active, wpwc_id
        """
        # Levée d'une exception si des champs diffèrent des champs attendus pour une variation
        extra_keys = set(variation_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Création de la variation
        new_variation = ObjectVariations(**variation_data)
        try:
            self.session.add(new_variation)
            self.session.flush()
            return new_variation
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création de la variation : {str(e)}") from e

    def update(
        self,
        variation_data: Dict[str, Any],
        variation: Optional[ObjectVariations] = None,
        variation_id: Optional[int] = None,
    ) -> ObjectVariations:
        """
        Met à jour une variation existante avec les données fournies.
        Les champs pouvant être mis à jour pour une variation sont :
            - name,
            - description,
            - price,
            - purchase_price,
            - vat_rate_id,
            - is_active
        Raise:
            - ValueError: Si des champs diffèrent des champs attendus pour une variation
                          ou si aucun objet ou id de variation n'est fourni pour la mise à jour.
        """
        # Levée d'une exception si des champs diffèrent des champs attendus pour une variation
        # ou si aucun objet ou id de variation n'est fourni pour la mise à jour
        extra_keys = set(variation_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")
        if not variation and not variation_id:
            raise ValueError("Passer un objet ou un id pour la mise à jour de la variation")
        if not variation and variation_id:
            variation = self.session.get(ObjectVariations, variation_id)
            if not variation:
                raise ValueError(f"Variation avec id {variation_id} non trouvée")

        # Mise à jour de la variation
        for key, value in variation_data.items():
            setattr(variation, key, value)

        try:
            self.session.flush()
            return variation
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de la variation : {str(e)}"
            ) from e

    def save_from_form(
        self, form: Any, general_object_id: int, instance: Optional[ObjectVariations] = None
    ) -> ObjectVariations:
        """
        Met à jour une variation à partir des données d'un formulaire.
        Les champs pouvant être mis à jour pour une variation sont :
            - name,
            - description,
            - price,
            - purchase_price,
            - vat_rate_id,
            - is_active
        Args:
            - form: Formulaire contenant les données de la variation à mettre à jour.
            - general_object_id: ID de l'objet général associé à la variation.
            - instance: Instance de la variation à mettre à jour (optionnel, si None une
                nouvelle variation sera créée).
        Returns:
            - ObjectVariations: La variation mise à jour ou créée.
         Raises:
            - ValueError: Si des champs du formulaire diffèrent des champs attendus pour
                une variation.
        """
        if instance is None:
            instance = ObjectVariations()
            self.session.add(instance)
        instance.general_object_id = general_object_id
        instance.name = form.name.data or ""
        instance.description = form.description.data or ""
        instance.price = float(form.price.data or 0)
        purchase_price = form.purchase_price.data
        instance.purchase_price = float(purchase_price) if purchase_price else None
        vat_id = form.vat_rate_id.data
        instance.vat_rate_id = int(vat_id) if vat_id else None
        instance.is_active = bool(form.is_active.data)
        try:
            self.session.flush()
            return instance
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la sauvegarde de la variation : {str(e)}"
            ) from e
