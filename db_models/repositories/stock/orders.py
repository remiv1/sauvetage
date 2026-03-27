"""Dépôt pour les opérations liées aux commandes fournisseurs et leurs lignes."""

from decimal import Decimal
from typing import Sequence
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from db_models.objects import (
    GeneralObjects,
    InventoryMovements,
    OrderIn,
    OrderInLine,
)
from db_models.repositories.base_repo import BaseRepository


class OrderRepository(BaseRepository):
    """Dépôt pour le CRUD et le workflow des commandes fournisseurs."""

    # ── Utilitaires internes ──────────────────────────────────────────────

    def _compensate_inventory_movements(self, movement_ids: set, order_id: int) -> None:
        """Crée des mouvements de compensation inverse pour annuler les mouvements d'inventaire
        liés à une commande annulée.

        Args:
            movement_ids: Ensemble des IDs des mouvements d'inventaire à compenser.
            order_id: L'identifiant de la commande annulée (pour les notes du mouvement).
        """
        inventory_movements = self.session.execute(
            select(InventoryMovements).where(InventoryMovements.id.in_(movement_ids))
        ).scalars().all()
        for movement in inventory_movements:
            note = f"Compensation du mouvement #{movement.id} lié à la commande annulée #{order_id}"
            source = f"Compensation annulation commande #{order_id}"
            compensation = InventoryMovements(
                general_object_id=movement.general_object_id,
                movement_type="in" if movement.movement_type == "out" else "out",
                quantity=movement.quantity * -1,
                price_at_movement=movement.price_at_movement,
                source=source,
                destination=movement.destination,
                notes=note,
            )
            self.session.add(compensation)

    def _check_order_completion(self, order_id: int) -> None:
        """Vérifie si toutes les lignes d'une commande sont finalisées
        et met à jour l'état de la commande en conséquence.

        - Si toutes les lignes sont 'received' → order_state = 'received'
        - Si toutes les lignes sont 'cancelled' → order_state = 'cancelled'
        """
        order = self.get_order_by_id(order_id)
        if not order.orderin_lines:
            return

        states = {line.line_state for line in order.orderin_lines}

        if states == {"received"}:
            order.order_state = "received"
        elif states == {"cancelled"}:
            order.order_state = "cancelled"
        elif "pending" not in states and states <= {"received", "cancelled"}:
            order.order_state = "received"
        else:
            return

        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(
                f"Erreur lors de la mise à jour de l'état de la commande : {exc}"
            ) from exc

    # ── Lecture ────────────────────────────────────────────────────────────

    def get_supplier_orders(
        self, out: bool = False, reservation: bool = False
    ) -> Sequence[OrderIn]:
        """Récupère la liste des commandes fournisseurs avec toutes les relations chargées.

        Charge les fournisseurs et les lignes de commande de manière eager pour éviter
        le lazy loading.

        Args:
            out: True pour les retours fournisseur (RET-).
            reservation: True pour les réservations (RES-).

        Returns:
            Sequence[OrderIn]: Liste des commandes avec relations complètement chargées.
        """
        if reservation:
            prefix = "RES-"
        elif out:
            prefix = "RET-"
        else:
            prefix = "CMD-"
        stmt = (
            select(OrderIn)
            .options(
                selectinload(OrderIn.supplier), selectinload(OrderIn.orderin_lines)
            )
            .where(OrderIn.order_ref.startswith(prefix))
            .order_by(OrderIn.id.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_order_by_id(self, order_id: int) -> OrderIn:
        """Récupère les détails d'une commande fournisseur à partir de son ID.

        Charge le fournisseur et les lignes de commande de manière eager.

        Args:
            order_id: L'identifiant de la commande à récupérer.

        Returns:
            L'objet OrderIn avec toutes les relations chargées.

        Raises:
            ValueError: Si la commande n'existe pas.
        """
        stmt = (
            select(OrderIn)
            .options(
                selectinload(OrderIn.supplier),
                selectinload(OrderIn.orderin_lines).selectinload(
                    OrderInLine.general_object
                ),
            )
            .where(OrderIn.id == order_id)
        )

        result = self.session.execute(stmt).scalar_one_or_none()
        if result is None:
            raise ValueError(f"Commande {order_id} introuvable")
        return result

    # ── CRUD commandes ────────────────────────────────────────────────────

    def edit_order_in_db(
        self, order_in: OrderIn, action: str = "create",
        out: bool = False, reservation: bool = False
    ) -> int:
        """Crée/ modifie une commande fournisseur en base à partir des données du formulaire.

        Args:
            order_in: L'objet OrderIn contenant les données de la commande à créer ou modifier.
            action: "create" pour une nouvelle commande, "edit" pour une modification.
            out: True si c'est un retour fournisseur (quantité négative), False pour une commande.
            reservation: True pour créer une réservation (RES-).

        Returns:
            L'ID de la commande créée/modifiée.
        """
        # Gestion de l'opération de création de commande
        if action == "create":
            self.session.add(order_in)
            self.session.flush()
            if reservation:
                ref = f"RES-{order_in.id:06d}"
            elif out is True:
                ref = f"RET-{order_in.id:06d}"
            else:
                ref = f"CMD-{order_in.id:06d}"
            order_in.order_ref = ref
            order_in.order_state = "draft"

        # Gestion de l'opération de modification de commande
        elif action == "edit":
            existing_order = self.session.get(OrderIn, order_in.id)
            if existing_order is None:
                raise ValueError(f"Commande {order_in.id} introuvable")
            existing_order.supplier_id = order_in.supplier_id
            existing_order.supplier_id = order_in.supplier_id
            existing_order.order_ref = order_in.order_ref
            existing_order.external_ref = order_in.external_ref
            existing_order.orderin_lines = order_in.orderin_lines
            existing_order.order_state = order_in.order_state
            existing_order.value = order_in.value

        # Gestion de l'action inconnue
        else:
            raise ValueError(f"Action inconnue : {action}")

        # Commit de la transaction avec gestion des erreurs
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la création/modification de la commande : {exc}"
            raise RuntimeError(message) from exc

        return order_in.id

    def cancel_supplier_order(
        self, order_id: int, reservation: bool = False
    ) -> None:
        """
        Supprime une commande fournisseur (ou réservation) et ses lignes associées
        et compense les mouvements d'inventaire liés.

        Args:
            order_id: L'identifiant de la commande à annuler.
            reservation: True pour supprimer une réservation (vérifie l'état brouillon).

        Raises:
            ValueError: Si la commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        label = "Réservation" if reservation else "Commande"
        order = self.session.get(OrderIn, order_id)
        if order is None:
            raise ValueError(f"{label} {order_id} introuvable")

        if reservation:
            if not order.order_ref.startswith("RES-"):
                raise ValueError(f"La commande {order_id} n'est pas une réservation")
            if order.order_state != "draft":
                raise ValueError(
                    f"Seules les réservations à l'état brouillon peuvent être supprimées "
                    f"(état actuel : {order.order_state})"
                )

        # Chargement ORM des lignes pour passer par les relations SQLAlchemy
        lines = (
            self.session.execute(
                select(OrderInLine).where(OrderInLine.order_in_id == order_id)
            )
            .scalars()
            .all()
        )

        # Suppression des lignes et déliaison des mouvements d'inventaire associés
        lines_to_compensate: set = set()
        for line in lines:
            lines_to_compensate.add(line.inventory_movement_id)
            line.inventory_movement_id = None  # type: ignore
            self.session.delete(line)

        # Création des mouvements de compensation pour annuler l'impact sur le stock
        self._compensate_inventory_movements(lines_to_compensate, order_id)

        # Flush pour propager les changements sur les lignes avant de supprimer la commande
        self.session.flush()
        self.session.delete(order)

        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise RuntimeError(
                f"Erreur lors de l'annulation de la commande : {exc}"
            ) from exc

    def update_order_in_price(self, order_id: int) -> None:
        """Met à jour le prix total d'une commande fournisseur en recalculant le total
        à partir des lignes de commande.

        Args:
            order_id: L'identifiant de la commande à mettre à jour.

        Raises:
            ValueError: Si la commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        order = self.session.get(OrderIn, order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")
        stmt = select(
            func.coalesce(
                func.sum(
                    OrderInLine.qty_ordered
                    * OrderInLine.unit_price
                    * (1 + OrderInLine.vat_rate / 100)
                ),
                0,
            ).label("total_ttc")
        ).where(OrderInLine.order_in_id == order_id)
        total_ttc = self.session.execute(stmt).scalar_one()
        print(f"DEBUG Calculated total TTC for order {order_id}: {total_ttc}")  # Debug log
        order.value = float(total_ttc)
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            message = f"Erreur lors de la mise à jour du prix de la commande : {exc}"
            raise SQLAlchemyError(message) from exc

    def update_order_external_ref(self, order_id: int, external_ref: str) -> None:
        """Met à jour la référence externe d'une commande fournisseur.

        Args:
            order_id: L'identifiant de la commande.
            external_ref: La référence externe du fournisseur.

        Raises:
            ValueError: Si la commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        order = self.session.get(OrderIn, order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")
        order.external_ref = external_ref if external_ref else ""
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(
                f"Erreur lors de la mise à jour de la réf. externe : {exc}"
            ) from exc

    # ── CRUD lignes de commande ───────────────────────────────────────────

    def edit_order_in_line_db(
            self, new_line: OrderInLine,
            action: str = "edit",
            out: bool = False,
            reservation: bool = False,
        ) -> int:
        """
        Modifie/crée une ligne de commande fournisseur en base à partir des données du formulaire.
        Gère également la création ou la mise à jour du mouvement d'inventaire associé.
        Args:
            new_line: L'objet OrderInLine contenant les données de la ligne à créer ou modifier.
            action: "create" pour une nouvelle ligne, "edit" pour une modification.
            out: True si c'est un retour fournisseur (quantité négative), False pour une commande.
            reservation: True pour une ligne de réservation (mouvement 'reserved', prix auto).
        """
        # Gestion de l'opération de création
        if action == "create":
            if reservation:
                obj = self.session.get(GeneralObjects, new_line.general_object_id)
                if obj is None:
                    raise ValueError(f"Objet {new_line.general_object_id} introuvable")
                order = self.session.get(OrderIn, new_line.order_in_id)
                if order is None:
                    raise ValueError(f"Réservation {new_line.order_in_id} introuvable")
                price = float(obj.purchase_price) if obj.purchase_price else 0.0
                source = "stock"
                destination = "reserve"
                movement_type = "reserved"
                notes = f"Réservation {order.order_ref} — objet #{new_line.general_object_id}"
                new_line.unit_price = price
            elif out is True:
                price = float(new_line.unit_price)
                source = f"Retour fournisseur #{new_line.order_in_id}"
                notes = f"Retour fournisseur #{new_line.order_in_id}" \
                       + f" - Ligne #{new_line.general_object_id}"
                destination = "Fournisseur"
                movement_type = "out"
            else:
                price = float(new_line.unit_price)
                source = f"Commande fournisseur #{new_line.order_in_id}"
                notes = f"Commande fournisseur #{new_line.order_in_id}" \
                       + f" - Ligne #{new_line.general_object_id}"
                destination = "Stock"
                movement_type = "in"
            movement = InventoryMovements(
                general_object_id=new_line.general_object_id,
                movement_type=movement_type,
                quantity=new_line.qty_ordered,
                price_at_movement=Decimal(str(price)),
                source=source,
                destination=destination,
                notes=notes,
            )
            self.session.add(movement)
            self.session.flush()
            new_line.inventory_movement_id = movement.id
            self.session.add(new_line)

        # Gestion de l'opération d'édition
        elif action == "edit":
            existing_line = self.session.get(OrderInLine, new_line.id)
            if existing_line is None:
                raise ValueError(f"Ligne de commande {new_line.id} introuvable")
            existing_movement = self.session.get(
                InventoryMovements, existing_line.inventory_movement_id
            )
            if existing_movement is None:
                raise ValueError(
                    f"Mouvement d'inventaire {existing_line.inventory_movement_id} introuvable"
                )
            existing_line.general_object_id = new_line.general_object_id
            existing_line.qty_ordered = new_line.qty_ordered
            existing_line.unit_price = new_line.unit_price
            existing_line.vat_rate = new_line.vat_rate

            existing_movement.general_object_id = new_line.general_object_id
            existing_movement.quantity = new_line.qty_ordered
            existing_movement.price_at_movement = new_line.unit_price

        else:
            raise ValueError(f"Action inconnue : {action}")
        try:
            self.session.commit()
            return new_line.id
        except SQLAlchemyError as exc:
            self.session.rollback()
            message = f"Erreur lors de la modification/création de la ligne de commande : {exc}"
            raise RuntimeError(message) from exc

    def delete_order_in_line_db(self, line_id: int) -> int:
        """Supprime une ligne de commande fournisseur en base.

        Args:
            line_id: L'identifiant de la ligne de commande à supprimer.

        Raises:
            ValueError: Si la ligne de commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        line = self.session.get(OrderInLine, line_id)
        if line is None:
            raise ValueError(f"Ligne de commande {line_id} introuvable")

        self.session.delete(line)

        try:
            self.session.commit()
            return line_id
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la suppression de la ligne de commande : {exc}"
            raise RuntimeError(message) from exc

    # ── Workflow de réception ──────────────────────────────────────────────

    def confirm_order(self, order_id: int) -> OrderIn:
        """Passe une commande de l'état 'draft' à 'sended'.

        Args:
            order_id: L'identifiant de la commande à confirmer.

        Returns:
            L'objet OrderIn mis à jour.

        Raises:
            ValueError: Si la commande n'existe pas ou n'est pas en état 'draft'.
            RuntimeError: En cas d'erreur lors du commit.
        """
        order = self.get_order_by_id(order_id)
        if order.order_state != "draft":
            raise ValueError(
                f"La commande {order_id} n'est pas en état 'draft' "
                f"(état actuel : {order.order_state})"
            )
        if not order.orderin_lines:
            raise ValueError(
                f"La commande {order_id} ne contient aucune ligne."
            )
        order.order_state = "sended"
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(
                f"Erreur lors de la confirmation de la commande : {exc}"
            ) from exc
        return order

    def receive_order_line(
        self, line_id: int, qty_received: int, qty_cancelled: int
    ) -> int:
        """Traite la réception d'une ligne de commande avec split possible.

        Logique de compensation des mouvements d'inventaire :
        - Le mouvement 'pending' original est compensé par un mouvement inverse 'pending'.
        - Un mouvement 'in' est créé pour la quantité reçue.
        - Si une quantité reste en attente, un nouveau mouvement 'pending' est créé pour le reste.

        Split des lignes :
        - La ligne originale est mise à jour avec la quantité reçue.
        - Si une quantité est annulée, une nouvelle ligne 'cancelled' est créée.
        - Si une quantité reste en attente, une nouvelle ligne 'pending' est créée.

        Args:
            line_id: L'identifiant de la ligne de commande.
            qty_received: La quantité reçue.
            qty_cancelled: La quantité annulée.

        Returns:
            L'ID de la commande parente.

        Raises:
            ValueError: Si la ligne n'existe pas, n'est pas pending, ou si les quantités sont
                        incohérentes.
            RuntimeError: En cas d'erreur lors du commit.
        """
        line = self.session.get(OrderInLine, line_id)
        if line is None:
            raise ValueError(f"Ligne de commande {line_id} introuvable")
        if line.line_state != "pending":
            raise ValueError(
                f"La ligne {line_id} n'est pas en état 'pending' "
                f"(état actuel : {line.line_state})"
            )

        qty_remaining = line.qty_ordered - qty_received - qty_cancelled
        if qty_remaining < 0:
            raise ValueError(
                f"La somme des quantités (reçues={qty_received} + annulées={qty_cancelled}) "
                f"dépasse la quantité commandée ({line.qty_ordered})."
            )

        order_id = line.order_in_id

        # ── Compensation du mouvement original via la méthode existante ──
        if line.inventory_movement_id is not None:
            self._compensate_inventory_movements(
                {line.inventory_movement_id}, order_id
            )
            self.session.flush()

        # ── Mouvement 'in' pour la quantité reçue ──
        if qty_received > 0:
            movement_in = InventoryMovements(
                general_object_id=line.general_object_id,
                movement_type="in",
                quantity=qty_received,
                price_at_movement=float(line.unit_price),
                source=f"Réception commande #{order_id}",
                destination="Stock",
                notes=f"Réception de {qty_received} unité(s) "
                      f"pour la ligne #{line_id} de la commande #{order_id}",
            )
            self.session.add(movement_in)
            self.session.flush()

            # Mise à jour de la ligne originale → received
            line.qty_received = qty_received
            line.line_state = "received"
            line.inventory_movement_id = movement_in.id

        # ── Mouvement 'pending' de compensation pour annulation ──
        # (le mouvement pending original a déjà été compensé en totalité,
        #  pas besoin de mouvement supplémentaire pour la partie annulée)

        # ── Ligne 'cancelled' pour la quantité annulée ──
        if qty_cancelled > 0:
            cancelled_line = OrderInLine(
                order_in_id=order_id,
                general_object_id=line.general_object_id,
                inventory_movement_id=None,
                qty_ordered=qty_cancelled,
                qty_received=0,
                unit_price=line.unit_price,
                vat_rate=line.vat_rate,
                line_state="cancelled",
            )
            self.session.add(cancelled_line)

        # ── Nouveau mouvement 'pending' + ligne pour le reste en attente ──
        if qty_remaining > 0:
            movement_pending = InventoryMovements(
                general_object_id=line.general_object_id,
                movement_type="pending",
                quantity=qty_remaining,
                price_at_movement=float(line.unit_price),
                source=f"Commande fournisseur #{order_id}",
                destination="Stock",
                notes=f"Reste en attente ({qty_remaining} unité(s)) "
                      f"pour la ligne #{line_id} de la commande #{order_id}",
            )
            self.session.add(movement_pending)
            self.session.flush()

            pending_line = OrderInLine(
                order_in_id=order_id,
                general_object_id=line.general_object_id,
                inventory_movement_id=movement_pending.id,
                qty_ordered=qty_remaining,
                qty_received=0,
                unit_price=line.unit_price,
                vat_rate=line.vat_rate,
                line_state="pending",
            )
            self.session.add(pending_line)

        # Si rien n'a été reçu (tout annulé ou reste en attente), marquer la ligne en conséquence
        if qty_received == 0 and qty_cancelled > 0 and qty_remaining == 0:
            line.line_state = "cancelled"
            line.inventory_movement_id = None  # type: ignore

        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(
                f"Erreur lors de la réception de la ligne : {exc}"
            ) from exc

        # Vérifier si toutes les lignes sont finalisées pour mettre à jour l'état de la commande
        self._check_order_completion(order_id)

        return order_id

    # ── Réservations ───────────────────────────────────────────────────────

    def return_reservation(self, order_id: int) -> None:
        """Retourne (clôture) une réservation : crée des mouvements inverses pour chaque ligne.

        Pour chaque ligne, duplique le mouvement d'inventaire avec :
        - quantity = -quantity (inverse)
        - source et destination inversées

        Puis passe la commande et toutes ses lignes à l'état 'received'.

        Args:
            order_id: L'identifiant de la réservation à retourner.
        """
        order = self.get_order_by_id(order_id)
        if not order.order_ref.startswith("RES-"):
            raise ValueError(f"La commande {order_id} n'est pas une réservation")
        if order.order_state not in ("draft", "sended"):
            raise ValueError(
                f"La réservation {order_id} ne peut pas être retournée "
                f"(état actuel : {order.order_state})"
            )

        for line in order.orderin_lines:
            if line.line_state != "pending":
                continue
            if line.inventory_movement_id is None:
                continue

            original = self.session.get(InventoryMovements, line.inventory_movement_id)
            if original is None:
                continue

            inverse = InventoryMovements(
                general_object_id=original.general_object_id,
                movement_type="reserved",
                quantity=-original.quantity,
                price_at_movement=original.price_at_movement,
                source=original.destination,
                destination=original.source,
                notes=f"Retour réservation {order.order_ref} — mouvement #{original.id}",
            )
            self.session.add(inverse)

            line.line_state = "received"
            line.qty_received = line.qty_ordered

        order.order_state = "received"

        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(
                f"Erreur lors du retour de la réservation : {exc}"
            ) from exc
