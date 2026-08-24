"""
Module de services pour l'intégration avec WooCommerce.
La base de données locale est source unique de vérité pour les produits,
et WooCommerce est utilisé pour exposer ces produits à l'extérieur.

Le schéma métier est le suivant :
- Export des produits (dernière version) vers WooCommerce en cas de changements.
- Récupération des commandes depuis WooCommerce pour traitement dans l'outil local.
- Mise à jour du statut des commandes dans WooCommerce en fonction du traitement local.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Sequence, Callable
from requests.exceptions import RequestException
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session
from db_models.objects import ObjectVariations
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
PROTOCOL = "http"

object_type_mapping = {
    "book": [20],
    "cd": [22, 23],
    "dvd": [22, 24],
    "games": [21, 26],
    "spiritual_object": [21, 25],
    "other": [15],
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
        """Trouve un local correspondant à un item WooCommerce pour une création."""
        raise NotImplementedError

    def match_update(self, locals_: Sequence[Any], item: WooReturnItem) -> Optional[Any]:
        """Trouve un local correspondant à un item WooCommerce pour une mise à jour."""
        raise NotImplementedError

    def match_delete(self, session: Session, item: WooReturnItem) -> Optional[Any]:
        """Trouve un local correspondant à un item WooCommerce pour une suppression."""
        raise NotImplementedError


class ReturnUpdater:
    """Stratégie pour mettre à jour un local après un retour WooCommerce."""
    def update_create(self, local: Any, item: WooReturnItem) -> None:
        """Met à jour un local après une création WooCommerce."""
        raise NotImplementedError

    def update_update(self, local: Any, item: WooReturnItem) -> None:
        """Met à jour un local après une mise à jour WooCommerce."""
        raise NotImplementedError

    def update_delete(self, local: Any, item: WooReturnItem) -> None:
        """Met à jour un local après une suppression WooCommerce."""
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
        self._merge_product_variation_attribute(product, product_dict)
        synced_tags = [
            {"id": obj_tag.tag.wpwc_id}
            for obj_tag in (product.object_tags or [])
            if obj_tag and obj_tag.tag and obj_tag.tag.wpwc_id is not None
        ]
        if synced_tags:
            product_dict["tags"] = synced_tags
        if product.media_files:
            product_dict["images"] = [
                {
                    "src": self._build_media_src(media),
                    "name": os.path.basename(media.file_link or "") or media.file_link or "",
                    "alt": f"{product.name} - {media.alt_text or (
                        os.path.basename(media.file_link or "") or media.file_link or ""
                        ),
                    }"
                }
                for media in product.media_files
            ]
        return product_dict

    @staticmethod
    def _build_variation_attribute(product: GeneralObjects) -> dict[str, Any] | None:
        """Construit l'attribut WooCommerce porté par les variations actives."""
        options = [
            variation.name
            for variation in product.object_variations
            if variation.is_active and variation.name
        ]
        if not options:
            return None
        if not product.object_variation_attribut:
            raise ValueError(
                f"Le produit {product.id} possède des variations sans attribut défini."
            )
        return {
            "name": product.object_variation_attribut,
            "options": list(dict.fromkeys(options)),
            "visible": True,
            "variation": True,
        }

    def _merge_product_variation_attribute(
        self,
        product: GeneralObjects,
        product_dict: dict[str, Any],
    ) -> None:
        """Ajoute l'attribut variable aux autres attributs du produit parent."""
        variation_attribute = self._build_variation_attribute(product)
        if variation_attribute is None:
            return
        current_attrs = product_dict.get("attributes", [])
        product_dict["attributes"] = _merge_attribute_lists(
            current_attrs if isinstance(current_attrs, list) else [],
            [variation_attribute],
        )

    def _build_media_src(self, media: MediaFiles) -> str:
        """Construit l'URL source d'une image pour WooCommerce.

        Les fichiers locaux sont servis via un jeton d'accès à usage unique,
        même lorsque le chemin est enregistré comme un nom de fichier ou un
        chemin absolu sans marqueur ``is_local`` explicite. Les URLs HTTP(S)
        restent transmises telles quelles.
        """
        file_link = media.file_link or ""
        is_local = bool(media.is_local) \
            or not file_link.startswith((f"{PROTOCOL}://", f"{PROTOCOL}s://"))
        if not is_local:
            return file_link

        base_url = (_FRONT_BASE_URL or "https://internal.editions-sauvetage.fr").strip().rstrip("/")

        token_repo = MediaAccessTokenRepository(self.session)
        existing = token_repo.get_last_by_media_id(media.id)
        if existing and existing.is_valid():
            token = existing
        elif existing:
            token = token_repo.renew(existing)
        else:
            token = token_repo.create(media_id=media.id)

        filename = os.path.basename(file_link) or f"media_{media.id}"
        return f"{base_url}/woocommerce/media/{token.token}/{filename}"

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
                (p for p in prods if p.wpwc_id == int(item["id"])), None
            ),
        }
        updaters = {
            "create": lambda p, wc_id, _: setattr(p, "wpwc_id", wc_id),
            "delete": lambda p, _, __: setattr(p, "wpwc_id", None),
        }
        finder = lambda wc_id: self.session.execute(    # pylint: disable=C3001
            select(GeneralObjects).where(GeneralObjects.wpwc_id == wc_id)
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
                (t for t in tgs if t.wpwc_id == int(item["id"])), None
            ),
        }
        updaters = {
            "create": lambda t, wc_id, _: setattr(t, "wpwc_id", wc_id),
            "delete": lambda t, _, __: setattr(t, "wpwc_id", None),
        }
        finder = lambda wc_id: self.session.execute(    # pylint: disable=C3001
            select(Tags).where(Tags.wpwc_id == wc_id)
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
                (p for p in pics if p.wpwc_id == int(item["id"])), None
            ),
        }
        updaters = {
            "create": lambda p, wc_id, _: setattr(p, "wpwc_id", wc_id),
            "delete": lambda p, _, __: setattr(p, "wpwc_id", None),
        }
        finder = lambda wc_id: self.session.execute(    # pylint: disable=C3001
            select(MediaFiles).where(MediaFiles.wpwc_id == wc_id)
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

    def _ensure_product_tags_are_synced(self, product: GeneralObjects) -> None:
        """Synchronise les tags d’un produit vers WooCommerce avant export produit."""
        has_unsynced_tags = any(
            obj_tag and obj_tag.tag and obj_tag.tag.wpwc_id is None
            for obj_tag in (product.object_tags or [])
        )
        if has_unsynced_tags:
            logger.info(
                "Produit %s contient des tags non synchronisés : déclenchement de export_tags().",
                product.id,
            )
            self.export_tags()

    def _fetch_all_wc_variations(self, product_id: int) -> list[dict[str, Any]]:
        """Récupère toutes les variations WooCommerce d'un produit."""
        variations: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self.api_read.get(
                f"products/{product_id}/variations",
                params={"page": page, "per_page": 100},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError(
                    f"Réponse WooCommerce invalide pour les variations du produit {product_id}."
                )
            variations.extend(payload)
            if len(payload) < 100:
                break
            page += 1
        return variations

    def _sync_product_variations(self, product: GeneralObjects) -> None:
        """Crée, met à jour ou supprime les variations WooCommerce du produit."""
        if not product.wpwc_id or not product.object_variations:
            return

        wc_variations = self._fetch_all_wc_variations(product.wpwc_id)
        by_id = {int(item["id"]): item for item in wc_variations}
        by_sku = {
            str(item.get("sku")): item
            for item in wc_variations
            if item.get("sku") not in (None, "")
        }
        for variation in product.object_variations:
            variation_sku = f"{product.id}-{variation.id}"
            matched = by_id.get(int(variation.wpwc_id or 0)) or by_sku.get(variation_sku)
            if matched:
                variation.wpwc_id = int(matched["id"])
            self._sync_product_variation(product.wpwc_id, variation, matched)

    def _sync_product_variation(
        self,
        product_id: int,
        variation: ObjectVariations,
        matched: dict[str, Any] | None,
    ) -> None:
        """Synchronise une variation avec son endpoint WooCommerce individuel."""
        payload: dict[str, Any] | None = None
        if variation.is_active:
            payload = variation.to_dict_for_woo_commerce()
            if matched:
                wc_id = int(matched["id"])
                action = "update"
                response = self.api_write.put(
                    f"products/{product_id}/variations/{wc_id}",
                    data=payload,
                )
            else:
                action = "create"
                response = self.api_write.post(
                    f"products/{product_id}/variations",
                    data=payload,
                )
        elif matched:
            wc_id = int(matched["id"])
            action = "delete"
            response = self.api_write.delete(
                f"products/{product_id}/variations/{wc_id}",
                params={"force": True},
            )
        else:
            variation.wpwc_id = None
            return

        try:
            response.raise_for_status()
        except RequestException as exc:
            raw_response = getattr(response, "text", "") or ""
            logger.error(
                "Échec WooCommerce variation locale=%d action=%s url=%s payload=%s "
                "réponse=%s",
                variation.id,
                action,
                getattr(response, "url", ""),
                payload,
                raw_response[:1000],
            )
            raise exc
        item = response.json()
        if not isinstance(item, dict) or not item.get("id"):
            raise ValueError(
                f"Réponse WooCommerce invalide pour la variation {variation.id}."
            )
        wc_id = int(item["id"])
        variation.wpwc_id = None if action == "delete" else wc_id
        self._log_sync(
            "variation",
            variation.id,
            wc_id,
            action,
            "success",
        )

    @staticmethod
    def _get_product_sync_status(has_batch_effect: bool, has_valid_wc_id: bool) -> str:
        """Détermine le statut final d'une synchronisation produit."""
        if has_batch_effect and has_valid_wc_id:
            return "success"
        if has_batch_effect:
            return "error"
        return "no change"

    def update_product(self, product_id: int) -> int | None:
        """
        Met à jour ou crée un produit spécifique dans WooCommerce.
        Si le produit est inactif, la mise à jour est ignorée.
        Args:
            product_id (int): ID du produit local à mettre à jour dans WooCommerce.
        Returns:
            int | None: L'identifiant WooCommerce du produit si connu après synchronisation.
        """

        # Récupération du produit local et vérification de son statut
        product = self.object_repo.get_by_ref(product_id, only_actives=False)
        if product is None:
            return None
        if not product.is_active:
            logger.warning(
                "Produit avec ID %d inactif. Mise à jour WooCommerce ignorée.",
                product_id
                )
            return product.wpwc_id

        self._ensure_product_tags_are_synced(product)

        # Récupération de la version actuelle du produit dans WooCommerce pour calculer des difs
        wpwc_product = self.api_read.get(
            f"products/{product.wpwc_id}"
            ).json() if product.wpwc_id else None
        data = self.__diff_objects([product], [wpwc_product] if wpwc_product else [])

        # Envoi de la requête de mise à jour à WooCommerce et traitement des retours
        returns: list[dict[str, list[dict[str, Any]]]] = []
        try:
            for d in data:
                response = self.api_write.post("products/batch", data=d)
                response.raise_for_status()
                r = response.json()
                raw_response = getattr(response, "text", None) \
                    or json.dumps(r, ensure_ascii=False, default=str)
                logger.info(
                    "Retour WooCommerce produit %d: HTTP %s — %s",
                    product_id,
                    getattr(response, "status_code", "unknown"),
                    raw_response[:1000],
                )
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
                wpwc_id=product.wpwc_id,
                operation="update",
                sync_status="error",
                error_message=str(exc)
            )
            self.session.commit()
            return product.wpwc_id

        # Application des retours de WooCommerce et enregistrement dans le log de synchronisation
        for r in returns:
            self._apply_product_returns(returns=r, products=[product])
        self.session.flush()
        self._sync_product_variations(product)
        self.session.commit()

        has_valid_wc_id = bool(product.wpwc_id)
        has_batch_effect = any(
            bool(r.get("create") or r.get("update"))
            for r in returns
        )
        status = self._get_product_sync_status(has_batch_effect, has_valid_wc_id)

        if status == "error":
            logger.warning(
                "Produit %d non synchronisé vers WooCommerce: un retour valide a été reçu " +
                "mais aucun wc_id n'a été attribué. Retour=%s",
                product_id,
                returns,
            )
        else:
            logger.info(
                "Produit %d synchronisé vers WooCommerce: statut=%s, wc_id=%s.",
                product_id,
                status,
                product.wpwc_id,
            )
        return product.wpwc_id if status == "success" else None

    def fetch_all_wc_products(self) -> list[dict[str, Any]]:
        """Récupère tous les produits WooCommerce, page par page, avec pagination."""
        all_products: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self.api_read.get("products", params={"page": page, "per_page": 100})
            payload = response.json()
            if not payload:
                break
            all_products.extend(payload)
            page += 1
        return all_products

    def export_all_products(self):
        """
        Exporte la dernière version des produits vers WooCommerce.
        - Créations : stocke l'wpwc_id retourné sur l'objet local + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog (wpwc_id déjà connu).
        - Suppressions : efface wpwc_id sur l'objet local (désactivé) + trace dans ObjectSyncLog.
        """
        products = self.object_repo.get_all(only_actives=True)
        logger.info("Export de %d produits vers WooCommerce...", len(products))
        for p in products:
            self._build_product_payload(p)
        wpwc_products = self.fetch_all_wc_products()
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
                    wpwc_id=p.wpwc_id,
                    operation="batch",
                    sync_status="error",
                    error_message=str(exc)
                )
            self.session.commit()
            return
        for r in returns:
            self._apply_product_returns(r, products)
        try:
            for product in products:
                self._sync_product_variations(product)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Erreur lors de la synchronisation des variations WooCommerce : %s",
                exc,
            )
            for product in products:
                self._log_sync(
                    entity_type="object",
                    entity_id=product.id,
                    wpwc_id=product.wpwc_id,
                    operation="batch",
                    sync_status="error",
                    error_message=str(exc),
                )
            self.session.commit()
            return
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
        - Créations : stocke l'wpwc_id retourné sur le tag local + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog.
        - Suppressions : efface wpwc_id sur le tag local + trace dans ObjectSyncLog.
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
                self._log_sync("tag", t.id, t.wpwc_id, "batch", "error", str(exc))
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
        - Créations : stocke l'wpwc_id retourné sur l'image locale + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog.
        - Suppressions : efface wpwc_id sur l'image locale + trace dans ObjectSyncLog.
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
                self._log_sync("media", p.id, p.wpwc_id, "batch", "error", str(exc))
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
                (wpwc for wpwc in wpwc_tags if int(wpwc["id"]) == int(t.wpwc_id or 0)),
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
                (wpwc for wpwc in wpwc_pictures if int(wpwc["id"]) == int(p.wpwc_id or 0)),
                None
            )
            src = self._build_media_src(p)
            name = os.path.basename(p.file_link or "") or p.file_link or ""
            if matched:
                entry = {
                    "id": int(matched["id"]),
                    "name": name,
                    "alt": p.alt_text or "",
                    "src": src,
                }
                data["update"].append(entry)
                wpwc_picture_ids.remove(int(entry["id"]))
            else:
                entry = {
                    "name": name,
                    "alt": p.alt_text or "",
                    "src": src,
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
                (wpwc for wpwc in wpwc_objects if int(wpwc["id"]) == int(o.wpwc_id or 0)),
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
                v.wpwc_id = t["id"]
                is_unchanged = (
                    float(matched.get("rate", 0)) == float(v.rate)
                    and matched.get("name") == v.label
                    and matched.get("class") == target_class
                )
                if not is_unchanged:
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

    @staticmethod
    def _validate_current_vat_slugs(vat_rates: Sequence[VatRate]) -> None:
        """Vérifie qu'une seule TVA en vigueur utilise chaque slug WooCommerce."""
        rates_by_slug: dict[str, list[VatRate]] = {}
        for vat_rate in vat_rates:
            slug = vat_rate.wpwc_slug or slugify(vat_rate.label)
            rates_by_slug.setdefault(slug, []).append(vat_rate)
        duplicates = {
            slug: rates
            for slug, rates in rates_by_slug.items()
            if len(rates) > 1
        }
        if not duplicates:
            return
        details = ", ".join(
            f"{slug} ({', '.join(str(rate.id) for rate in rates)})"
            for slug, rates in duplicates.items()
        )
        raise ValueError(f"Slugs WooCommerce dupliqués pour les TVA en vigueur : {details}.")

    def export_vat_rates(self, name: Optional[str] = None) -> bool:
        """
        Exporte les taux de TVA vers WooCommerce.
        - Crée d'abord les classes de taxe WC manquantes (une par taux, slug dérivé du label).
        - Créations : stocke wpwc_id retourné sur le VatRate local + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog.
        - Suppressions : efface wpwc_id sur le VatRate local + trace dans ObjectSyncLog.

        Arguments:
            name (str, optional): Le nom du taux de TVA à exporter. Si None, exporte tous les taux.
        """
        now = datetime.now(timezone.utc)
        stmt = select(VatRate).where(
            VatRate.date_start <= now,
            or_(
                VatRate.date_end == None,  # pylint: disable=singleton-comparison
                VatRate.date_end > now,
            ),
        )
        if name:
            stmt = stmt.where(VatRate.label == name)
        vat_rates = self.session.execute(stmt).scalars().all()
        self._validate_current_vat_slugs(vat_rates)
        self._ensure_wc_tax_classes(vat_rates)
        wpwc_vat_rates: list[dict[str, Any]] = self.api_read.get("taxes").json()
        data = self.__diff_vat_rates(vat_rates, wpwc_vat_rates)
        if not any(data.values()):
            self.session.commit()
            logger.info("Export taux de TVA ignoré : WooCommerce est déjà à jour.")
            return False
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
            return False
        self._apply_vat_returns(returns, vat_rates)
        self.session.commit()
        logger.info(
            "Export taux de TVA terminé. Créés: %d, Mis à jour: %d, Supprimés: %d",
            len(returns.get("create", [])),
            len(returns.get("update", [])),
            len(returns.get("delete", [])),
        )
        return True

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
            select(Tags).where(Tags.wpwc_id == None)  # pylint: disable=singleton-comparison
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
                int(wpwc["id"]) == int(local_product.wpwc_id or 0)
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
                int(wpwc["id"]) == int(local_file.wpwc_id or 0)
                for wpwc in wpwc_media
            ):
                logger.info(
                    "Média '%s' (ID %d) manquant dans WooCommerce. Création en cours.",
                    local_file.file_link,
                    local_file.id
                )
                self.export_pictures()
