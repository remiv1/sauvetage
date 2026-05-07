"""
Module de services pour l'intégration avec WooCommerce.
La base de données locale est source unique de vérité pour les produits,
et WooCommerce est utilisé pour exposer ces produits à l'extérieur.

TODO : implémenter les méthodes.

Le schéma métier est le suivant :
- Export des produits (dernière version) vers WooCommerce en cas de changements.
- Récupération des commandes depuis WooCommerce pour traitement dans l'outil local.
- Mise à jour du statut des commandes dans WooCommerce en fonction du traitement local.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from woocommerce import API
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from db_models.objects.vat import VatRate
from db_models.objects.objects import ObjectSyncLog, MediaFiles
from db_models.config.woocommerce import WooCommerceConfig, load_woocommerce_config
from db_models.repositories.objects import ObjectsRepository, GeneralObjects
from db_models.repositories.tags import TagsRepository, Tags
from db_models.services.utils import slugify

logger = logging.getLogger(__name__)

class WCService:
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
        self.session = session
        if separated_keys:
            self.config_read: WooCommerceConfig = load_woocommerce_config(direction="r")
            self.config_write: WooCommerceConfig = load_woocommerce_config(direction="w")
            self.api_read: API = API(
                url=self.config_read.base_url,
                consumer_key=self.config_read.consumer_key,
                consumer_secret=self.config_read.consumer_secret,
                wp_api=self.config_read.wp_api,
                verify_ssl=self.config_read.verify_ssl,
                version=self.config_read.version
            )
            self.api_write: API = API(
                url=self.config_write.base_url,
                consumer_key=self.config_write.consumer_key,
                consumer_secret=self.config_write.consumer_secret,
                wp_api=self.config_write.wp_api,
                verify_ssl=self.config_write.verify_ssl,
                version=self.config_write.version
            )
        else:
            self.config: WooCommerceConfig = load_woocommerce_config(direction="rw")
            self.api_read: API = API(
                url=self.config.base_url,
                consumer_key=self.config.consumer_key,
                consumer_secret=self.config.consumer_secret,
                wp_api=self.config.wp_api,
                verify_ssl=self.config.verify_ssl,
                version=self.config.version
            )
            self.api_write = self.api_read
        self.object_repo = ObjectsRepository(self.session)
        self.tag_repo = TagsRepository(self.session)

    def _log_sync(
        self,
        entity_type: str,
        entity_id: Optional[int],
        wpwc_id: Optional[int],
        operation: str,
        sync_status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Enregistre une entrée dans le journal de synchronisation WooCommerce."""
        log = ObjectSyncLog(
            entity_type=entity_type,
            entity_id=entity_id,
            wpwc_id=wpwc_id,
            operation=operation,
            sync_status=sync_status,
            error_message=error_message,
            synced_at=datetime.now(timezone.utc),
        )
        self.session.add(log)

    def _build_product_payload(self, p: GeneralObjects) -> dict[str, Any]:
        """Construit le dictionnaire WooCommerce pour un produit (enrichi des sous-objets)."""
        product = p.to_dict(is_woo_commerce=True)
        meta = p.obj_metadatas.to_dict(is_woo_commerce=True) if p.obj_metadatas else None
        other_object = p.other_object.to_dict(is_woo_commerce=True) if p.other_object else None
        book = p.book.to_dict(is_woo_commerce=True) if p.book else None
        product["meta_data"] |= meta["meta_data"] if meta else product["meta_data"]
        if other_object:
            product["meta_data"] |= other_object["meta_data"]
        if book:
            product["meta_data"] |= book["meta_data"]
        object_tags = [tag.to_dict(is_woo_commerce=True) for tag in p.object_tags]
        if object_tags:
            product["tags"] = object_tags
        return product

    def _apply_product_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        products: Sequence[GeneralObjects],
    ) -> None:
        """Traite les retours batch WooCommerce pour les produits."""
        for item in returns.get("create", []):
            sku = item.get("sku")
            matching = next(
                (p for p in products if p.ean13 and str(p.ean13) == str(sku or "")),
                None,
            )
            if matching:
                matching.id_wpwc = int(item["id"])
            self._log_sync(
                entity_type="object",
                entity_id=matching.id if matching else None,
                wpwc_id=int(item["id"]),
                operation="create",
                sync_status="success"
                )
        for item in returns.get("update", []):
            wpwc_id = int(item["id"])
            matching = next((p for p in products if p.id_wpwc == wpwc_id), None)
            self._log_sync(
                entity_type="object",
                entity_id=matching.id if matching else None,
                wpwc_id=wpwc_id,
                operation="update",
                sync_status="success"
            )
        for item in returns.get("delete", []):
            wpwc_id = int(item["id"])
            local_obj = self.session.execute(
                select(GeneralObjects).where(GeneralObjects.id_wpwc == wpwc_id)
            ).scalar_one_or_none()
            if local_obj:
                local_obj.id_wpwc = None
            self._log_sync(
                entity_type="object",
                entity_id=local_obj.id if local_obj else None,
                wpwc_id=wpwc_id,
                operation="delete",
                sync_status="success"
            )

    def _apply_tag_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        tags: Sequence[Tags],
    ) -> None:
        """Traite les retours batch WooCommerce pour les tags."""
        for item in returns.get("create", []):
            matching = next((t for t in tags if t.name == item.get("name")), None)
            if matching:
                matching.id_wpwc = int(item["id"])
            self._log_sync(
                entity_type="tag",
                entity_id=matching.id if matching else None,
                wpwc_id=int(item["id"]),
                operation="create",
                sync_status="success"
            )
        for item in returns.get("update", []):
            wpwc_id = int(item["id"])
            matching = next((t for t in tags if t.id_wpwc == wpwc_id), None)
            self._log_sync(
                entity_type="tag",
                entity_id=matching.id if matching else None,
                wpwc_id=wpwc_id,
                operation="update",
                sync_status="success"
            )
        for item in returns.get("delete", []):
            wpwc_id = int(item["id"])
            local_tag = self.session.execute(
                select(Tags).where(Tags.id_wpwc == wpwc_id)
            ).scalar_one_or_none()
            if local_tag:
                local_tag.id_wpwc = None
            self._log_sync(
                entity_type="tag",
                entity_id=local_tag.id if local_tag else None,
                wpwc_id=wpwc_id,
                operation="delete",
                sync_status="success"
            )

    def export_products(self):
        """
        Exporte la dernière version des produits vers WooCommerce.
        - Créations : stocke l'id_wpwc retourné sur l'objet local + trace dans ObjectSyncLog.
        - Mises à jour : trace uniquement dans ObjectSyncLog (id_wpwc déjà connu).
        - Suppressions : efface id_wpwc sur l'objet local (désactivé) + trace dans ObjectSyncLog.
        """
        products = self.object_repo.get_all(only_actives=True)
        for p in products:
            self._build_product_payload(p)
        wpwc_products = self.api_read.get("products").json()
        data = self.__diff_objects(products, wpwc_products)
        try:
            returns: dict[str, list[dict[str, Any]]] = (
                self.api_write.post("products/batch", data=data).json()
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Erreur lors de l'export des produits vers WooCommerce : %s", exc)
            for p in products:
                self._log_sync("object", p.id, p.id_wpwc, "batch", "error", str(exc))
            self.session.commit()
            return
        self._apply_product_returns(returns, products)
        self.session.commit()
        logger.info(
            "Export produits terminé. Créés: %d, Mis à jour: %d, Supprimés: %d",
            len(returns.get("create", [])),
            len(returns.get("update", [])),
            len(returns.get("delete", [])),
        )

    def get_orders(self):
        """Récupère les commandes depuis WooCommerce."""
        # Implémenter la logique pour récupérer les commandes depuis WooCommerce
        raise NotImplementedError("Méthode get_orders non implémentée")

    def get_customer_info(self, customer_id):
        """Récupère les informations d'un client depuis WooCommerce."""
        # Implémenter la logique pour récupérer les informations d'un client depuis WooCommerce
        raise NotImplementedError("Méthode get_customer_info non implémentée")

    def update_order(self, order_id, status):
        """Met à jour le statut d'une commande dans WooCommerce."""
        # Implémenter la logique pour mettre à jour le statut d'une commande dans WooCommerce
        raise NotImplementedError("Méthode update_order non implémentée")

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
            logger.error("Erreur lors de l'export des tags vers WooCommerce : %s", exc)
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
        """Exporte les images vers WooCommerce."""
        # Implémenter la logique pour exporter les images vers WooCommerce
        raise NotImplementedError("Méthode export_pictures non implémentée")


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
                    "name": p.file_name,
                    "alt": p.alt_text or "",
                    "src": p.file_link or "",
                }
                data["update"].append(entry)
                wpwc_picture_ids.remove(int(entry["id"]))
            else:
                entry = {
                    "name": p.file_name,
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
        ) -> dict[str, list[dict[str, Any]]]:
        """Calcule les différences entre les objets locaux et ceux de WooCommerce."""
        data: dict[str, list[dict[str, Any]]] = {"create": [], "update": [], "delete": []}
        wpwc_object_ids = {int(obj["id"]) for obj in wpwc_objects}
        for o in objects:
            matched = next(
                (wpwc for wpwc in wpwc_objects if int(wpwc["id"]) == int(o.id_wpwc or 0)),
                None
            )
            if matched:
                entry = o.to_dict(is_woo_commerce=True)
                entry["id"] = int(matched["id"])
                data["update"].append(entry)
                wpwc_object_ids.remove(int(entry["id"]))
            else:
                data["create"].append(o.to_dict(is_woo_commerce=True))
        for wpwc_id in wpwc_object_ids:
            data["delete"].append({"id": wpwc_id})
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
            matched = next(
                (wpwc for wpwc in wpwc_vat_rates if int(wpwc["id"]) == int(v.wpwc_id or 0)),
                None
            )
            if matched:
                t = {
                    "id": int(matched["id"]),
                    "rate": str(v.rate),
                    "name": v.label,
                    "class": "standard" if v.code == 30 else "taux-reduit",
                }
                data["update"].append(t)
                wpwc_vat_ids.remove(int(t["id"]))
            else:
                t = {
                    "rate": str(v.rate),
                    "name": v.label,
                    "class": "standard" if v.code == 30 else "taux-reduit",
                }
                data["create"].append(t)
        for wpwc_id in wpwc_vat_ids:
            data["delete"].append({"id": wpwc_id})
        return data

    def _apply_vat_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        vat_rates: Sequence[VatRate],
    ) -> None:
        """Traite les retours batch WooCommerce pour les taux de TVA."""
        for item in returns.get("create", []):
            matching = next(
                (v for v in vat_rates if float(v.rate) == float(item.get("rate", -1))),
                None,
            )
            if matching:
                matching.wpwc_id = int(item["id"])
            self._log_sync(
                entity_type="vat_rate",
                entity_id=matching.id if matching else None,
                wpwc_id=int(item["id"]),
                operation="create",
                sync_status="success"
            )
        for item in returns.get("update", []):
            wpwc_id = int(item["id"])
            matching = next((v for v in vat_rates if v.wpwc_id == wpwc_id), None)
            self._log_sync(
                entity_type="vat_rate",
                entity_id=matching.id if matching else None,
                wpwc_id=wpwc_id,
                operation="update",
                sync_status="success"
            )
        for item in returns.get("delete", []):
            wpwc_id = int(item["id"])
            local_vat = self.session.execute(
                select(VatRate).where(VatRate.wpwc_id == wpwc_id)
            ).scalar_one_or_none()
            if local_vat:
                local_vat.wpwc_id = None
            self._log_sync(
                entity_type="vat_rate",
                entity_id=local_vat.id if local_vat else None,
                wpwc_id=wpwc_id,
                operation="delete",
                sync_status="success"
            )

    def export_vat_rates(self, name: Optional[str] = None) -> None:
        """
        Exporte les taux de TVA vers WooCommerce.
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
        wpwc_vat_rates: list[dict[str, Any]] = self.api_read.get("taxes").json()
        data = self.__diff_vat_rates(vat_rates, wpwc_vat_rates)
        try:
            returns: dict[str, list[dict[str, Any]]] = (
                self.api_write.post("taxes/batch", data=data).json()
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Erreur lors de l'export des taux de TVA vers WooCommerce : %s", exc)
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
