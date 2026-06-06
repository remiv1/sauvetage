"""Modèles de services pour Henrri."""

from henrri_connect import SyncHenrriClient
from .utils import HenrriConfig

class HenrriService:
    """Service de base pour les échanges avec Henrri."""

    def __init__(self):
        key = HenrriConfig().api_key
        secret = HenrriConfig().api_secret
        url = HenrriConfig().api_url
        if url:
            self.client: SyncHenrriClient = SyncHenrriClient(key, secret, base_url=url)
        else:
            self.client: SyncHenrriClient = SyncHenrriClient(key, secret)
