"""Services Dilicom structurés par domaine métier.

Le package expose une API publique compatible avec l'ancien import:
    from db_models.services.dilicom import DilicomService

Les services spécialisés sont regroupés dans les classes ci-dessous et le service
principal hérite des spécialisations pour garder une façade unique.
"""

from .base import DilicomServiceBase


class DilicomServiceBook(DilicomServiceBase):
    """Service dédié au traitement des retours livres / ONIX."""

    _books_target_path = DilicomServiceBase._books_target_path
    send_updates = DilicomServiceBase.send_updates
    fetch_returns = DilicomServiceBase.fetch_returns
    _build_refel_content = DilicomServiceBase._build_refel_content
    _update_synced = DilicomServiceBase._update_synced
    _get_metadatas_from_onix = DilicomServiceBase._get_metadatas_from_onix
    _get_values_from_onix = DilicomServiceBase._get_values_from_onix
    _update_books = DilicomServiceBase._update_books


class DilicomServiceSupplier(DilicomServiceBase):
    """Service dédié au traitement des fournisseurs / distributeurs."""

    _clear_directory = DilicomServiceBase._clear_directory
    _update_distributors = DilicomServiceBase._update_distributors
    _generate_supplier_from_distributor_line = (
        DilicomServiceBase._DilicomServiceBase__generate_supplier_from_distributor_line
    )
    _update_services = DilicomServiceBase._update_services


class DilicomService(DilicomServiceBook, DilicomServiceSupplier):
    """Façade publique de traitement Dilicom.

    La logique métier est portée par les sous-services spécialisés tout en
    conservant une API unique pour le reste du code.
    """

    pass


__all__ = [
    "DilicomService",
    "DilicomServiceBase",
    "DilicomServiceBook",
    "DilicomServiceSupplier",
]
