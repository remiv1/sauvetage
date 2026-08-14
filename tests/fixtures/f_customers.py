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
def professional_customer() -> Customers:
    """Client pro réutilisable pour les contrats Henri."""
    customer = Customers(wpwc_id="42", henrri_id="7", customer_type="pro", is_active=True)
    customer.pro = CustomerPros(
        customer_id=1,
        company_name="ACME SAS",
        siret_number="12345678901234",
        vat_number="FR01123456789",
    )
    customer.emails = [
        CustomerMails(
            customer_id=1,
            email_name="Henri",
            email="contact@acme.fr",
            is_active=True,
        )
    ]
    customer.phones = [
        CustomerPhones(
            customer_id=1,
            phone_name="Henri",
            phone_number="0102030405",
            is_active=True,
        )
    ]
    customer.addresses = [
        CustomerAddresses(
            customer_id=1,
            address_name="Facturation",
            address_line1="12 rue du Test",
            address_line2="Bâtiment A",
            city="Paris",
            state="IDF",
            postal_code="75001",
            country="France",
            is_billing=True,
            is_shipping=False,
            is_active=True,
        )
    ]
    return customer


@pytest.fixture
def individual_customer() -> Customers:
    """Client particulier réutilisable pour les contrats Henri."""
    customer = Customers(
        wpwc_id="43",
        henrri_id="8",
        customer_type="part",
        is_active=True,
    )
    customer.part = CustomerParts(
        customer_id=2,
        first_name="Alice",
        last_name="Martin",
    )
    customer.emails = [
        CustomerMails(
            customer_id=2,
            email_name="Henri",
            email="alice@example.com",
            is_active=True,
        )
    ]
    customer.phones = [
        CustomerPhones(
            customer_id=2,
            phone_name="Henri",
            phone_number="0601020304",
            is_active=True,
        )
    ]
    customer.addresses = [
        CustomerAddresses(
            customer_id=2,
            address_name="Domicile",
            address_line1="8 avenue de la Paix",
            address_line2="",
            city="Lyon",
            state="Auvergne-Rhône-Alpes",
            postal_code="69000",
            country="France",
            is_billing=True,
            is_shipping=True,
            is_active=True,
        )
    ]
    return customer


@pytest.fixture
def wc_customer_pro() -> Customers:
    """Client pro réutilisable pour les payloads WooCommerce."""
    customer = Customers(wpwc_id="42", customer_type="pro")
    customer.pro = CustomerPros(
        customer_id=999,
        company_name="ACME",
        siret_number="12345678901234",
        vat_number="FR12345678901",
    )
    customer.emails = [
        CustomerMails(
            email_name="WooCommerce",
            email="acme@example.com",
            is_active=True,
        ),
    ]
    customer.phones = [
        CustomerPhones(
            phone_name="WooCommerce",
            phone_number="0102030405",
            is_active=True,
        ),
    ]
    customer.addresses = [
        CustomerAddresses(
            address_name="WooCommerce",
            address_line1="12 rue de l'Étoile",
            address_line2="",
            city="Paris",
            state="IDF",
            postal_code="75001",
            country="FR",
            is_billing=True,
            is_shipping=True,
            is_active=True,
        )
    ]
    return customer


@pytest.fixture
def wc_customer_part() -> Customers:
    """Client particulier réutilisable pour les tests Woo."""
    customer = Customers(wpwc_id="42", customer_type="part")
    customer.part = CustomerParts(
        customer_id=1,
        first_name="Alice",
        last_name="Martin",
    )
    customer.addresses = [
        CustomerAddresses(
            customer_id=1,
            address_name="WooCommerce",
            address_line1="12 rue des Fables",
            address_line2="",
            city="Paris",
            state="IDF",
            postal_code="75000",
            country="FR",
            is_billing=True,
            is_shipping=True,
            is_active=True,
        )
    ]
    customer.emails = [
        CustomerMails(
            customer_id=1,
            email_name="WooCommerce",
            email="alice@example.com",
            is_active=True,
        ),
    ]
    customer.phones = [
        CustomerPhones(
            customer_id=1,
            phone_name="WooCommerce",
            phone_number="0601020304",
            is_active=True,
        ),
    ]
    return customer


@pytest.fixture
def customer_pair() -> list[Customers]:
    """Paire de clients de test pour les scénarios CRUD."""
    primary = Customers(wpwc_id="1", henrri_id="2", customer_type="pro", is_active=True)
    secondary = Customers(
        wpwc_id="ojg54561",
        henrri_id="oe65v06b5g106e",
        customer_type="part",
        is_active=True,
    )
    return [primary, secondary]


@pytest.fixture
def complete_customer_pro(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
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
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
) -> Customers:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un client particulier complet avec tous les champs."""
    customer = Customers(wpwc_id="2", henrri_id="3", customer_type="part")
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
            customer_id=customer.id, phone_name="Mobile", phone_number="+1234567894"
        ),
        CustomerPhones(
            customer_id=customer.id, phone_name="Fixe", phone_number="+0987654324"
        ),
    ]
    db_session_main.add(customer_part)
    db_session_main.add_all(addresses)
    db_session_main.add_all(emails)
    db_session_main.add_all(phones)
    db_session_main.commit()
    return customer
