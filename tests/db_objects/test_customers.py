"""Test unitaire pour la classe Customers dans db_models.objects.customers."""

from db_models.objects.customers import Customers
from db_models.objects.orders import Order, OrderLine
from db_models.objects.objects import GeneralObjects, Books, OtherObjects, MediaFiles, ObjMetadatas, Tags, ObjectTags
from db_models.objects.shipments import Shipment
from db_models.objects.inventory import InventoryMovements
from db_models.objects.invoices import Invoice
from db_models.objects.suppliers import Suppliers
from db_models.objects.users import Users
from tests.fake_datas.sqlite_fixture import db_session, engine

def test_customer_creation(db_session) -> None:
    """Test de la méthode to_dict de la classe Customers avec des données issues de la fixture."""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="pro", is_active=True)
    db_session.add(customer)
    db_session.commit()
    assert db_session.query(Customers).count() == 1

def test_customer_read(db_session) -> None:
    """Test pour vérifier que le client créé est bien retrouvé"""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="pro", is_active=True)
    db_session.add(customer)
    db_session.commit()
    customer = db_session.query(Customers).where(Customers.id==1).first()
    new_customer = Customers(wpwc_id="ojg54561", henrri_id="oe65v06b5g106e", customer_type="part")
    db_session.add(new_customer)
    db_session.commit()

    assert customer.id == 1
    assert customer.customer_type == 'pro'
    assert customer.is_active == True

def test_new_customer_write(db_session) -> None:
    """test de lecture du client rentré précédemment et de modification"""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="pro", is_active=True)
    db_session.add(customer)
    db_session.commit()
    customer = db_session.query(Customers).where(Customers.id==1).first()
    new_customer = Customers(wpwc_id="ojg54561", henrri_id="oe65v06b5g106e", customer_type="part")
    db_session.add(new_customer)
    db_session.commit()
    customer = db_session.query(Customers).where(Customers.id==2).first()
    customer.is_active = False
    db_session.add(customer)
    db_session.commit()
    customer = db_session.query(Customers).where(Customers.id==2).first()
    assert customer.is_active == False
    assert customer.customer_type == 'part'
