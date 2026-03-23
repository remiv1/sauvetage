"""Package v1 de l'API Sauvetage."""

from .user import router as user_router  # type: ignore
from .inventory import router as inventory_router  # type: ignore
from .dilicom import router  as dilicom_router  # type: ignore
