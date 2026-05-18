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
from typing import Any, Optional, Sequence
from requests.exceptions import RequestException
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session
from db_models.objects.vat import VatRate
from db_models.repositories.objects import ObjectsRepository, GeneralObjects
from db_models.repositories.tags import TagsRepository, Tags
from db_models.repositories.objects.media import MediaRepository, MediaFiles
from db_models.services.utils import slugify
from db_models.services.woo_commerce.base import WCBase

logger = logging.getLogger(__name__)

object_type_mapping = {
    "book": [19],
    "cd": [21, 22],
    "dvd": [21, 23],
    "games": [24, 25],
    "spiritual_object": [24, 26],
    "other": [24],
}

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
            product_dict |= product.book.to_dict_for_woo_commerce()
        if product.other_object:
            product_dict |= product.other_object.to_dict_for_woo_commerce()
        if product.obj_metadatas:
            metadata_wc = product.obj_metadatas.to_dict_for_woo_commerce()
            if metadata_wc:
                product_dict |= metadata_wc
        if product.media_files:
            product_dict["images"] = [
                {
                    "src": media.file_url,
                    "name": media.file_name,
                    "alt": f"{product.name} - {media.alt_text or media.file_name}"
                }
                for media in product.media_files
            ]
        return product_dict

    def _apply_product_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        products: Sequence[GeneralObjects],
    ) -> None:
        """
        Traite les retours batch WooCommerce pour les produits.
        
        Args:
            returns (dict[str, list[dict[str, Any]]]): Les retours batch WooCommerce.
            products (Sequence[GeneralObjects]): La liste des produits locaux.
        
        Returns:
            None
        """
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

    def _apply_picture_returns(
        self,
        returns: dict[str, list[dict[str, Any]]],
        pictures: Sequence[MediaFiles],
    ) -> None:
        """Traite les retours batch WooCommerce pour les images."""
        for item in returns.get("create", []):
            matching = next(
                (p for p in pictures if p.file_name == item.get("name")), None
            )
            if matching:
                matching.id_wpwc = int(item["id"])
            self._log_sync(
                entity_type="media",
                entity_id=matching.id if matching else None,
                wpwc_id=int(item["id"]),
                operation="create",
                sync_status="success"
            )
        for item in returns.get("update", []):
            wpwc_id = int(item["id"])
            matching = next((p for p in pictures if p.id_wpwc == wpwc_id), None)
            self._log_sync(
                entity_type="media",
                entity_id=matching.id if matching else None,
                wpwc_id=wpwc_id,
                operation="update",
                sync_status="success"
            )
        for item in returns.get("delete", []):
            wpwc_id = int(item["id"])
            local_media = self.session.execute(
                select(MediaFiles).where(MediaFiles.id_wpwc == wpwc_id)
            ).scalar_one_or_none()
            if local_media:
                local_media.id_wpwc = None
            self._log_sync(
                entity_type="media",
                entity_id=local_media.id if local_media else None,
                wpwc_id=wpwc_id,
                operation="delete",
                sync_status="success"
            )
        self.session.commit()

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
                    "Objet local ID %d correspond à l'objet WooCommerce ID %d. Ajouté à la liste de mise à jour.",
                    o.id,
                    int(matched["id"])
                )
            else:
                batch_data["create"].append(self._build_product_payload(o))
                logger.debug(
                    "Objet local ID %d n'a pas de correspondance dans WooCommerce. Ajouté à la liste de création.",
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
            "Différence calculée entre les objets locaux et WooCommerce : %d à créer, %d à mettre à jour, %d à supprimer",
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
                    local_file.file_name,
                    local_file.id
                )
                self.export_pictures()
