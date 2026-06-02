"""Modèles de services pour Henrri."""

from typing import cast
from henrri_connect import HenrriClient
from henrri_connect.connect import _SyncHenrriClient
from .utils import HenrriConfig

class HenrriService:
    """Service de base pour les échanges avec Henrri."""

    def __init__(self):
        key = HenrriConfig().api_key
        secret = HenrriConfig().api_secret
        url = HenrriConfig().api_url
        if url:
            self.client: _SyncHenrriClient = cast(
                _SyncHenrriClient,
                HenrriClient(
                    key,
                    secret,
                    base_url=url,
                    async_mode=False
                )
            )
        else:
            self.client: _SyncHenrriClient = cast(
                _SyncHenrriClient,
                HenrriClient(
                    key,
                    secret,
                    async_mode=False
                )
            )
