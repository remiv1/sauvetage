from unittest.mock import Mock
from mock.mock import Mock
import pytest
import pandas as pd
from pytest_mock import MockerFixture
from db_models.objects.customers import Customers

@pytest.fixture
def customer_data() -> pd.DataFrame:
    """Fixture pour créer un DataFrame de données de clients simulées."""
    data = {
        "wpwc_id": ["az974hdpr672oje39", "bzeof3972foej038éfiFJSIFOé&"],
        "henrri_id": ["pzeof3972foej038éfiFJSIFOé&", "qzeof3972foej038éfiFJSIFOé&"],
        "customer_type": ["pro", "particulier"],
        "is_active": [True, False]
    }
    return pd.DataFrame(data)

@pytest.fixture
def mock_session(mocker: MockerFixture) -> Mock:
    """Fixture pour créer une session de base de données simulée."""
    return mocker.Mock()

def test_customer_to_dict() -> None:
    """Test de la méthode to_dict de la classe Customers."""
    customer = Customers(
        wpwc_id="az974hdpr672oje39",
        henrri_id="pzeof3972foej038éfiFJSIFOé&",
        customer_type="pro",
        is_active=True
    )
    customer_dict = customer.to_dict()
    assert customer_dict["wpwc_id"] == "az974hdpr672oje39"
    assert customer_dict["henrri_id"] == "pzeof3972foej038éfiFJSIFOé&"
    assert customer_dict["customer_type"] == "pro"
    assert customer_dict["is_active"] is True
    assert "created_at" not in customer_dict
    assert "updated_at" not in customer_dict
