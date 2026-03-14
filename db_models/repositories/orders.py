"""
Module pour la gestion des commandes. Contient la classe OrdersRepository qui gère
les interactions avec la base de données pour les commandes, notamment la création, la
mise à jour, la suppression et la récupération des commandes.
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Order, OrderLine

class OrdersRepository(BaseRepository):
    """Dépôt de données pour les commandes. Contient les méthodes pour interagir avec les
    données des commandes, notamment la création, la mise à jour, la suppression et la
    récupération des commandes."""

    def get_by_id(self, order_id: int) -> Order | None:
        """Récupère une commande par son identifiant.
        Args:
            order_id (int): L'identifiant de la commande à récupérer.
        Returns:
            Order | None: La commande correspondant à l'identifiant, ou None s'il n'existe pas.
        """
        stmt = select(Order).where(Order.id == order_id) \
                            .options(selectinload(Order.order_lines),
                                     joinedload(Order.invoice_address),
                                     joinedload(Order.delivery_address),
                                     joinedload(Order.customer),
                                     selectinload(Order.invoices),
                                     selectinload(Order.shipments))
        order = self.session.execute(stmt).scalar_one_or_none()
        return order

    def cut_line_for_invoice(self, order_line: OrderLine, invoiced_quantity: int) -> bool:
        """Crée une nouvelle ligne de commande à partir d'une ligne de commande existante,
        en ajustant les quantités et les montants pour correspondre à la quantité facturée.
        Args:
            order_line (OrderLine): La ligne de commande à couper.
        Returns:
            bool: True si la ligne a été coupée avec succès.
        """
        # La quantité facturée doit être inférieure à la quantité commandée
        if order_line.quantity_invoiced >= order_line.quantity:
            raise ValueError("La quantité facturée doit être inférieure à la quantité commandée.")

        # Création de la nouvelle ligne de commande avec les quantités et montants ajustés
        new_line = OrderLine(
            order_id=order_line.order_id,
            general_object_id=order_line.general_object_id,
            quantity=order_line.quantity - invoiced_quantity,
            unit_price=order_line.unit_price,
            vat_rate=order_line.vat_rate,
            update_source="cut_line_for_invoice",
        )

        # Mise à jour de la ligne de commande existante pour refléter la quantité facturée
        order_line.quantity = invoiced_quantity

        # Enregistrement des changements en base de données
        try:
            self.session.add(new_line)
            self.session.merge(order_line)
            self.session.commit()
            return True

        # En cas d'erreur, rollback de la transaction et levée d'une exception
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la coupure de la ligne de commande : {str(e)}") from e
