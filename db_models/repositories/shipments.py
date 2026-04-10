"""Module pour la gestion des expéditions."""

from datetime import datetime, timezone
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Shipment, ShipmentLine


class ShipmentsRepository(BaseRepository):
    """Repository pour les opérations sur les expéditions."""

    def generate_reference(self) -> str:
        """
        Génère une référence unique au format ENV-YYMM-00001.
        La référence est basée sur la date de création et un compteur incrémental.
        Returns:
            str: La référence générée.
        """
        now = datetime.now(timezone.utc)
        yymm = now.strftime("%y%m")
        pattern = f"ENV-{yymm}-%"
        last_ref = self.session.execute(
            select(Shipment.reference)
            .where(Shipment.reference.like(pattern))
            .order_by(Shipment.reference.desc())
            .limit(1)
        ).scalar()
        if last_ref:
            last_num = int(last_ref.split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        return f"ENV-{yymm}-{next_num:05d}"

    def get_by_id(self, shipment_id: int) -> "Shipment | None":
        """
        Récupère une expédition par son identifiant.
        Args:
            shipment_id: L'identifiant de l'expédition à récupérer.
        Returns:
            Shipment | None: L'expédition correspondant à l'identifiant, ou None s'il n'existe pas.
        """
        stmt = (
            select(Shipment)
            .where(Shipment.id == shipment_id)
            .options(selectinload(Shipment.lines))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_order_id(self, order_id: int) -> list[Shipment]:
        """
        Récupère toutes les expéditions d'une commande.
        Args:
            order_id: L'identifiant de la commande.
        Returns:
            list[Shipment]: Liste des expéditions correspondant à la commande.
        """
        stmt = (
            select(Shipment)
            .where(Shipment.order_id == order_id)
            .options(selectinload(Shipment.lines))
            .order_by(Shipment.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def create_shipment(    # pylint: disable=too-many-arguments
        self,
        *,
        order_id: int,
        carrier: str,
        tracking_number: str | None,
        line_items: List[ShipmentLine],
        create_source: str = "web",
    ) -> "Shipment":
        """Crée une expédition avec ses lignes.
        Args:
            order_id: ID de la commande parente.
            carrier: Transporteur.
            tracking_number: Numéro de suivi.
            line_items: Liste de ShipmentLine.
            create_source: Source de création.
        Returns:
            Shipment créée.
        """
        shipment = Shipment(
            order_id=order_id,
            reference=self.generate_reference(),
            carrier=carrier,
            tracking_number=tracking_number,
            create_source=create_source,
        )
        try:
            self.session.add(shipment)
            self.session.flush()

            for line in line_items:
                line.shipment_id = shipment.id
                self.session.add(line)

            self.session.commit()
            return shipment
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de l'expédition : {e.orig}"
            ) from e
