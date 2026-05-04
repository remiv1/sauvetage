"""Dépôt pour les opérations liées aux références Dilicom."""

import logging
from typing import Optional, Any, Dict
from sqlalchemy import select, and_
from db_models.objects import DilicomReferencial
from db_models.repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class DilicomReferencialRepository(BaseRepository):
    """
    Dépôt de fonctions de gestion des références Dilicom utilisées par les
    routes du blueprint stock.
    """

    def _get_select(
        self,
        to_create: Optional[bool] = None,
        created: Optional[bool] = None,
        to_delete: Optional[bool] = None,
        deleted: Optional[bool] = None,
    ) -> Any:
        """Construit une requête SQLAlchemy pour filtrer les références Dilicom en fonction
        des critères de création/suppression.

        Args:
            to_create: Si True, filtre les références à créer (create_ref=True).
            created: Si True, filtre les références déjà créées (create_ref=True).
            to_delete: Si True, filtre les références à supprimer (delete_ref=True).
            deleted: Si True, filtre les références déjà supprimées (delete_ref=True).
        """
        stmt = select(DilicomReferencial)
        where_clauses = []
        if to_create is True:
            where_clauses.append(
                DilicomReferencial.create_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == False  # pylint: disable=singleton-comparison
            )
        if created is True:
            where_clauses.append(
                DilicomReferencial.create_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == True  # pylint: disable=singleton-comparison
            )
        if to_delete is True:
            where_clauses.append(
                DilicomReferencial.delete_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == False  # pylint: disable=singleton-comparison
            )
        if deleted is True:
            where_clauses.append(
                DilicomReferencial.delete_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == True  # pylint: disable=singleton-comparison
            )
        if where_clauses:
            stmt = stmt.where(and_(*where_clauses))
        return stmt

    def _get_status(self, row: DilicomReferencial) -> str:
        """
        Détermine le statut d'une référence Dilicom à partir de ses champs de création
        et de suppression.
        Args:
            row: L'instance de `DilicomReferencial` dont on veut déterminer le statut.
        Returns:
            Le statut de la référence, qui peut être "to_create", "created", "to_delete" ou "deleted".
        Raises:
            ValueError: Si le statut de la référence ne correspond à aucun des cas attendus.
        """
        if row.create_ref and not row.dilicom_synced:
            return "to_create"
        elif row.create_ref and row.dilicom_synced:
            return "created"
        elif row.delete_ref and not row.dilicom_synced:
            return "to_delete"
        elif row.delete_ref and row.dilicom_synced:
            return "deleted"
        else:
            raise ValueError("Statut inconnu pour la référence Dilicom.")

    def _update_status(self, status: str) -> Dict[str, bool]:
        """Met à jour les champs de statut d'une référence Dilicom en fonction du statut
        cible.

        Args:
            status: Le statut cible (to_create, created, to_delete, deleted).

        Returns:
            Un dictionnaire avec les clés `create_ref`, `delete_ref`, `dilicom_synced`
            indiquant les valeurs à appliquer pour chaque champ.
        """
        if status == "to_create":
            return {"create_ref": True, "delete_ref": False, "dilicom_synced": False}
        elif status == "created":
            return {"create_ref": True, "delete_ref": False, "dilicom_synced": True}
        elif status == "to_delete":
            return {"create_ref": False, "delete_ref": True, "dilicom_synced": False}
        elif status == "deleted":
            return {"create_ref": False, "delete_ref": True, "dilicom_synced": True}
        else:
            raise ValueError(f"Statut inconnu : {status}")

    def get_last_by_ean13(self, ean13: str) -> Optional[DilicomReferencial]:
        """Récupère une référence Dilicom à partir de son EAN13.

        Args:
            ean13: L'EAN13 de la référence à récupérer.

        Returns:
            Une instance de `DilicomReferencial` si la référence existe, sinon None.
        """
        stmt = select(DilicomReferencial) \
                .where(DilicomReferencial.ean13 == ean13) \
                .order_by(DilicomReferencial.created_at.desc()) \
                .limit(1)
        result = self.session.execute(stmt).scalar_one_or_none()
        return result

    def create_status(
        self, ean13: str, gln13: str, movement: str
    ) -> DilicomReferencial:
        """Crée une nouvelle référence Dilicom en base.

        Args:
            ean13: L'EAN13 de l'objet à référencer.
            gln13: Le GLN13 du point de vente.
            movement: Le type de mouvement (to_create, created, to_delete, deleted).

        Returns:
            L'instance de `DilicomReferencial` créée.

        Raises:
            ValueError: Si le type de mouvement est inconnu.
            RuntimeError: En cas d'erreur lors du commit.
        """
        status_fields = self._update_status(movement)
        ref = self.get_last_by_ean13(ean13)
        if not ref:
            ref = DilicomReferencial(ean13=ean13, gln13=gln13)
        for field, value in status_fields.items():
            setattr(ref, field, value)
        self.session.add(ref)
        try:
            self.session.commit()
            logger.info(
                "Référence Dilicom créée avec succès : EAN13=%s, GLN13=%s, Movement=%s",
                ean13,
                gln13,
                movement,
            )
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la création de la référence Dilicom : {exc}"
            raise RuntimeError(message) from exc

        return ref

    def update_status(self, ean13: str) -> DilicomReferencial:
        """Met à jour le statut d'une référence Dilicom existante.

        Args:
            ean13: L'EAN13 de la référence à mettre à jour.

        Returns:
            L'instance de `DilicomReferencial` mise à jour.

        Raises:
            ValueError: Si le type de mouvement est inconnu ou si la référence n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        row = self.get_last_by_ean13(ean13)
        if not row:
            raise ValueError(f"Aucune référence Dilicom trouvée pour l'EAN13 : {ean13}")
        movement = self._get_status(row)
        if movement == "to_create":
            next_movement = "created"
        elif movement == "to_delete":
            next_movement = "deleted"
        else:
            raise ValueError(f"Statut de mouvement inconnu pour mise à jour : {movement}")
        row.dilicom_synced = True
        new_row = self.create_status(ean13=ean13, gln13=row.gln13, movement=next_movement)
        self.session.add(new_row)
        try:
            self.session.commit()
            logger.info(
                "Référence Dilicom MàJ avec succès : ID=%s, EAN13=%s, GLN13=%s, Movement=%s",
                new_row.id,
                ean13,
                row.gln13,
                next_movement,
            )
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la mise à jour de la référence Dilicom : {exc}"
            raise RuntimeError(message) from exc
        return new_row
