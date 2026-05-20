"""
Module de services pour l'intégration avec WooCommerce.
La base de données locale est source unique de vérité pour les produits,
et WooCommerce est utilisé pour exposer ces produits à l'extérieur.

Le schéma métier est le suivant :
- Export des produits (dernière version) vers WooCommerce en cas de changements.
- Récupération des commandes depuis WooCommerce pour traitement dans l'outil local.
- Mise à jour du statut des commandes dans WooCommerce en fonction du traitement local.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Callable
from requests.exceptions import RequestException
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session
from db_models.objects.vat import VatRate
from db_models.repositories.objects import ObjectsRepository, GeneralObjects
from db_models.repositories.tags import TagsRepository, Tags
from db_models.repositories.objects.media import MediaRepository, MediaFiles
from db_models.repositories.objects.media_access_token import MediaAccessTokenRepository
from db_models.services.utils import slugify
from db_models.services.woo_commerce.base import WCBase
from db_models.services.woo_commerce.utils import _merge_attribute_lists

_FRONT_BASE_URL = os.environ.get("FRONT_BASE_URL", "")

logger = logging.getLogger(__name__)

object_type_mapping = {
    "book": [20],
    "cd": [21, 22],
    "dvd": [21, 23],
    "games": [24, 26],
    "spiritual_object": [24, 25],
    "other": [24],
}


@dataclass
class WooReturnItem:
    """Représente un item retourné par l'API WooCommerce batch."""
    id: int
    name: str | None = None
    rate: float | None = None
    class_: str | None = None
    sku: str | None = None
    file_link: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WooReturnItem":
        """Parse un dict WooCommerce en WooReturnItem."""
        return cls(
            id=int(data["id"]),
            name=data.get("name"),
            rate=float(data.get("rate", 0)) if data.get("rate") else None,
            class_=data.get("class"),
            sku=data.get("sku"),
            file_link=data.get("name"),  # Pour images, c'est le "name" qui est le file_link
        )


class ReturnMatcher:
    """Stratégie pour trouver un local matching un item WooCommerce."""
    def match_create(self, locals_: Sequence[Any], item: WooReturnItem) -> Optional[Any]:
        raise NotImplementedError

    def match_update(self, locals_: Sequence[Any], item: WooReturnItem) -> Optional[Any]:
        raise NotImplementedError

    def match_delete(self, session: Session, item: WooReturnItem) -> Optional[Any]:
        raise NotImplementedError


class ReturnUpdater:
    """Stratégie pour mettre à jour un local après un retour WooCommerce."""
    def update_create(self, local: Any, item: WooReturnItem) -> None:
        raise NotImplementedError

    def update_update(self, local: Any, item: WooReturnItem) -> None:
        raise NotImplementedError

    def update_delete(self, local: Any, item: WooReturnItem) -> None:
        raise NotImplementedError

class WCProductsService(WCBase):
    """
    Service pour interagir avec l'API de WooCommerce.
    Ce service gère la connexion à l'API, l'export des produits, la récupération des commandes,
    et la mise à jour des statuts de commandes.
    Vérifier les variables d'environnement pour la configuration de l'API WooCommerce :
    - WOOCOMMERCE_BASE_URL : URL de base de l'API WooCommerce (ex: https://www.your_site.com)
    - WOOCOMMERCE_VERIFY_SSL : Vérifie le certificat SSL lors des requêtes API (True/False)
    - WOOCOMMERCE_VERSION : Version de l'API WooCommerce
    - WOOCOMMERCE_WP_API : Indique si l'API WordPress est utilisée
    - WOOCOMMERCE_READER_KEY : Clé API pour la lecture
    - WOOCOMMERCE_READER_SECRET : Secret API pour la lecture
    - WOOCOMMERCE_WRITER_KEY : Clé API pour l'écriture
    - WOOCOMMERCE_WRITER_SECRET : Secret API pour l'écriture
    - WOOCOMMERCE_CONSUMER_KEY : Clé API consommateur
    - WOOCOMMERCE_CONSUMER_SECRET : Secret API consommateur
    
    Args:
        separated_keys (bool): Si True, utilise des clés séparées pour la lecture et l'écriture.
                              Sinon, utilise une seule configuration pour les deux.
    """

    def __init__(self, session: Session, separated_keys: bool = False):
        """
        Initialise le service WooCommerce avec la configuration appropriée.
        Args:
            session (Session):
                - Session SQLAlchemy pour les opérations de base de données.
            separated_keys (bool):
                - Indique si des clés séparées sont utilisées pour la lecture et l'écriture.
        Attributs:
            api_read (API): Instance de l'API WooCommerce pour les opérations de lecture.
            api_write (API): Instance de l'API WooCommerce pour les opérations d'écriture.
            object_repo (ObjectsRepository): Repo pour accéder aux objets locaux.
            tag_repo (TagsRepository): Repo pour accéder aux tags locaux.
            media_repo (MediaRepository): Repo pour accéder aux médias locaux.
            sync_log_repo (SyncLogRepository): Repo pour enregistrer les logs de synchronisation.
        """
        super().__init__(session, separated_keys)
        self.object_repo = ObjectsRepository(self.session)
        self.tag_repo = TagsRepository(self.session)
        self.media_repo = MediaRepository(self.session)

    def _build_product_payload(self, product: GeneralObjects) -> dict[str, Any]:
        """
        Construit le dictionnaire WooCommerce pour un produit (enrichi des sous-objets).
        
        Args:
            product (GeneralObjects): L'objet général à convertir en payload WooCommerce.
        
        Returns:
            dict[str, Any]: Le dictionnaire WooCommerce représentant le produit.
        """
        categories = {
            "categories": [
                {"id": o} \
                for o in object_type_mapping.get(
                    product.general_object_type,
                    [15]
                )
            ]
        }
        product_dict = product.to_dict_for_woo_commerce()
        product_dict |= categories
        if product.book:
            book_attrs = product.book.to_dict_for_woo_commerce().get("attributes", [])
            current_attrs = product_dict.get("attributes", [])
            merged_attrs = _merge_attribute_lists(current_attrs, book_attrs) \
                if isinstance(current_attrs, list) else book_attrs
            product_dict["attributes"] = merged_attrs
        if product.other_object:
            other_attrs = product.other_object.to_dict_for_woo_commerce().get("attributes", [])
            current_attrs = product_dict.get("attributes", [])
            merged_attrs = _merge_attribute_lists(current_attrs, other_attrs) \
                if isinstance(current_attrs, list) else other_attrs
            product_dict["attributes"] = merged_attrs
        if product.obj_metadatas:
            meta_attrs = product.obj_metadatas.to_dict_for_woo_commerce().get("attributes", [])
            current_attrs = product_dict.get("attributes", [])
            merged_attrs = _merge_attribute_lists(current_attrs, meta_attrs) \
                if isinstance(current_attrs, list) else meta_attrs
            product_dict["attributes"] = merged_attrs
        if product.media_files:
            product_dict["images"] = [
                {
                    "src": self._build_media_src(media),
                    "name": media.file_link,
                    "alt": f"{product.name} - {media.alt_text or media.file_link}"
                }
                for media in product.media_files
            ]
        return product_dict

    def _build_media_src(self, media: MediaFiles) -> str:
        """Construit l'URL source d'une image pour WooCommerce.

        Pour les fichiers locaux (``is_local=True``), crée un jeton d'accès
        à usage unique et retourne l'URL tokenisée via la route ``serve_media``.
        Pour les fichiers externes, retourne directement ``file_link``.
        """
        if not media.is_local:
            return media.file_link or ""

        token_repo = MediaAccessTokenRepository(self.session)
        existing = token_repo.get(media.file_link)
        if existing:
            token = existing if existing.is_valid() else token_repo.renew(existing)
        else:
            token = token_repo.create(media.file_link)

        return f"{_FRONT_BASE_URL}/woocommerce/media/{token.token}"

    def _process_returns_action(
        self,
        action: str,
        items: list[dict[str, Any]],
        locals_: Sequence[Any],
        entity_type: str,
        matcher: Optional[Callable[[Sequence[Any], dict[str, Any]], Optional[Any]]],
        updater: Optional[Callable[[Any, int, dict[str, Any]], None]],
        finder_by_wc_id: Optional[Callable[[int], Optional[Any]]] = None,
    ) -> None:
        """Traite une action (create/update/delete) pour une batch de retours."""
        for item in items:
            wc_id = int(item["id"])
            # Chercher l'entité locale : d'abord par wc_id (delete), sinon par matcher
            if finder_by_wc_id:
                local = finder_by_wc_id(wc_id)
            elif matcher:
                local = matcher(locals_, item)
            else:
                local = None
            if updater and local:
                updater(local, wc_id, item)
            self._log_sync(entity_type, local.id if local else None, wc_id, action, "success")

    def _apply_returns_generic(
        self,
        returns: dict[str, list[dict[str, Any]]],
        locals_: Sequence[Any],
        entity_type: str,
        matchers: dict[str, Callable[[Sequence[Any], dict[str, Any]], Optional[Any]]],
        updaters: dict[str, Callable[[Any, int, dict[str, Any]], None]],
        finder_by_wc_id: Optional[Callable[[int], Optional[Any]]] = None,
    ) -> None:
        """
        Dispatcher générique pour traiter les retours batch WooCommerce.

        Args:
            returns: Dict avec clés "create"/"update"/"delete" contenant les items WC
            locals_: Liste des entités locales de même type
            entity_type: Nom du type pour le logging
            matchers: Dict[action] → fonction de matching
            updaters: Dict[action] → fonction de mise à jour
            finder_by_wc_id: Optionnel, fonction pour retrouver local par wc_id (delete)
        """
        for action in ("create", "update", "delete"):
            use_finder = action == "delete"
            finder = finder_by_wc_id if use_finder else None
            self._process_returns_action(
                action,
                returns.get(action, []),
                locals_,
                entity_type,
                matchers.get(action),
                updaters.get(action),
                finder,
            )

    def _apply_product_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        products: Sequence[GeneralObjects],
    ) -> None:
        """Traite les retours batch WooCommerce pour les produits."""
        matchers = {
            "create": lambda prods, item: next(
                (p for p in prods if str(p.id) == str(item.get("sku") or "")), None
            ),
            "update": lambda prods, item: next(
                (p for p in prods if p.id_wpwc == int(item["id"])), None
            ),
        }
        updaters = {
            "create": lambda p, wc_id, _: setattr(p, "id_wpwc", wc_id),
            "delete": lambda p, _, __: setattr(p, "id_wpwc", None),
        }
        finder = lambda wc_id: self.session.execute(    # pylint: disable=C3001
            select(GeneralObjects).where(GeneralObjects.id_wpwc == wc_id)
        ).scalar_one_or_none()

        self._apply_returns_generic(
            returns, products, "object", matchers, updaters, finder
        )

    def _apply_tag_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        tags: Sequence[Tags],
    ) -> None:
        """Traite les retours batch WooCommerce pour les tags."""
        matchers = {
            "create": lambda tgs, item: next(
                (t for t in tgs if t.name == item.get("name")), None
            ),
            "update": lambda tgs, item: next(
                (t for t in tgs if t.id_wpwc == int(item["id"])), None
            ),
        }
        updaters = {
            "create": lambda t, wc_id, _: setattr(t, "id_wpwc", wc_id),
            "delete": lambda t, _, __: setattr(t, "id_wpwc", None),
        }
        finder = lambda wc_id: self.session.execute(    # pylint: disable=C3001
            select(Tags).where(Tags.id_wpwc == wc_id)
        ).scalar_one_or_none()

        self._apply_returns_generic(
            returns, tags, "tag", matchers, updaters, finder
        )

    def _apply_picture_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        pictures: Sequence[MediaFiles],
    ) -> None:
        """Traite les retours batch WooCommerce pour les images."""
        matchers = {
            "create": lambda pics, item: next(
                (p for p in pics if p.file_link == item.get("name")), None
            ),
            "update": lambda pics, item: next(
                (p for p in pics if p.id_wpwc == int(item["id"])), None
            ),
        }
        updaters = {
            "create": lambda p, wc_id, _: setattr(p, "id_wpwc", wc_id),
            "delete": lambda p, _, __: setattr(p, "id_wpwc", None),
        }
        finder = lambda wc_id: self.session.execute(    # pylint: disable=C3001
            select(MediaFiles).where(MediaFiles.id_wpwc == wc_id)
        ).scalar_one_or_none()

        self._apply_returns_generic(
            returns, pictures, "media", matchers, updaters, finder
        )

    def _apply_vat_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        vat_rates: Sequence[VatRate],
    ) -> None:
        """Traite les retours batch WooCommerce pour les taux de TVA."""

        def updater_create(v: VatRate, wc_id: int, item: dict[str, Any]) -> None:
            v.wpwc_id = wc_id
            v.wpwc_slug = item.get("class") or ""

        def updater_update(v: VatRate, _: int, item: dict[str, Any]) -> None:
            if item.get("class") is not None:
                v.wpwc_slug = item.get("class") or ""

        matchers = {
            "create": lambda vrs, item: next(
                (v for v in vrs if float(v.rate) == float(item.get("rate", -1))),
                None,
            ),
            "update": lambda vrs, item: next(
                (v for v in vrs if v.wpwc_id == int(item["id"])), None
            ),
        }
        updaters = {
            "create": updater_create,
            "update": updater_update,
            "delete": lambda v, _, __: setattr(v, "wpwc_id", None),
        }
        finder = lambda wc_id: self.session.execute(    # pylint: disable=C3001
            select(VatRate).where(VatRate.wpwc_id == wc_id)
        ).scalar_one_or_none()

        self._apply_returns_generic(
            returns, vat_rates, "vat_rate", matchers, updaters, finder
        )

    def update_product(self, product_id: int):
        """
        Met à jour ou crée un produit spécifique dans WooCommerce.
        Si le produit est inactif, la mise à jour est ignorée.
        Args:
            product_id (int): ID du produit local à mettre à jour dans WooCommerce.
        Returns:
            None
        """

        # Récupération du produit local et vérification de son statut
        product = self.object_repo.get_by_ref(product_id, only_actives=False)
        if product and not product.is_active:
            logger.warning(
                "Produit avec ID %d inactif. Mise à jour WooCommerce ignorée.",
                product_id
                )
            return

        # Récupération de la version actuelle du produit dans WooCommerce pour calculer des difs
        wpwc_product = self.api_read.get(
            f"products/{product.id_wpwc}"
            ).json() if product.id_wpwc else None
        data = self.__diff_objects([product], [wpwc_product] if wpwc_product else [])

        # Envoi de la requête de mise à jour à WooCommerce et traitement des retours
        returns: list[dict[str, list[dict[str, Any]]]] = []
        try:
            for d in data:
                response = self.api_write.post("products/batch", data=d)
                response.raise_for_status()
                r = response.json()
                logger.debug(
                    "Retour de WooCommerce pour la mise à jour du produit %d : %s",
                    product_id,
                    r
                )
                returns.append(r)

        # Gestion des exceptions
        except (RequestException, ValueError) as exc:
            logger.exception(
                "Erreur lors de la mise à jour du produit %d vers WooCommerce : %s",
                product_id,
                exc
                )
            self._log_sync(
                entity_type="object",
                entity_id=product.id,
                wpwc_id=product.id_wpwc,
                operation="update",
                sync_status="error",
                error_message=str(exc)
            )
            self.session.commit()
            return

        # Application des retours de WooCommerce et enregistrement dans le log de synchronisation
        for r in returns:
            self._apply_product_returns(returns=r, products=[product])
        self.session.commit()
        logger.info(
            "Mise à jour du produit %d vers WooCommerce terminée. Statut: %s",
            product_id,
            "success" if any(r.get("create") or r.get("update") for r in returns) else "no change"
        )

    def export_all_products(self):
        """
        Exporte la dernière version des produits vers WooCommerce.
        - Créations : stocke l'id_wpwc retourné sur l'objet local + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog (id_wpwc déjà connu).
        - Suppressions : efface id_wpwc sur l'objet local (désactivé) + trace dans ObjectSyncLog.
        """
        products = self.object_repo.get_all(only_actives=True)
        logger.info("Export de %d produits vers WooCommerce...", len(products))
        for p in products:
            self._build_product_payload(p)
        wpwc_products = self.api_read.get("products").json()
        data = self.__diff_objects(products, wpwc_products)
        returns: list[dict[str, list[dict[str, Any]]]] = []
        try:
            for d in data:
                response = self.api_write.post("products/batch", data=d)
                response.raise_for_status()
                returns.append(response.json())
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Erreur lors de l'export des produits vers WooCommerce : %s", exc)
            for p in products:
                self._log_sync(
                    entity_type="object",
                    entity_id=p.id,
                    wpwc_id=p.id_wpwc,
                    operation="batch",
                    sync_status="error",
                    error_message=str(exc)
                )
            self.session.commit()
            return
        for r in returns:
            self._apply_product_returns(r, products)
        self.session.commit()
        logger.info(
            "Export produits terminé. Créés: %d, Mis à jour: %d, Supprimés: %d",
            sum(len(r.get("create", [])) for r in returns),
            sum(len(r.get("update", [])) for r in returns),
            sum(len(r.get("delete", [])) for r in returns),
        )

    def export_tags(self) -> None:
        """
        Exporte les tags vers WooCommerce.
        - Créations : stocke l'id_wpwc retourné sur le tag local + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog.
        - Suppressions : efface id_wpwc sur le tag local + trace dans ObjectSyncLog.
        """
        tags = self.tag_repo.get_all(only_actives=True)
        if not tags:
            logger.info("Aucun tag à exporter vers WooCommerce.")
            return
        wpwc_tags: list[dict[str, Any]] = self.api_read.get("products/tags").json()
        data = self.__diff_tags(tags, wpwc_tags)
        try:
            returns: dict[str, list[dict[str, Any]]] = (
                self.api_write.post("products/tags/batch", data=data).json()
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Erreur lors de l'export des tags vers WooCommerce : %s", exc)
            for t in tags:
                self._log_sync("tag", t.id, t.id_wpwc, "batch", "error", str(exc))
            self.session.commit()
            return
        self._apply_tag_returns(returns, tags)
        self.session.commit()
        logger.info(
            "Export tags terminé. Créés: %d, Mis à jour: %d, Supprimés: %d",
            len(returns.get("create", [])),
            len(returns.get("update", [])),
            len(returns.get("delete", [])),
        )

    def export_pictures(self):
        """
        Exporte les images vers WooCommerce.
        - Créations : stocke l'id_wpwc retourné sur l'image locale + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog.
        - Suppressions : efface id_wpwc sur l'image locale + trace dans ObjectSyncLog.
        """
        pictures = self.media_repo.get_all()
        if not pictures:
            logger.info("Aucune image à exporter vers WooCommerce.")
            return
        wpwc_pictures: list[dict[str, Any]] = self.api_read.get("media").json()
        data = self.__diff_pictures(pictures, wpwc_pictures)
        try:
            returns: dict[str, list[dict[str, Any]]] = (
                self.api_write.post("media/batch", data=data).json()
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Erreur lors de l'export des images vers WooCommerce : %s", exc)
            for p in pictures:
                self._log_sync("media", p.id, p.id_wpwc, "batch", "error", str(exc))
            self.session.commit()
            return
        self._apply_picture_returns(returns, pictures)
        self.session.commit()
        logger.info(
            "Export images terminé. Créés: %d, Mis à jour: %d, Supprimés: %d",
            len(returns.get("create", [])),
            len(returns.get("update", [])),
            len(returns.get("delete", [])),
        )

    def __diff_tags(
            self,
            tags: Sequence[Tags],
            wpwc_tags: list[dict[str, Any]]
        ) -> dict[str, list[dict[str, Any]]]:
        """Calcule les différences entre les tags locaux et ceux de WooCommerce."""
        data: dict[str, list[dict[str, Any]]] = {"create": [], "update": [], "delete": []}
        wpwc_tag_ids = {int(tag["id"]) for tag in wpwc_tags}
        for t in tags:
            matched = next(
                (wpwc for wpwc in wpwc_tags if int(wpwc["id"]) == int(t.id_wpwc or 0)),
                None
            )
            if matched:
                entry = {
                    "id": int(matched["id"]),
                    "name": t.name,
                    "slug": slugify(t.name),
                    "description": t.description or "",
                }
                data["update"].append(entry)
                wpwc_tag_ids.remove(int(entry["id"]))
            else:
                entry = {
                    "name": t.name,
                    "slug": slugify(t.name),
                    "description": t.description or "",
                }
                data["create"].append(entry)
        for wpwc_id in wpwc_tag_ids:
            data["delete"].append({"id": wpwc_id})
        return data

    def __diff_pictures(
            self,
            pictures: Sequence[MediaFiles],
            wpwc_pictures: list[dict[str, Any]]
        ) -> dict[str, list[dict[str, Any]]]:
        """Calcule les différences entre les images locales et celles de WooCommerce."""
        data: dict[str, list[dict[str, Any]]] = {"create": [], "update": [], "delete": []}
        wpwc_picture_ids = {int(p["id"]) for p in wpwc_pictures}
        for p in pictures:
            matched = next(
                (wpwc for wpwc in wpwc_pictures if int(wpwc["id"]) == int(p.id_wpwc or 0)),
                None
            )
            if matched:
                entry = {
                    "id": int(matched["id"]),
                    "name": p.file_link,
                    "alt": p.alt_text or "",
                    "src": p.file_link or "",
                }
                data["update"].append(entry)
                wpwc_picture_ids.remove(int(entry["id"]))
            else:
                entry = {
                    "name": p.file_link,
                    "alt": p.alt_text or "",
                    "src": p.file_link or "",
                }
                data["create"].append(entry)
        for wpwc_id in wpwc_picture_ids:
            data["delete"].append({"id": wpwc_id})
        return data

    def __diff_objects(
            self,
            objects: Sequence[GeneralObjects],
            wpwc_objects: list[dict[str, Any]]
        ) -> list[dict[str, list[dict[str, Any]]]]:
        """Calcule les différences entre les objets locaux et ceux de WooCommerce."""
        data: list[dict[str, list[dict[str, Any]]]] = []
        batch_data: dict[str, list[dict[str, Any]]] = {"create": [], "update": [], "delete": []}
        wpwc_object_ids = {int(obj["id"]) for obj in wpwc_objects}
        for i, o in enumerate(objects):
            matched = next(
                (wpwc for wpwc in wpwc_objects if int(wpwc["id"]) == int(o.id_wpwc or 0)),
                None
            )
            logger.debug(
                "Comparaison de l'objet local ID %d avec l'objet WooCommerce ID %s",
                o.id,
                str(matched["id"]) if matched else "None"
            )
            if matched:
                entry = self._build_product_payload(o)
                entry["id"] = int(matched["id"])
                batch_data["update"].append(entry)
                wpwc_object_ids.remove(int(entry["id"]))
                logger.debug(
                    "Objet local ID %d correspond à l'objet WooCommerce ID %d. " +
                    "Ajouté à la liste de mise à jour.",
                    o.id,
                    int(matched["id"])
                )
            else:
                batch_data["create"].append(self._build_product_payload(o))
                logger.debug(
                    "Objet local ID %d n'a pas de correspondance dans WooCommerce. " +
                    "Ajouté à la liste de création.",
                    o.id
                )
            if (i + 1) % 100 == 0 or (i + 1) == len(objects):
                data.append(batch_data)
                batch_data = {"create": [], "update": [], "delete": []}
        for wpwc_id in wpwc_object_ids:
            batch_data["delete"].append({"id": wpwc_id})
            if sum(len(lst) for lst in batch_data.values()) >= 100:
                data.append(batch_data)
                batch_data = {"create": [], "update": [], "delete": []}
        if batch_data["create"] or batch_data["update"] or batch_data["delete"]:
            data.append(batch_data)
        logger.debug(
            "Différence calculée entre les objets locaux et WooCommerce : " +
            "%d à créer, %d à mettre à jour, %d à supprimer",
            sum(len(d.get("create", [])) for d in data),
            sum(len(d.get("update", [])) for d in data),
            sum(len(d.get("delete", [])) for d in data)
        )
        return data

    def __diff_vat_rates(
            self,
            vat_rates: Sequence[VatRate],
            wpwc_vat_rates: list[dict[str, Any]]
        ) -> dict[str, list[dict[str, Any]]]:
        """
        Calcule les différences entre les taux de TVA locaux et ceux de WooCommerce.
        Args:
            vat_rates (Sequence[VatRate]): Liste des taux de TVA locaux.
            wpwc_vat_rates (list[dict[str, Any]]): Liste des taux de TVA de WooCommerce.
        Returns:
            dict[str, list[dict[str, Any]]]: Dictionnaire contenant les taux à créer,
                                             mettre à jour et supprimer dans WooCommerce.
        """
        data: dict[str, list[dict[str, Any]]] = {"create": [], "update": [], "delete": []}
        wpwc_vat_ids = {int(rate["id"]) for rate in wpwc_vat_rates}
        for v in vat_rates:
            target_class = v.wpwc_slug or slugify(v.label)
            # Appariement par classe de taxe (robuste), puis par wpwc_id (fallback)
            matched = next(
                (wpwc for wpwc in wpwc_vat_rates if wpwc.get("class") == target_class),
                None,
            )
            if matched is None and v.wpwc_id:
                matched = next(
                    (wpwc for wpwc in wpwc_vat_rates if int(wpwc["id"]) == int(v.wpwc_id)),
                    None,
                )
            if matched:
                t = {
                    "id": int(matched["id"]),
                    "rate": str(v.rate),
                    "name": v.label,
                    "class": target_class,
                }
                data["update"].append(t)
                wpwc_vat_ids.discard(int(t["id"]))
            else:
                t = {
                    "rate": str(v.rate),
                    "name": v.label,
                    "class": target_class,
                }
                data["create"].append(t)
        for wpwc_id in wpwc_vat_ids:
            data["delete"].append({"id": wpwc_id})
        return data

    def _ensure_wc_tax_classes(self, vat_rates: Sequence[VatRate]) -> None:
        """Crée dans WooCommerce les classes de taxe manquantes (une par taux de TVA local)
        et met à jour wpwc_slug en conséquence.
        """
        try:
            wc_classes: list[dict[str, Any]] = self.api_read.get("taxes/classes").json()
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Erreur récupération classes de taxe WC : %s", exc)
            return
        wc_slug_map: dict[str, dict[str, Any]] = {cls["slug"]: cls for cls in wc_classes}
        for v in vat_rates:
            expected_slug = slugify(v.label)
            if expected_slug in wc_slug_map:
                if v.wpwc_slug != expected_slug:
                    v.wpwc_slug = expected_slug
            else:
                try:
                    resp = self.api_write.post("taxes/classes", data={"name": v.label})
                    resp.raise_for_status()
                    actual_slug = resp.json().get("slug") or expected_slug
                    wc_slug_map[actual_slug] = resp.json()
                    if v.wpwc_slug != actual_slug:
                        v.wpwc_slug = actual_slug
                    logger.info(
                        "Classe de taxe WC créée : %r → slug=%r", v.label, actual_slug
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.exception(
                        "Erreur création classe de taxe WC pour %r : %s", v.label, exc
                    )
        self.session.flush()

    def export_vat_rates(self, name: Optional[str] = None) -> None:
        """
        Exporte les taux de TVA vers WooCommerce.
        - Crée d'abord les classes de taxe WC manquantes (une par taux, slug dérivé du label).
        - Créations : stocke wpwc_id retourné sur le VatRate local + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog.
        - Suppressions : efface wpwc_id sur le VatRate local + trace dans ObjectSyncLog.

        Arguments:
            name (str, optional): Le nom du taux de TVA à exporter. Si None, exporte tous les taux.
        """
        stmt = select(VatRate).where(or_(VatRate.date_end == None, VatRate.date_end > func.now()))  # pylint: disable=singleton-comparison, not-callable
        if name:
            stmt = stmt.where(VatRate.label == name)
        vat_rates = self.session.execute(stmt).scalars().all()
        self._ensure_wc_tax_classes(vat_rates)
        wpwc_vat_rates: list[dict[str, Any]] = self.api_read.get("taxes").json()
        data = self.__diff_vat_rates(vat_rates, wpwc_vat_rates)
        try:
            returns: dict[str, list[dict[str, Any]]] = (
                self.api_write.post("taxes/batch", data=data).json()
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Erreur lors de l'export des taux de TVA vers WooCommerce : %s", exc)
            for v in vat_rates:
                self._log_sync(
                    entity_type="vat_rate",
                    entity_id=v.id,
                    wpwc_id=v.wpwc_id,
                    operation="batch",
                    sync_status="error",
                    error_message=str(exc)
                )
            self.session.commit()
            return
        self._apply_vat_returns(returns, vat_rates)
        self.session.commit()
        logger.info(
            "Export taux de TVA terminé. Créés: %d, Mis à jour: %d, Supprimés: %d",
            len(returns.get("create", [])),
            len(returns.get("update", [])),
            len(returns.get("delete", [])),
        )

    def ensure_vat_rates(self) -> None:
        """
        S'assure que les taux de TVA nécessaires sont présents dans WooCommerce.
        Si un taux de TVA n'existe pas dans WooCommerce, il est créé à partir des données locales.
        """
        local_vat_rates = self.session.execute(
            select(VatRate) \
            .where(
                and_(
                    VatRate.wpwc_id == None,    # pylint: disable=singleton-comparison
                    or_(
                        VatRate.date_end == None,   # pylint: disable=singleton-comparison
                        VatRate.date_end > func.now()   # pylint: disable=not-callable
                    )))) \
            .scalars().all()
        wpwc_vat_rates: list[dict[str, Any]] = self.api_read.get("taxes").json()
        for local_rate in local_vat_rates:
            if not any(float(wpwc["rate"]) == float(local_rate.rate) for wpwc in wpwc_vat_rates):
                logger.info(
                    "Taux de TVA %s%% manquant dans WooCommerce. Création en cours.",
                    local_rate.rate
                )
                self.export_vat_rates(name=local_rate.label)

    def import_vat_slugs(self) -> int:
        """Lit les taux de TVA depuis WooCommerce et rétro-alimente wpwc_slug en local.

        À appeler une fois après la migration, ou après un changement de configuration WC.

        Returns:
            Nombre de taux mis à jour.
        """
        wpwc_rates: list[dict[str, Any]] = self.api_read.get(
            "taxes", params={"per_page": 100}
        ).json()
        local_rates = self.session.execute(select(VatRate)).scalars().all()
        updated = 0
        for wc_rate in wpwc_rates:
            wc_id = wc_rate.get("id")
            wc_slug = wc_rate.get("class") or ""
            wc_rate_value = float(wc_rate.get("rate", 0))
            # Appariement par taux (robuste), avec fallback sur wpwc_id
            local = next(
                (v for v in local_rates if round(float(v.rate), 3) == round(wc_rate_value, 3)),
                None,
            )
            if local is None:
                local = next((v for v in local_rates if v.wpwc_id == wc_id), None)
            if local:
                changed = False
                if local.wpwc_id != wc_id:
                    local.wpwc_id = wc_id
                    changed = True
                if local.wpwc_slug != wc_slug:
                    local.wpwc_slug = wc_slug
                    changed = True
                if changed:
                    updated += 1
                    logger.info(
                        "VatRate id=%d (rate=%.3f) : wpwc_id=%d, wpwc_slug=%r",
                        local.id, float(local.rate), wc_id, wc_slug,
                    )
        self.session.commit()
        logger.info("import_vat_slugs : %d taux mis à jour.", updated)
        return updated

    def ensure_tags(self) -> None:
        """
        S'assure que les tags nécessaires sont présents dans WooCommerce.
        Si un tag n'existe pas dans WooCommerce, il est créé à partir des données locales.
        """
        local_tags = self.session.execute(
            select(Tags).where(Tags.id_wpwc == None)  # pylint: disable=singleton-comparison
        ).scalars().all()
        wpwc_tags: list[dict[str, Any]] = self.api_read.get("products/tags").json()
        for local_tag in local_tags:
            if not any(wpwc["name"] == local_tag.name for wpwc in wpwc_tags):
                logger.info(
                    "Tag '%s' manquant dans WooCommerce. Création en cours.",
                    local_tag.name
                )
                self.export_tags()

    def ensure_products(self) -> None:
        """
        S'assure que les produits locaux sont présents dans WooCommerce.
        Si un produit local n'existe pas dans WooCommerce, il est créé.
        """
        local_products = self.object_repo.get_all(only_actives=True)
        wpwc_products: list[dict[str, Any]] = self.api_read.get("products").json()
        for local_product in local_products:
            if not any(
                int(wpwc["id"]) == int(local_product.id_wpwc or 0)
                for wpwc in wpwc_products
            ):
                logger.info(
                    "Produit '%s' (ID %d) manquant dans WooCommerce. Création en cours.",
                    local_product.name,
                    local_product.id
                )
                self.update_product(local_product.id)

    def ensure_media(self) -> None:
        """
        S'assure que les médias locaux sont présents dans WooCommerce.
        Si un média local n'existe pas dans WooCommerce, il est créé.
        """
        local_media = self.media_repo.get_all()
        wpwc_media: list[dict[str, Any]] = self.api_read.get("media").json()
        for local_file in local_media:
            if not any(
                int(wpwc["id"]) == int(local_file.id_wpwc or 0)
                for wpwc in wpwc_media
            ):
                logger.info(
                    "Média '%s' (ID %d) manquant dans WooCommerce. Création en cours.",
                    local_file.file_link,
                    local_file.id
                )
                self.export_pictures()
