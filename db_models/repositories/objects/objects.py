"""
Module pour les dépôts des objets vendus par la librairie. Contient les classes :
    - ObjectsRepository : Contient les méthodes pour interagir avec les données des objets
                          vendus par la librairie.
"""

from datetime import date, timedelta
from decimal import Decimal
from logging import getLogger
from typing import Any, Sequence, Optional
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import (
    GeneralObjects,
    Books,
    OtherObjects,
    ObjMetadatas,
    ObjectTags,
    MediaFiles,
    ObjectPrices,
)
from db_models.objects.vat import VatRate
from db_models.services.objects import sync_collection

logger = getLogger(__name__)


class ObjectsRepository(BaseRepository):
    """
    Dépôt de données pour les objets vendus par la librairie.
    Contient les méthodes :
    - get_all : pour récupérer tous les objets.
    - get_by_ref : pour récupérer un objet par une référence (id, ean13, etc.).
    - create : pour créer un nouvel objet.
    - update : pour mettre à jour un objet existant.
    - update_complete : pour mettre à jour un objet avec tous ses éléments liés
                        (books, other_objects, obj_metadata, object_tags, media).
    - delete : pour supprimer un objet (soft delete).
    """

    def __init__(self, *args: Any, **kwargs: str) -> None:
        """Initialise le dépôt de données pour les objets vendus par la librairie."""
        super().__init__(*args, **kwargs)
        self.model = GeneralObjects
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)
        # Importations locales pour casser l'import circulaire
        from .books import BooksRepository  # pylint: disable=import-outside-toplevel
        from .other_objects import OtherObjectsRepository  # pylint: disable=import-outside-toplevel
        from .obj_metadatas import ObjMetadatasRepository  # pylint: disable=import-outside-toplevel
        from .object_tags import ObjectTagsRepository  # pylint: disable=import-outside-toplevel
        from .media import MediaRepository  # pylint: disable=import-outside-toplevel
        from .prices import PricesRepository  # pylint: disable=import-outside-toplevel
        from .variations import VariationsRepository  # pylint: disable=import-outside-toplevel

        self.book_repo = BooksRepository(self.session)
        self.other_object_repo = OtherObjectsRepository(self.session)
        self.obj_metadata_repo = ObjMetadatasRepository(self.session)
        self.object_tags_repo = ObjectTagsRepository(self.session)
        self.media_repo = MediaRepository(self.session)
        self.price_repo = PricesRepository(self.session)
        self.variation_repo = VariationsRepository(self.session)

    def _get_global_select(self, only_actives: bool = False):
        """Retourne une requête de base pour les objets, avec tous les éléments liés."""
        stmt = select(self.model).options(
            joinedload(self.model.supplier),
            joinedload(self.model.book),
            joinedload(self.model.other_object),
            joinedload(self.model.inventory_movements),
            joinedload(self.model.obj_metadatas),
            joinedload(self.model.object_tags).joinedload(ObjectTags.tag),
            joinedload(self.model.media_files),
            joinedload(self.model.object_variations),
            joinedload(self.model.prices),
        )
        if only_actives:
            stmt = stmt.where(self.model.is_active == True)  # pylint: disable=singleton-comparison
        return stmt

    def get_all(self, only_actives: bool = False) -> Sequence["GeneralObjects"]:
        """
        Récupère les objets avec tous les éléments liés.
        Returns:
            List[GeneralObjects]: Une liste d'objets avec leurs éléments liés.
        """
        stmt = self._get_global_select(only_actives=only_actives)
        return self.session.execute(stmt).unique().scalars().all()

    def get_by_ref(self, reference: str | int, only_actives: bool = False) -> "GeneralObjects":
        """Récupère un objet par référence EAN13 ou par identifiant interne.

        Les chaînes sont traitées comme EAN13, tandis que les entiers sont traités
        comme identifiants SQL de l'objet. Cela évite de chercher un enregistrement
        par l'ID au lieu de l'EAN13 lorsqu'un EAN13 numérique est fourni sous forme de chaîne.
        """
        if isinstance(reference, str):
            stmt = self._get_global_select(only_actives=only_actives).where(
                self.model.ean13 == reference.strip()
            )
        elif isinstance(reference, int):
            stmt = self._get_global_select(only_actives=only_actives).where(
                self.model.id == reference
            )
        else:
            raise ValueError("Reference must be an integer id or a string ean13.")
        return self.session.execute(stmt).unique().scalar_one_or_none()

    def get_by_wpwc_id(self, wpwc_id: int) -> Optional["GeneralObjects"]:
        """Récupère un objet par son ID WooCommerce."""
        stmt = self._get_global_select().where(self.model.wpwc_id == wpwc_id)
        return self.session.execute(stmt).unique().scalar_one_or_none()

    def get_by_name(
        self,
        name: str,
        supplier_id: Optional[int] = None
    ) -> Sequence["GeneralObjects"]:
        """Récupère une liste d'objets dont le nom correspond à la recherche."""
        stmt = self._get_global_select().where(self.model.name.ilike(f"%{name.lower()}%"))
        if supplier_id is not None:
            stmt = stmt.where(self.model.supplier_id == supplier_id)
        stmt = stmt.order_by(self.model.name).limit(10)
        return self.session.execute(stmt).unique().scalars().all()

    def get_vat_rate(self, object_id: int) -> Optional[float]:
        """Récupère le taux de TVA du prix courant d'un objet à partir de son id."""
        stmt = (
            select(self.model)
            .where(self.model.id == object_id, self.model.is_active == True)  # pylint: disable=singleton-comparison
            .options(joinedload(self.model.prices))
        )
        obj = self.session.execute(stmt).unique().scalar_one_or_none()
        if obj is None:
            return None
        current_vat = obj.get_current_vat_rate()
        if current_vat is None:
            return None
        return current_vat

    def get_vat_rate_id(self, vat_rate: float) -> Optional[int]:
        """Récupère l'id d'un taux de TVA à partir de son taux."""
        stmt = select(VatRate).where(
            and_(
                VatRate.rate == Decimal(str(vat_rate)).quantize(Decimal("0.01")),
                or_(VatRate.date_end == None, VatRate.date_end > func.now()),  # pylint: disable=singleton-comparison, not-callable
            )
        )
        vat_rate_obj = self.session.execute(stmt).scalar_one_or_none()
        if vat_rate_obj:
            return vat_rate_obj.id
        return None

    def get_current_vat_rates(self) -> dict[float, int]:
        """Retourne le mapping des taux de TVA actuellement valides vers leur identifiant."""
        stmt = select(VatRate).where(
            or_(VatRate.date_end == None, VatRate.date_end > func.now())  # pylint: disable=singleton-comparison, not-callable
        )
        mapping: dict[float, int] = {}
        for vat_rate in self.session.execute(stmt).scalars().all():
            rounded_rate = float(Decimal(str(vat_rate.rate)).quantize(Decimal("0.01")))
            mapping[rounded_rate] = vat_rate.id
        return mapping

    def commit_object(self) -> None:
        """
        Commit les changements liés à un objet (création, mise à jour, suppression).
        En cas d'erreur lors du commit, la transaction est rollbackée et une exception est levée.
        """
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error committing object changes: {str(e)}") from e

    def delete(self, object_id: int):
        """Supprime un objet (soft delete)."""
        obj = self.get_by_ref(object_id)
        if not obj:
            raise ValueError(f"Object with id {object_id} not found.")
        obj.is_active = False
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error committing object changes: {str(e)}") from e

    def toggle_active(self, object_id: int) -> bool:
        """Bascule le statut actif/inactif d'un objet. Retourne le nouveau statut."""
        obj = self.get_by_ref(object_id)
        if not obj:
            raise ValueError(f"Object with id {object_id} not found.")
        obj.is_active = not obj.is_active
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error committing object changes: {str(e)}") from e
        return obj.is_active

    def save_from_form(
        self, form: Any, instance: Optional[GeneralObjects] = None
    ) -> int:
        """
        Sauvegarde un objet à partir d'un formulaire.
        Si instance est fourni, met à jour l'objet existant, sinon en crée un nouveau.
        """
        if instance is None:
            instance = GeneralObjects()
            self.session.add(instance)

        instance.supplier_id = int(form.supplier_id.data)
        instance.general_object_type = form.general_object_type.data
        instance.ean13 = form.ean_13.data
        instance.name = form.name.data
        instance.description = form.description.data
        instance.purchase_price = float(form.purchase_price.data) \
                                        if getattr(form, 'purchase_price', None) \
                                              and form.purchase_price.data \
                                        else None   # type: ignore
        self.session.flush()
        form.general_object_id.data = instance.id

        if form.general_object_type.data == "book":
            self.book_repo.save_from_form(
                form=form.book, general_object_id=instance.id, instance=instance.book
            )
        else:
            self.other_object_repo.save_from_form(
                general_object_id=instance.id,
                instance=instance.other_object,
            )
        self.obj_metadata_repo.save_from_form(
            form=form.obj_metadatas,
            general_object_id=instance.id,
            instance=instance.obj_metadatas if instance.obj_metadatas else None,
        )
        self._sync_price_history_from_form(instance, form.prices)
        self.object_tags_repo.save_from_form(
            form=form,
            general_object_id=instance.id,
            parent_instance=instance,
        )
        self.media_repo.save_from_form(
            form=form,
            general_object_id=instance.id,
            parent_instance=instance,
        )
        self.commit_object()
        return instance.id

    def _sync_price_history_from_form(
        self, instance: GeneralObjects, price_entries: Any
    ) -> None:
        """Synchronise l'historique des prix à partir du tableau du formulaire."""
        price_model = instance.__mapper__.relationships["prices"].mapper.class_
        sorted_entries = sorted(
            list(price_entries or []),
            key=lambda entry: (
                entry.form.from_date.data or date.min,
                entry.form.to_date.data or date.max,
            ),
        )
        sync_collection(
            parent=instance,
            general_object_id=instance.id,
            attr_name="prices",
            form_fieldlist=[entry.form for entry in sorted_entries],
            model_class=price_model,
            session=self.session,
        )

    def _set_current_price(
            self,
            instance: GeneralObjects,
            object_price: ObjectPrices,
        ) -> None:
        """Ajoute ou remplace le prix courant sans toucher aux autres périodes."""
        today = date.today()
        current_price = next((row for row in instance.prices if row.is_current), None)
        if current_price is not None:
            if (
                float(current_price.price or 0.0) == float(object_price.price)
                and (
                    object_price.vat_rate_id is None
                    or current_price.vat_rate_id == object_price.vat_rate_id
                )
            ):
                return
            if current_price.from_date == today and current_price.to_date is None:
                current_price.price = float(object_price.price)
                if object_price.vat_rate_id is not None:
                    current_price.vat_rate_id = object_price.vat_rate_id
                return
            current_price.to_date = today - timedelta(days=1)

        instance.prices.append(
            ObjectPrices(
                price=float(object_price.price),
                vat_rate_id=object_price.vat_rate_id,
                from_date=today,
                to_date=None,
            )
        )

    def save_or_update_from_object(
            self,
            general_object: GeneralObjects,
            other_object: Optional[OtherObjects] = None,
            book: Optional[Books] = None,
            obj_metadatas: Optional[ObjMetadatas] = None,
            object_tags: Optional[ObjectTags] = None,
            media_files: Optional[MediaFiles] = None,
            object_price: Optional[ObjectPrices] = None,
            ) -> int:
        """
        Sauvegarde un objet à partir d'une instance de GeneralObjects complète.
        Si l'objet a un id, met à jour l'objet existant, sinon en crée un nouveau.
        """
        normalized_ean = (
            str(general_object.ean13).strip() if general_object.ean13 is not None else None
        )
        if normalized_ean is not None:
            general_object.ean13 = normalized_ean

        # 1. Récupération éventuelle de l'objet existant
        instance = None
        if general_object.id is not None:
            instance = self.session.get(self.model, general_object.id)
        if instance is None and normalized_ean:
            instance = self.get_by_ref(normalized_ean, only_actives=False)
        if instance is None and normalized_ean:
            instance = self.session.execute(
                select(self.model).where(self.model.ean13 == normalized_ean)
            ).scalar_one_or_none()

        if instance is None:
            # 2. Création
            instance = GeneralObjects()
            for attr, value in vars(general_object).items():
                if attr not in ("id", "_sa_instance_state") and value is not None:
                    setattr(instance, attr, value)
            self.session.add(instance)
        else:
            # 3. Mise à jour : on copie les champs utiles
            for attr, value in vars(general_object).items():
                if attr not in ("id", "_sa_instance_state") and value is not None:
                    setattr(instance, attr, value)

        try:
            # 4. Flush pour obtenir instance.id si nouvel objet
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            if normalized_ean:
                instance = self.session.execute(
                    select(self.model).where(self.model.ean13 == normalized_ean)
                ).scalar_one_or_none()
                if instance is None:
                    raise
                for attr, value in vars(general_object).items():
                    if attr not in ("id", "_sa_instance_state") and value is not None:
                        setattr(instance, attr, value)
                self.session.flush()

        # 5. Assignation des relations (SQLAlchemy gère les FK)
        if book:
            instance.book = book

        if other_object:
            instance.other_object = other_object

        if obj_metadatas:
            instance.obj_metadatas = obj_metadatas

        if object_tags:
            instance.object_tags = object_tags

        if media_files:
            instance.media_files = media_files

        if object_price is not None:
            self._set_current_price(instance, object_price)

        logger.debug(
            "[ObjectsRepository] objet avant commit: ean13=%s, name=%s, description=%s, book=%s, obj_metadatas=%s, prices=%s, object_price=%s, vat_rate_id=%s",
            getattr(instance, "ean13", None),
            getattr(instance, "name", None),
            getattr(instance, "description", None),
            getattr(instance, "book", None),
            getattr(instance, "obj_metadatas", None),
            getattr(instance, "prices", None),
            object_price,
            getattr(object_price, "vat_rate_id", None),
        )

        # 6. Retour verse l'appelant (id de l'objet créé ou mis à jour)
        return instance.id
