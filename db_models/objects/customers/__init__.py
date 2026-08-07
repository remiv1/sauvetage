"""Package des modèles clients découpés par domaine."""

from .addresses import CustomerAddresses
from .constants import CASCADE_ALL, CUSTOMER_PK
from .customers import Customers
from .mails import CustomerMails
from .parts import CustomerParts
from .phones import CustomerPhones
from .pros import CustomerPros
from .sync_logs import CustomerSyncLog

__all__ = [
    "CUSTOMER_PK",
    "CASCADE_ALL",
    "Customers",
    "CustomerParts",
    "CustomerPros",
    "CustomerAddresses",
    "CustomerMails",
    "CustomerPhones",
    "CustomerSyncLog",
]
