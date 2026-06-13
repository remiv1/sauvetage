"""
Module de gestion des rapports entre les commandes et Henrri.

Ce module permet de :
- Générer une facture chez Henrri.
- Retrouver une facture chez Henrri.
- Récupérer une facture PDF chez Henrri.
- Vérifier l'existance d'un produit chez Henrri.
- Vérifier l'existance d'un client chez Henrri.

Fonctions:
- create_invoice(invoice: Invoice): Crée une facture chez Henrri.

Exceptions:
- HenrriSyncError: Erreur lors de la synchronisation avec Henrri.
"""
import logging
from typing import Any
from henrri_connect.models import Document, DocumentLine, Item, Customer
from db_models.services.henrri import (
    HenrriProductsService,
    HenrriCustomersService,
    HenrriDocumentsService,
)
from db_models.objects.invoices import Invoice

logger = logging.getLogger(__name__)


class HenrriSyncError(Exception):
    """Erreur lors de la synchronisation avec Henrri.

    Attributes:
        status_code: Code HTTP de l'erreur (ex: 422, 500).
        message: Message d'erreur lisible.
        details: Détails supplémentaires (corps de la réponse, etc.).
        step: Étape où l'erreur s'est produite (customer, product, document).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: Any = None,
        step: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details
        self.step = step

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.step:
            parts.append(f"[étape: {self.step}]")
        return " ".join(parts)

def create_invoice(invoice: Invoice) -> tuple[Document, Invoice]:
    """
    Crée une facture chez Henrri à partir des données en base métier.

    Arguments:
        invoice: L'objet Invoice contenant les données de la facture.

    Returns:
        Le document créé chez Henrri et l'objet Invoice mis à jour.

    Raises:
        HenrriSyncError: Si une erreur survient lors de la communication avec Henrri.
    """
    hcs = HenrriCustomersService()
    hps = HenrriProductsService()
    hds = HenrriDocumentsService()

    # ——— 1. Validation des clients ———
    try:
        if invoice.customer.henrri_id is None:
            customer = Customer(**invoice.customer.to_dict_henrri())
            henrri_id = hcs.create_customer(customer)
            invoice.customer.henrri_id = henrri_id
    except Exception as e:
        logger.exception("Erreur lors de la création du client Henrri")
        raise HenrriSyncError(
            f"Échec création client: {e}",
            status_code=_extract_status_code(e),
            details=_extract_error_details(e),
            step="customer",
        ) from e

    # ——— 2. Création des produits ———
    seen = set()
    for line in invoice.lines:
        product = line.order_line.general_object
        if product not in seen:
            seen.add(product)
            if product.henrri_id is None:
                try:
                    henrri_item = Item(**product.to_dict_henrri())
                    product_id = hps.create_product(henrri_item)
                    product.henrri_id = product_id
                except Exception as e:
                    logger.exception("Erreur création produit %s Henrri", product.id)
                    raise HenrriSyncError(
                        f"Échec création produit {product.id}: {e}",
                        status_code=_extract_status_code(e),
                        details=_extract_error_details(e),
                        step="product",
                    ) from e

    # ——— 3. Création de la facture (non finalisée, sans lignes) ———
    # Ou récupération si elle existe déjà
    if invoice.henrri_id:
        # La facture existe déjà, on la récupère depuis Henrri
        logger.debug("Facture %s déjà créée sur Henrri, relance des lignes", invoice.henrri_id)
        document_id = int(invoice.henrri_id)
    else:
        try:
            henrri_doc = Document(**invoice.to_dict_henrri())
            logger.debug("Création de la facture: %s", henrri_doc)
            created = hds.create_document(henrri_doc)
        except Exception as e:
            logger.exception("Erreur lors de la création de la facture Henrri")
            raise HenrriSyncError(
                f"Échec création facture: {e}",
                status_code=_extract_status_code(e),
                details=_extract_error_details(e),
                step="document",
            ) from e

        if created.id is None:
            raise HenrriSyncError(
                "Facture créée mais sans ID",
                step="document",
                details={"created": str(created)},
            )

        invoice.henrri_id = str(created.id)
        document_id = created.id

    # ——— 4. Création des lignes via l'endpoint dédié ———
    # (seulement si elles n'existent pas déjà)
    for local_line in invoice.lines:
        if local_line.henrri_id:
            # Ligne déjà créée sur Henrri, on la saute
            logger.debug("Ligne %s déjà créée sur Henrri", local_line.reference)
            continue

        try:
            henrri_line = DocumentLine(**local_line.to_dict_henrri())
            created_line = hds.add_line(document_id, henrri_line)
        except Exception as e:
            logger.exception("Erreur création ligne %s Henrri", local_line.reference)
            raise HenrriSyncError(
                f"Échec création ligne {local_line.reference}: {e}",
                status_code=_extract_status_code(e),
                details=_extract_error_details(e),
                step="lines",
            ) from e

        if created_line.id is None:
            raise HenrriSyncError(
                f"Ligne {local_line.reference} créée mais sans ID",
                step="lines",
                details={"reference": local_line.reference},
            )
        local_line.henrri_id = created_line.id

    # ——— 5. Finalisation de la facture ———
    try:
        finalized = hds.finalize_document(document_id)
    except Exception as e:
        logger.exception("Erreur lors de la finalisation de la facture Henrri %s", document_id)
        raise HenrriSyncError(
            f"Échec finalisation facture: {e}",
            status_code=_extract_status_code(e),
            details=_extract_error_details(e),
            step="finalize",
        ) from e

    return finalized, invoice


def _extract_status_code(exc: Exception) -> int | None:
    """Extrait le code HTTP d'une exception si disponible."""
    status_code: Any = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    response: Any = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    return None


def _extract_error_details(exc: Exception) -> dict | str | None:
    """Extrait les détails d'erreur d'une exception HTTP."""
    body: Any = getattr(exc, "body", None)
    if isinstance(body, dict):
        return body
    if body is not None:
        return str(body)

    response: Any = getattr(exc, "response", None)
    if response is not None:
        json_reader: Any = getattr(response, "json", None)
        if callable(json_reader):
            try:
                details = json_reader()
            except ValueError:
                details = None
            if isinstance(details, dict):
                return details
            if details is not None:
                return str(details)

        text: Any = getattr(response, "text", None)
        if isinstance(text, str):
            return text
    return str(exc)

def find_invoice(ext_id: str) -> Invoice:
    """Retrouve une facture chez Henrri."""
    raise NotImplementedError

def get_invoice_pdf(ext_id: str) -> bytes:
    """Récupère une facture PDF chez Henrri."""
    raise NotImplementedError

def check_product(ext_id: str) -> bool:
    """Vérifie l'existance d'un produit chez Henrri."""
    raise NotImplementedError

def check_customer(ext_id: str) -> bool:
    """Vérifie l'existance d'un client chez Henrri."""
    raise NotImplementedError
