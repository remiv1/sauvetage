"""Test unitaire pour la classe Customers dans db_models.objects.customers."""

from sqlalchemy.orm import Session
from db_models.objects.customers import (
    Customers, CustomerPros, CustomerAddresses, CustomerMails, CustomerPhones)
from tests.fake_datas.sqlite_fixture import db_session, engine  # pylint: disable=unused-import # type: ignore

def test_customer_create_read_and_update(db_session: Session) -> None:    # pylint: disable=redefined-outer-name
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

def test_create_complete_customer(db_session: Session) -> None:    # pylint: disable=redefined-outer-name
    """test de création d'un client complet avec tous les champs"""
    customer = Customers(
        wpwc_id="1",
        henrri_id="2",
        customer_type="pro"
    )
    db_session.add(customer)
    db_session.flush()
    customer_pro = CustomerPros(
        customer_id=customer.id,
        company_name="Test Company",
        siret_number="12345678901234",
        vat_number="FR01123456789"
    )
    addresses = [
        CustomerAddresses(
            customer_id=customer.id,
            address_name="Domicile",
            address_line1="123 Rue de Test",
            city="Testville",
            state="Test State",
            postal_code="12345",
            country="Test Country",
            is_billing=True,
            is_shipping=False
        ),
        CustomerAddresses(
            customer_id=customer.id,
            address_name="Bureau",
            address_line1="456 Avenue de Test",
            city="Testville",
            state="Test State",
            postal_code="12345",
            country="Test Country",
            is_billing=False,
            is_shipping=True
        )
    ]
    mails = [
        CustomerMails(
            customer_id=customer.id,
            email_name="Principal",
            email="john.doe@example.com"
        ),
        CustomerMails(
            customer_id=customer.id,
            email_name="Secondaire",
            email="john.secondary@example.com"
        )
    ]
    phones = [
        CustomerPhones(
            customer_id=customer.id,
            phone_name="Mobile",
            phone_number="+1234567890"
        ),
        CustomerPhones(
            customer_id=customer.id,
            phone_name="Fixe",
            phone_number="+0987654321"
        )
    ]
    db_session.add(customer_pro)
    db_session.add_all(addresses)
    db_session.add_all(mails)
    db_session.add_all(phones)
    db_session.commit()
    # Vérification de la création du client et de ses relations
    created_customer = db_session.query(Customers).where(Customers.id == customer.id).first()
    assert created_customer is not None
    assert created_customer.wpwc_id == "1"
    assert created_customer.henrri_id == "2"
    assert created_customer.customer_type == "pro"
    assert created_customer.pro is not None
    assert created_customer.pro.company_name == "Test Company"
    assert created_customer.pro.siret_number == "12345678901234"
    assert created_customer.pro.vat_number == "FR01123456789"
    assert len(created_customer.addresses) == 2
    assert len(created_customer.mails) == 2
    assert len(created_customer.phones) == 2
    assert created_customer.addresses[0].address_name == "Domicile"
    assert created_customer.addresses[0].is_billing is True
    assert created_customer.addresses[0].is_shipping is False
    assert created_customer.addresses[1].address_name == "Bureau"
    assert created_customer.addresses[1].is_billing is False
    assert created_customer.addresses[1].is_shipping is True
    assert created_customer.mails[0].email_name == "Principal"
    assert created_customer.mails[0].email == "john.doe@example.com"
