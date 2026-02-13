"""Test unitaire pour la classe Customers dans db_models.objects.customers."""

from sqlalchemy.orm import Session
from db_models.objects.customers import Customers
from tests.fake_datas.sqlite_fixture import db_session, engine  # pylint: disable=unused-import # type: ignore

def test_customer_creation(db_session: Session) -> None:    # pylint: disable=redefined-outer-name
    """Test de la méthode to_dict de la classe Customers avec des données issues de la fixture."""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="pro", is_active=True)
    db_session.add(customer)
    db_session.commit()
    assert db_session.query(Customers).count() == 1

def test_customer_read(db_session: Session) -> None:    # pylint: disable=redefined-outer-name
    """Test pour vérifier que le client créé est bien retrouvé"""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="pro", is_active=True)
    db_session.add(customer)
    db_session.commit()
    customer = db_session.query(Customers).where(Customers.id==1).first()
    new_customer = Customers(wpwc_id="ojg54561", henrri_id="oe65v06b5g106e", customer_type="part")
    db_session.add(new_customer)
    db_session.commit()
    assert customer.id == 1 if customer else None
    assert customer.customer_type == 'pro' if customer else None
    assert customer.is_active is True if customer else None

def test_new_customer_write(db_session: Session) -> None:    # pylint: disable=redefined-outer-name
    """test de lecture du client rentré précédemment et de modification"""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="pro", is_active=True)
    db_session.add(customer)
    db_session.commit()
    new_customer = Customers(wpwc_id="ojg54561", henrri_id="oe65v06b5g106e", customer_type="part")
    db_session.add(new_customer)
    db_session.commit()
    customer = db_session.query(Customers).where(Customers.id==2).first()
    if customer:
        customer.is_active = False
    db_session.add(customer)
    db_session.commit()
    customer = db_session.query(Customers).where(Customers.id==2).first()
    assert customer.is_active is False if customer else None
    assert customer.customer_type == 'part' if customer else None
