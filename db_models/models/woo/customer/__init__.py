"""
This package contains the models for WooCommerce customers, including data structures
for customer information, billing and shipping addresses, and related metadata.
The models are designed to facilitate the integration of WooCommerce customer data with an
ERP system.
"""

from .customer_get import (
    WCCustomerGet,
)
from .customer_put import (
    WCCustomerPut,
)

__all__ = [
    "WCCustomerGet",
    "WCCustomerPut",
]
