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


class ObjectsRepository(BaseRepository):    # pylint: disable=R0902
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

    def get_by_name_or_ean(
        self,
        query: str,
        supplier_id: Optional[int] = None,
    ) -> Sequence["GeneralObjects"]:
        """Recherche des objets par EAN13 exact ou par nom.

        Une saisie composée de treize chiffres est considérée comme un EAN13.
        Toute autre saisie conserve la recherche partielle par nom.
        """
        normalized_query = query.strip()
        if len(normalized_query) == 13 and normalized_query.isdigit():
            stmt = self._get_global_select().where(
                self.model.ean13 == normalized_query
            )
        else:
            stmt = self._get_global_select().where(
                self.model.name.ilike(f"%{normalized_query.lower()}%")
            )
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
        instance.object_variation_attribut = self._normalize_variation_attribut(
            form.object_variation_attribut.data
        )
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
        self._sync_variations_from_form(instance, form.variations)
        self.commit_object()
        return instance.id

    def _normalize_variation_attribut(self, value: str | None) -> str | None:
        """Réutilise la casse d'un attribut existant ou nettoie une nouvelle valeur."""
        normalized = " ".join((value or "").split())
        if not normalized:
            return None
        existing = self.session.execute(
            select(GeneralObjects.object_variation_attribut)
            .where(
                func.lower(GeneralObjects.object_variation_attribut)
                == normalized.casefold()
            )
            .limit(1)
        ).scalar_one_or_none()
        return existing or normalized

    def set_variation_attribut(
        self,
        instance: GeneralObjects,
        value: str | None,
    ) -> None:
        """Met à jour l'attribut porté par les variations d'un produit."""
        instance.object_variation_attribut = self._normalize_variation_attribut(value)
        self.session.flush()

    def _sync_price_history_from_form(
        self, instance: GeneralObjects, price_entries: Any
    ) -> None:
        """Synchronise l'historique des prix à partir du tableau du formulaire."""
        price_model = instance.__mapper__.relationships["prices"].mapper.class_
        sorted_entries = sorted(
            price_entries or [],
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

    def _sync_variations_from_form(
        self, instance: GeneralObjects, variations: Any
    ) -> None:
        """Synchronise les variations de l'objet à partir du formulaire principal."""
        sync_collection(
            parent=instance,
            general_object_id=instance.id,
            attr_name="object_variations",
            form_fieldlist=[entry.form for entry in variations],
            model_class=self.variation_repo.model,
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

    def _coerce_price_rows(
        self,
        object_price: ObjectPrices | list[ObjectPrices] | None,
    ) -> list[ObjectPrices]:
        """Normalise un prix unique ou une liste de prix dans un même format."""
        if object_price is None:
            return []
        if isinstance(object_price, list):
            return object_price
        return [object_price]

    def _normalize_ean(self, general_object: GeneralObjects) -> str | None:
        """Nettoie et normalise le code EAN13 de l'objet."""
        if general_object.ean13 is None:
            return None
        normalized = str(general_object.ean13).strip()
        general_object.ean13 = normalized
        return normalized

    def _copy_object_fields(self, target: GeneralObjects, source: GeneralObjects) -> None:
        """Copie les champs utiles d'un objet source vers la cible."""
        for attr, value in vars(source).items():
            if attr not in ("id", "_sa_instance_state") and value is not None:
                setattr(target, attr, value)

    def _find_existing_instance(
        self,
        general_object_id: int | None,
        normalized_ean: str | None,
    ) -> GeneralObjects | None:
        """Cherche une instance existante par id ou par EAN13."""
        if general_object_id is not None:
            instance = self.session.get(self.model, general_object_id)
            if instance is not None:
                return instance
        if normalized_ean is None:
            return None
        instance = self.get_by_ref(normalized_ean, only_actives=False)
        if instance is not None:
            return instance
        return self.session.execute(
            select(self.model).where(self.model.ean13 == normalized_ean)
        ).scalar_one_or_none()

    def _resolve_instance(self, general_object: GeneralObjects) -> GeneralObjects:
        """Récupère ou crée l'instance GeneralObjects correspondante."""
        normalized_ean = self._normalize_ean(general_object)
        instance = self._find_existing_instance(general_object.id, normalized_ean)
        if instance is None:
            instance = GeneralObjects()
            self.session.add(instance)
        self._copy_object_fields(instance, general_object)
        return instance

    def _flush_instance(
        self,
        instance: GeneralObjects,
        normalized_ean: str | None,
    ) -> GeneralObjects:
        """Flush l'instance et récupère l'enregistrement existant en cas de conflit."""
        try:
            self.session.flush()
            return instance
        except IntegrityError:
            self.session.rollback()
            if normalized_ean is None:
                raise
            existing_instance = self.session.execute(
                select(self.model).where(self.model.ean13 == normalized_ean)
            ).scalar_one_or_none()
            if existing_instance is None:
                raise
            self._copy_object_fields(existing_instance, instance)
            self.session.flush()
            return existing_instance

    def _apply_relationships(   # pylint: disable=R0913
        self,
        instance: GeneralObjects,
        *,
        book: Books | None,
        other_object: OtherObjects | None,
        obj_metadatas: ObjMetadatas | None,
        object_tags: ObjectTags | None,
        media_files: MediaFiles | None,
    ) -> None:
        """Attache les relations de l'objet sans logique métier de prix."""
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

    def _apply_price_rows(self, instance: GeneralObjects, price_rows: list[ObjectPrices]) -> None:
        """Synchronise les périodes de prix sans modifier les tarifs futurs connus."""
        for price_row in sorted(price_rows, key=lambda row: row.from_date or date.today()):
            from_date = price_row.from_date or date.today()
            existing = next(
                (
                    price for price in instance.prices
                    if price.vat_rate_id == price_row.vat_rate_id
                    and price.from_date == from_date
                ),
                None,
            )
            if existing is None:
                existing = ObjectPrices(
                    price=price_row.price,
                    vat_rate_id=price_row.vat_rate_id,
                    from_date=from_date,
                    to_date=price_row.to_date,
                )
                instance.prices.append(existing)
            else:
                existing.price = price_row.price

            previous_prices = [
                price for price in instance.prices
                if price.vat_rate_id == existing.vat_rate_id
                and price.from_date < from_date
                and (price.to_date is None or price.to_date >= from_date)
            ]
            if previous_prices:
                latest_price = max(previous_prices, key=lambda price: price.from_date)
                latest_price.to_date = from_date - timedelta(days=1)

            future_prices = [
                price for price in instance.prices
                if price.vat_rate_id == existing.vat_rate_id
                and price.from_date > from_date
            ]
            if future_prices:
                next_price = min(future_prices, key=lambda price: price.from_date)
                existing.to_date = next_price.from_date - timedelta(days=1)

    def save_or_update_from_object( # pylint: disable=R0913, R0917
            self,
            general_object: GeneralObjects,
            other_object: Optional[OtherObjects] = None,
            book: Optional[Books] = None,
            obj_metadatas: Optional[ObjMetadatas] = None,
            object_tags: Optional[ObjectTags] = None,
            media_files: Optional[MediaFiles] = None,
            object_price: ObjectPrices | list[ObjectPrices] | None = None,
            ) -> int:
        """Sauvegarde un objet à partir d'une instance GeneralObjects complète."""
        normalized_ean = self._normalize_ean(general_object)
        instance = self._resolve_instance(general_object)
        instance = self._flush_instance(instance, normalized_ean)

        self._apply_relationships(
            instance,
            book=book,
            other_object=other_object,
            obj_metadatas=obj_metadatas,
            object_tags=object_tags,
            media_files=media_files,
        )

        price_rows = self._coerce_price_rows(object_price)
        if price_rows:
            self._apply_price_rows(instance, price_rows)

        first_price = price_rows[0] if price_rows else None
        logger.debug(
            "[ObjectsRepository] objet avant commit: ean13=%s, name=%s, description=%s, book=%s, " +
            "obj_metadatas=%s, prices=%s, object_price=%s, vat_rate_id=%s",
            getattr(instance, "ean13", None),
            getattr(instance, "name", None),
            getattr(instance, "description", None),
            getattr(instance, "book", None),
            getattr(instance, "obj_metadatas", None),
            getattr(instance, "prices", None),
            first_price,
            getattr(first_price, "vat_rate_id", None),
        )

        return instance.id
