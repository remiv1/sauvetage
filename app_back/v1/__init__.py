"""Package v1 de l'API Sauvetage."""

from .user import router as user_router
from .inventory import router as inventory_router
from .dilicom import dilicom_router
from .documents import router as documents_router
from .mails import router as mails_router
from .woocommerce import router as woo_commerce_router

__all__ = [
    "user_router",
    "inventory_router",
    "dilicom_router",
    "documents_router",
    "mails_router",
    "woo_commerce_router",
]
