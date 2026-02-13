"""Test unitaire pour la classe Customers dans db_models.objects.customers."""

from os.path import join, dirname, abspath
import pytest
import pandas as pd
from db_models.objects.customers import Customers

DATA_PATH = join(abspath(join(dirname(__file__), '..')), 'fake_datas')

@pytest.fixture
def data_customer() -> pd.DataFrame:
    """Fixture pour créer un DataFrame de données de clients simulées."""
    print(f"Loading data from {join(DATA_PATH, 'customers/customers.csv')}")
    df = pd.read_csv(join(DATA_PATH, 'customers/customers.csv'))  # type: ignore
    df.columns = df.columns.str.strip()  # Supprime les espaces autour des noms de colonnes
    return df

@pytest.fixture
def part_data() -> pd.DataFrame:
    """Fixture pour créer un DataFrame de données de clients simulées."""
    return pd.read_csv(join(DATA_PATH, 'customers/part.csv'))  # type: ignore

@pytest.fixture
def pro_data() -> pd.DataFrame:
    """Fixture pour créer un DataFrame de données de clients simulées."""
    return pd.read_csv(join(DATA_PATH, 'customers/pro.csv'))   # type: ignore

def test_customer_to_dict(customer_data: pd.DataFrame) -> None:
    """Test de la méthode to_dict de la classe Customers avec des données issues de la fixture."""
    # On récupère une ligne de données du DataFrame
    customer_row = customer_data.iloc[0]

    # Création de l'objet Customers à partir des données de la ligne
    customer = Customers(
        wpwc_id=customer_row["wpwc_id"],
        henrri_id=customer_row["henrri_id"],
        customer_type=customer_row["customer_type"],
        is_active=customer_row["is_active"]
    )

    # Conversion de l'objet en dictionnaire
    customer_dict = customer.to_dict()

    # Vérifications des valeurs
    assert customer_dict["wpwc_id"] == customer_row["wpwc_id"]
    assert customer_dict["henrri_id"] == customer_row["henrri_id"]
    assert customer_dict["customer_type"] == customer_row["customer_type"]
    assert customer_dict["is_active"] == customer_row["is_active"]
    assert "created_at" not in customer_dict
    assert "updated_at" not in customer_dict
