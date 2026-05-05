"""Module de configuration pour l'intégration avec WooCommerce."""

from os import getenv
from dataclasses import dataclass

@dataclass
class WooCommerceConfig:
    """Classe de configuration pour l'intégration avec WooCommerce."""
    base_url: str
    consumer_key: str
    consumer_secret: str
    wp_api: bool = True
    verify_ssl: bool = True
    version: str = "wc/v3"

def load_woocommerce_config(direction: str) -> WooCommerceConfig:
    """
    Charge la configuration de WooCommerce à partir des variables d'environnement.
    Args:
        direction (str): "r" pour lecture, "w" pour écriture, "rw" pour les deux.
    Returns:
        WooCommerceConfig: La configuration chargée.
    """
    if direction not in ("r", "w", "rw"):
        raise ValueError("Direction must be 'r', 'w', or 'rw'.")
    if direction == "r":
        key = getenv("WOOCOMMERCE_READER_KEY", "your_reader_key")
        secret = getenv("WOOCOMMERCE_READER_SECRET", "your_reader_secret")
    elif direction == "w":
        key = getenv("WOOCOMMERCE_WRITER_KEY", "your_writer_key")
        secret = getenv("WOOCOMMERCE_WRITER_SECRET", "your_writer_secret")
    else: # "rw"
        key = getenv("WOOCOMMERCE_CONSUMER_KEY", "your_consumer_key")
        secret = getenv("WOOCOMMERCE_CONSUMER_SECRET", "your_consumer_secret")

    return WooCommerceConfig(
        base_url=getenv("WOOCOMMERCE_BASE_URL", "https://api.woocommerce.com"),
        consumer_key=key,
        consumer_secret=secret,
        verify_ssl=getenv("WOOCOMMERCE_VERIFY_SSL", "False").lower() in ("true", "1", "t"),
        version=getenv("WOOCOMMERCE_VERSION", "wc/v3"),
        wp_api=getenv("WOOCOMMERCE_WP_API", "True").lower() in ("true", "1", "t")
    )
