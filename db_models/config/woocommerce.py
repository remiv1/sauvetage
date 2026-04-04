"""Module de configuration pour l'intégration avec WooCommerce."""

from os import getenv
from dataclasses import dataclass

@dataclass
class WooCommerceConfig:
    """Classe de configuration pour l'intégration avec WooCommerce."""
    base_url: str
    consumer_key: str
    consumer_secret: str

def load_woocommerce_config() -> WooCommerceConfig:
    """Charge la configuration de WooCommerce à partir des variables d'environnement."""
    return WooCommerceConfig(
        base_url=getenv("WOOCOMMERCE_BASE_URL", "https://api.woocommerce.com"),
        consumer_key=getenv("WOOCOMMERCE_CONSUMER_KEY", "your_consumer_key"),
        consumer_secret=getenv("WOOCOMMERCE_CONSUMER_SECRET", "your_consumer_secret"),
    )
