"""Service public de synchronisation des produits WooCommerce."""

from sqlalchemy.orm import Session

from db_models.repositories.objects import ObjectsRepository
from db_models.repositories.objects.media import MediaRepository
from db_models.repositories.tags import TagsRepository
from db_models.services.woo_commerce.base import WCBase
from .catalog import ProductCatalogMixin
from .exports import ProductExportsMixin
from .payloads import ProductPayloadMixin
from .returns import BatchReturnsMixin
from .vat import VatRatesMixin
from .variations import ProductVariationsMixin


class WCProductsService(
    ProductPayloadMixin,
    BatchReturnsMixin,
    ProductVariationsMixin,
    ProductCatalogMixin,
    ProductExportsMixin,
    VatRatesMixin,
    WCBase,
):
    """Compose les responsabilités de synchronisation des produits WooCommerce."""

    def __init__(self, session: Session, separated_keys: bool = False) -> None:
        """Initialise les clients WooCommerce et les dépôts produits."""
        super().__init__(session, separated_keys)
        self.object_repo = ObjectsRepository(self.session)
        self.tag_repo = TagsRepository(self.session)
        self.media_repo = MediaRepository(self.session)
