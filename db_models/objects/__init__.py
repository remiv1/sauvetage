"""Module d'initialisation pour les modèles d'objets de la base de données.
Ce module importe tous les modèles d'objets pour les rendre facilement accessibles à partir
d'autres parties de l'application.
"""

from .common import QueryMixin
from .customers import (
    Customers,
    CustomerMails,
    CustomerPhones,
    CustomerAddresses,
    CustomerSyncLog,
    CustomerParts,
    CustomerPros,
)
from .orders import Order, OrderLine
from .stocks import OrderIn, OrderInLine, DilicomReferencial
from .inventory import InventoryMovements
from .invoices import Invoice, InvoiceLine
from .shipments import Shipment, ShipmentLine
from .users import Users, UsersPasswords
from .objects import (
    GeneralObjects,
    Books,
    OtherObjects,
    Tags,
    ObjectTags,
    ObjMetadatas,
    MediaFiles,
)
from .vat import VatRate
from .suppliers import Suppliers
