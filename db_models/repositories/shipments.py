"""
Module pour la gestion des expéditions. Contient la classe ShipmentsRepository qui gère les
opérations liées aux expéditions, telles que la création, la récupération, la mise à jour et la
suppression des expéditions dans la base de données.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Shipment


class ShipmentsRepository(BaseRepository):
    """
    Repository pour les opérations sur les expéditions.
    Comprend les méthodes suivantes :
    - get_by_id : Récupère une expédition par son identifiant.
    - create_shipment : Crée une nouvelle expédition.
    - update_shipment : Met à jour une expédition existante.
    """

    def get_by_id(self, shipment_id: int) -> "Shipment | None":
        """Récupère une expédition par son identifiant.
        Args:
            shipment_id (int): L'identifiant de l'expédition à récupérer.
        Returns:
            Shipment | None: L'expédition correspondant à l'identifiant,
                             ou None s'il n'existe pas.
        """
        stmt = select(Shipment).where(Shipment.id == shipment_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_shipment(
        self, *, reference: str, carrier: str, tracking_number: str, create_source: str
    ) -> "Shipment":
        """Crée une nouvelle expédition.
        Args:
            reference (str): La référence de l'expédition.
            carrier (str): Le transporteur de l'expédition.
            tracking_number (str): Le numéro de suivi de l'expédition.
            create_source (str): La source de création de l'expédition.
        Returns:
            Shipment: L'expédition créée mais pas encore commité en base de données.
        """
        shipment = Shipment(
            reference=reference,
            carrier=carrier,
            tracking_number=tracking_number,
            create_source=create_source,
        )
        try:
            self.session.add(shipment)
            self.session.commit()
            return shipment
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de l'expédition : {e.orig}"
            ) from e

    def update_shipment(
        self,
        shipment: Shipment,
        *,
        reference: str | None = None,
        carrier: str | None = None,
        tracking_number: str | None = None,
        update_source: str | None = None,
    ) -> "Shipment":
        """Met à jour les informations d'une expédition existante.
        Args:
            shipment (Shipment): L'expédition à mettre à jour.
            reference (str | None): La nouvelle référence de l'expédition (optionnel).
            carrier (str | None): Le nouveau transporteur de l'expédition (optionnel).
            tracking_number (str | None): Le nouveau numéro de suivi de l'expédition (optionnel).
            update_source (str | None): La source de la mise à jour de l'expédition (optionnel).
        Returns:
            Shipment: L'expédition mise à jour mais pas encore commité en base de données.
        """
        if reference is not None:
            shipment.reference = reference
        if carrier is not None:
            shipment.carrier = carrier
        if tracking_number is not None:
            shipment.tracking_number = tracking_number
        if update_source is not None:
            shipment.update_source = update_source
        try:
            self.session.commit()
            return shipment
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de l'expédition : {e.orig}"
            ) from e
