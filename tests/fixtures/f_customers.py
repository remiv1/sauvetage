"""Module de fixtures pour les tests liés aux clients"""

from datetime import date
import pytest
from sqlalchemy.orm import Session
from db_models.objects import (
    Customers,
    CustomerParts,
    CustomerPros,
    CustomerAddresses,
    CustomerMails,
    CustomerPhones,
)
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type: ignore
    db_session_main,  # pylint: disable=unused-import # type: ignore
    engine,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore


@pytest.fixture
def complete_customer_pro(
    db_session_main: Session,   # pylint: disable=redefined-outer-name, unused-argument
) -> Customers:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un client professionnel complet avec tous les champs."""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="pro")
    db_session_main.add(customer)
    db_session_main.flush()
    customer_pro = CustomerPros(
        customer_id=customer.id,
        company_name="Test Company",
        siret_number="12345678901234",
        vat_number="FR01123456789",
    )
    addresses = [
        CustomerAddresses(
            customer_id=customer.id,
            address_name="Domicile",
            address_line1="123 Rue de Test",
            city="Testville",
            state="Test State Pro",
            postal_code="12345",
            country="Test Country Pro",
            is_billing=True,
            is_shipping=False,
        ),
        CustomerAddresses(
            customer_id=customer.id,
            address_name="Bureau",
            address_line1="456 Avenue de Test",
            city="Testville",
            state="Test State Pro",
            postal_code="12345",
            country="Test Country Pro",
            is_billing=False,
            is_shipping=True,
        ),
    ]
    emails = [
        CustomerMails(
            customer_id=customer.id,
            email_name="Principal",
            email="john.doe@example.com",
        ),
        CustomerMails(
            customer_id=customer.id,
            email_name="Secondaire",
            email="john.secondary@example.com",
        ),
    ]
    phones = [
        CustomerPhones(
            customer_id=customer.id, phone_name="Mobile", phone_number="+1234567890"
        ),
        CustomerPhones(
            customer_id=customer.id, phone_name="Fixe", phone_number="+0987654321"
        ),
    ]
    db_session_main.add(customer_pro)
    db_session_main.add_all(addresses)
    db_session_main.add_all(emails)
    db_session_main.add_all(phones)
    db_session_main.commit()
    return customer


@pytest.fixture
def complete_customer_part(
    db_session_main: Session,   # pylint: disable=redefined-outer-name, unused-argument
) -> Customers:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un client particulier complet avec tous les champs."""
    customer = Customers(wpwc_id="1", henrri_id="2", customer_type="part")
    db_session_main.add(customer)
    db_session_main.flush()
    customer_part = CustomerParts(
        customer_id=customer.id,
        first_name="Jane",
        last_name="Doe",
        date_of_birth=date(1984, 5, 5),
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
            is_shipping=False,
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
            is_shipping=True,
        ),
    ]
    emails = [
        CustomerMails(
            customer_id=customer.id,
            email_name="Principal",
            email="jane.doe@example.com",
        ),
        CustomerMails(
            customer_id=customer.id,
            email_name="Secondaire",
            email="jane.secondary@example.com",
        ),
    ]
    phones = [
        CustomerPhones(
            customer_id=customer.id, phone_name="Mobile", phone_number="+1234567890"
        ),
        CustomerPhones(
            customer_id=customer.id, phone_name="Fixe", phone_number="+0987654321"
        ),
    ]
    db_session_main.add(customer_part)
    db_session_main.add_all(addresses)
    db_session_main.add_all(emails)
    db_session_main.add_all(phones)
    db_session_main.commit()
    return customer
