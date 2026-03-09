"""Module d'initialisation pour les modèles d'objets de la base de données.
Ce module importe tous les modèles d'objets pour les rendre facilement accessibles à partir
d'autres parties de l'application.
"""
from .common import QueryMixin
from .customers import (
    Customers, CustomerMails, CustomerPhones, CustomerAddresses, CustomerSyncLog,
    CustomerParts, CustomerPros
)
from .orders import Order, OrderLine
from .stocks import OrderIn, OrderInLine
from .inventory import InventoryMovements
from .invoices import Invoice
from .shipments import Shipment
from .users import Users
from .objects import GeneralObjects, Books, OtherObjects, Tags, ObjectTags, ObjMetadatas, MediaFiles
from .suppliers import Suppliers
