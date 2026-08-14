"""Modèles de services pour Henrri."""

import httpx
from henrri_connect import SyncHenrriClient
from .utils import HenrriConfig

class HenrriService:
    """Service de base pour les échanges avec Henrri."""

    READ_TIMEOUT_SECONDS = 60.0

    def __init__(self):
        key = HenrriConfig().api_key
        secret = HenrriConfig().api_secret
        url = HenrriConfig().api_url
        if url:
            self.client: SyncHenrriClient = SyncHenrriClient(key, secret, base_url=url)
        else:
            self.client: SyncHenrriClient = SyncHenrriClient(key, secret)

        self.client._http = httpx.Client(
            timeout=httpx.Timeout(
                connect=15.0,
                read=self.READ_TIMEOUT_SECONDS,
                write=30.0,
                pool=10.0,
            )
        )
