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

"""
from henrri_connect.models import Document, Item, Customer
from db_models.services.henrri import (
    HenrriProductsService,
    HenrriCustomersService,
    HenrriDocumentsService,
)
from db_models.objects.invoices import Invoice

def create_invoice(invoice: Invoice) -> Document:
    """
    Crée une facture chez Henrri à partir des données en base métier.
    
    Arguments:
    - invoice (Invoice): L'objet Invoice contenant les données de la facture.
    
    Returns:
    - tuple[Document, list[DocumentLine]]: La facture et ses lignes.
    """
    hcs = HenrriCustomersService()
    hps = HenrriProductsService()
    hds = HenrriDocumentsService()
    customer = invoice.customer
    if customer.id_henrri is None:
        customer = Customer(**customer.to_dict_henrri())
        hcs.create_customer(customer)
    for line in invoice.lines:
        if line.order.general_object.id_henrri is None:
            item = Item(**line.order.general_object.to_dict_henrri())
            hps.create_product(item)
    new_document = Document(**invoice.to_dict_henrri())
    return hds.create_document(new_document)

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
