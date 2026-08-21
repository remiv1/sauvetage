"""Services de synchronisation multi-partenaires."""

from .partners import (
    TargetResult,
    sync_all_customers,
    sync_all_products,
    sync_customer,
)

__all__ = [
    "TargetResult",
    "sync_all_customers",
    "sync_all_products",
    "sync_customer",
]
