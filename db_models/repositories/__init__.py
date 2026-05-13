"""Module de repositories pour la gestion des données de l'application."""

from .objects.objects import ObjectsRepository
from .objects.books import BooksRepository
from .objects.media import MediaRepository
from .objects.media_access_token import MediaAccessTokenRepository
from .objects.obj_metadatas import ObjMetadatasRepository
from .objects.object_tags import ObjectTagsRepository
from .objects.other_objects import OtherObjectsRepository
from .stocks.dilicom import DilicomReferencialRepository
from .stocks.inventory import InventoryRepository
from .stocks.orders import OrderRepository as OrdersSuppliersRepository
from .stocks.stock import StockRepository
from .customers import (
    CustomersRepository,
    CustomerAddressesRepository,
    CustomerMailsRepository,
    CustomerPhonesRepository,
)
from .henrii import *
from .invoices import InvoiceRepository
from .orders import OrdersRepository
from .shipments import ShipmentsRepository
from .suppliers import SuppliersRepository
from .sync_log import SyncLogRepository
from .tags import TagsRepository
from .user import UsersRepository
