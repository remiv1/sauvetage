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
from henrri_connect.models import Document, DocumentLine
from henrri_connect.exc import HenrriError
from db_models.services.henrri import (
    HenrriProductsService,
    HenrriCustomersService,
    HenrriDocumentsService,
    sync_customer_to_henrri,
    sync_product_to_henrri,
)
from db_models.objects.invoices import Invoice

logger = logging.getLogger(__name__)


def _build_henrri_document_for_creation(invoice: Invoice) -> Document:
    """Construit un document Henrri sans lignes pour l'API de création."""
    payload = invoice.to_dict_henrri()
    payload.pop("lines", None)
    return Document(**payload)


def _log_henrri_business_error(
    *,
    invoice: Invoice,
    message: str,
    exc: Exception,
    step: str,
    product_id: str | int | None = None,
) -> None:
    """Journalise une erreur métier Henrri dans la collection métier dédiée."""
    metadata: dict[str, Any] = {
        "invoice_id": getattr(invoice, "id", None),
        "step": step,
        "exception_type": type(exc).__name__,
        "error": str(exc),
    }
    if product_id is not None:
        metadata["product_id"] = product_id
    logger.exception(
        message,
        extra={
            "log_type": "metiers",
            "action": "henrri_sync",
            "resource_type": "invoice",
            "resource_id": str(getattr(invoice, "id", "unknown")),
            "status_code": _extract_status_code(exc),
            "obj_metadata": metadata,
        },
    )


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

    Le client, les produits et le document sont créés (POST) ou mis à jour (PUT)
    selon la présence d'un identifiant Henrri. Une facture déjà finalisée chez
    Henrri n'est pas modifiée.

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

    # ——— Synchronisation du client et des produits ———
    _sync_customer_step(invoice, hcs)
    _sync_products_step(invoice, hps)

    # ——— Création (POST) ou mise à jour (PUT) de la facture ———
    try:
        document_id, remote_document = _upsert_henrri_document(invoice, hds)
    except HenrriSyncError:
        raise
    except Exception as e:
        _log_henrri_business_error(
            invoice=invoice,
            message="Erreur lors de la création de la facture Henrri",
            exc=e,
            step="document",
        )
        raise HenrriSyncError(
            f"Échec création facture: {e}",
            status_code=_extract_status_code(e),
            details=_extract_error_details(e),
            step="document",
        ) from e

    if remote_document is not None and remote_document.finalized:
        logger.info(
            "Facture Henrri %s déjà finalisée, aucune modification appliquée",
            document_id,
        )
        return remote_document, invoice

    _create_missing_lines(invoice, hds, document_id)

    # ——— Finalisation de la facture ———
    try:
        finalized = hds.finalize_document(document_id)
    except Exception as e:
        _log_henrri_business_error(
            invoice=invoice,
            message="Erreur lors de la finalisation de la facture Henrri %s",
            exc=e,
            step="finalize",
        )
        raise HenrriSyncError(
            f"Échec finalisation facture: {e}",
            status_code=_extract_status_code(e),
            details=_extract_error_details(e),
            step="finalize",
        ) from e

    return finalized, invoice


def _sync_customer_step(invoice: Invoice, hcs: HenrriCustomersService) -> None:
    """Synchronise le client de la facture chez Henrri (POST ou PUT)."""
    try:
        sync_customer_to_henrri(invoice.customer, hcs)
    except Exception as e:
        _log_henrri_business_error(
            invoice=invoice,
            message="Erreur lors de la synchronisation du client Henrri",
            exc=e,
            step="customer",
        )
        raise HenrriSyncError(
            f"Échec synchronisation client: {e}",
            status_code=_extract_status_code(e),
            details=_extract_error_details(e),
            step="customer",
        ) from e


def _sync_products_step(invoice: Invoice, hps: HenrriProductsService) -> None:
    """Synchronise les produits facturés chez Henrri (POST ou PUT)."""
    seen = set()
    for line in invoice.lines:
        product = (
            line.order_line.invoice_fee_product
            if line.order_line.is_shipping_fee
            else line.order_line.general_object
        )
        if product in seen:
            continue
        seen.add(product)
        try:
            sync_product_to_henrri(product, hps)
        except Exception as e:
            _log_henrri_business_error(
                invoice=invoice,
                message="Erreur synchronisation produit %s Henrri: %s",
                exc=e,
                step="product",
                product_id=product.id,
            )
            raise HenrriSyncError(
                f"Échec synchronisation produit {product.id}: {e}",
                status_code=_extract_status_code(e),
                details=_extract_error_details(e),
                step="product",
            ) from e


def _create_missing_lines(
    invoice: Invoice,
    hds: HenrriDocumentsService,
    document_id: int,
) -> None:
    """Crée chez Henrri les lignes de facture qui n'y sont pas encore."""
    for local_line in invoice.lines:
        if local_line.henrri_id:
            logger.debug("Ligne %s déjà créée sur Henrri", local_line.reference)
            continue

        try:
            henrri_line = DocumentLine(**local_line.to_dict_henrri())
            created_line = hds.add_line(document_id, henrri_line)
        except Exception as e:
            _log_henrri_business_error(
                invoice=invoice,
                message="Erreur création ligne %s Henrri",
                exc=e,
                step="lines",
            )
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


def _upsert_henrri_document(
    invoice: Invoice,
    hds: HenrriDocumentsService,
) -> tuple[int, Document | None]:
    """Crée la facture chez Henrri, ou met à jour son en-tête si elle existe déjà."""
    if not invoice.henrri_id:
        created = hds.create_document(_build_henrri_document_for_creation(invoice))
        if created.id is None:
            raise HenrriSyncError(
                "Facture créée mais sans ID",
                step="document",
                details={"created": str(created)},
            )
        invoice.henrri_id = str(created.id)
        return created.id, created

    document_id = int(invoice.henrri_id)
    existing = hds.get_document(document_id)
    if existing.finalized:
        return document_id, existing

    updated = hds.modify_document(document_id, _build_henrri_document_for_creation(invoice))
    return document_id, updated


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

def find_invoice(ext_id: str) -> Document:
    """Retrouve une facture chez Henrri."""
    hds = HenrriDocumentsService()
    try:
        return hds.get_document(int(ext_id))
    except Exception as e:
        logger.exception("Erreur lors de la récupération de la facture Henrri %s", ext_id)
        raise HenrriSyncError(
            f"Échec récupération facture {ext_id}: {e}",
            status_code=_extract_status_code(e),
            details=_extract_error_details(e),
            step="document_status",
        ) from e

def get_invoice_pdf(ext_id: str) -> bytes:
    """Récupère une facture PDF chez Henrri."""
    hds = HenrriDocumentsService()
    try:
        return hds.get_pdf_bytes(int(ext_id))
    except Exception as e:
        logger.exception("Erreur lors de la récupération du PDF Henrri %s", ext_id)
        raise HenrriSyncError(
            f"Échec récupération PDF facture {ext_id}: {e}",
            status_code=_extract_status_code(e),
            details=_extract_error_details(e),
            step="pdf",
        ) from e

def check_product(ext_id: str) -> bool:
    """Vérifie l'existence d'un produit chez Henrri."""
    try:
        product_id = int(ext_id)
        service = HenrriProductsService()
        product = service.client.items.get(product_id)
        return product is not None and getattr(product, "id", None) is not None
    except (TypeError, ValueError):
        logger.warning("Identifiant produit Henrri invalide: %s", ext_id)
        return False
    except HenrriError as he:
        logger.warning(
            "Erreur Henrri lors de la vérification du produit %s: %s",
            ext_id,
            he,
        )
        return False
    except Exception as exc:  # pragma: no cover - dépendance réseau / API
        logger.warning("Produit Henrri %s introuvable ou inaccessible: %s", ext_id, exc)
        return False


def check_customer(ext_id: str) -> bool:
    """Vérifie l'existence d'un client chez Henrri."""
    try:
        customer_id = int(ext_id)
        service = HenrriCustomersService()
        customer = service.client.customers.get(customer_id)
        return customer is not None and getattr(customer, "id", None) is not None
    except (TypeError, ValueError):
        logger.warning("Identifiant client Henrri invalide: %s", ext_id)
        return False
    except HenrriError as he:
        logger.warning(
            "Erreur Henrri lors de la vérification du client %s: %s",
            ext_id,
            he,
        )
        return False
    except Exception as exc:  # pragma: no cover - dépendance réseau / API
        logger.warning("Client Henrri %s introuvable ou inaccessible: %s", ext_id, exc)
        return False
