"""Tests de validation du parsing Dilicom ONIX."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from onixlib import Notice

from db_models.objects import VatRate, GeneralObjects, DilicomReferencial, ObjectPrices
from db_models.repositories.objects import ObjectsRepository
from db_models.repositories.stocks.dilicom import DilicomReferencialRepository
from db_models.services.dilicom import DilicomService


def test_price_ht_uses_taxable_amount_when_present() -> None:
    """Le prix HT doit être la base taxable quand ONIX fournit un montant taxable."""
    product = Notice.parse_full(
        Path("documents/back/dilicom/in/DIF499492051/499492051.xml"),
        version="3.0",
    ).products[0]

    service = object.__new__(DilicomService)
    data = service._extract_price_and_vat_from_onix(product)    # pylint: disable=W0212

    assert data["price_ht"] == 9.95
    assert data["vat_rate"] == 5.5


def test_reproduces_dif499492052_price_year_and_metadata() -> None:
    """Le fichier réel de régression doit garder le prix HT, l’année et les ressources d’image."""
    product = Notice.parse_full(
        Path("tests/back/fixtures/dilicom/in/DIF499492052/499492052.xml"),
        version="3.0",
    ).products[0]

    service = object.__new__(DilicomService)
    service.supplier_repo = type(   # type: ignore
        "S",
        (),
        {
            "get_by_gln13": lambda self,
            gln: type(
                "Supplier",
                (),
                {
                    "id": 1,
                    "name": "Supplier"
                }
            )()
        }
    )()
    service.objects_repo = type(   # type: ignore
        "O",
        (),
        {
            "get_current_vat_rates": lambda self: {5.5: 2}
        }
    )()
    service.refresh_vat_rate_cache = lambda: None
    service.vat_rates_by_value = {5.5: 2}

    data = service._extract_price_and_vat_from_onix(product)  # pylint: disable=W0212
    assert data["price_ht"] == 7.58
    assert data["vat_rate"] == 5.5

    publication_year = service._extract_publication_year_from_onix(product)  # pylint: disable=W0212
    assert publication_year == 2021

    onix_data = service._get_values_from_onix(product)  # pylint: disable=W0212
    assert onix_data is not None
    assert onix_data["book"].pages == 80

    metadata = service._get_metadatas_from_onix(product)  # pylint: disable=W0212
    assert metadata["langue"] in {"français", "fre", "fr"}
    assert any("cover" in key.lower() for key in metadata)


def test_dilicom_real_file_extracts_language_collection_dimensions_and_weight_metadata() -> None:
    """
    Le fichier ONIX doit remonter les métadonnées explicites de langue,
    collection, dimensions et poids.
    """
    product = Notice.parse_full(
        Path("documents/back/dilicom/in/DIF492327800/492327800.xml"),
        version="3.0",
    ).products[0]

    service = object.__new__(DilicomService)
    metadata = service._get_metadatas_from_onix(product)  # pylint: disable=W0212

    assert metadata["code_langue"] in {"FRE", "fre", "FR"}
    assert metadata["langue"] in {"français", "fre", "fr"}
    assert "sujets" not in metadata
    assert "sujet" not in metadata
    assert any(
        "ancade" in str(item).lower()
        for item in metadata.get("collections", [])   # type: ignore
    )
    assert metadata["dimensions_mm"] == "210*120*7"
    assert metadata["poids_grammes"] == "115"
    assert "ref_bnf" not in metadata
    assert "notice_bnf" not in metadata


def test_dilicom_extracts_bnf_metadata_when_present() -> None:
    """Les identifiants BNF doivent être remontés quand le fichier ONIX les fournit."""
    product = Notice.parse_full(
        Path("tests/back/fixtures/dilicom/in/DIF499492052/499492052.xml"),
        version="3.0",
    ).products[0]

    service = object.__new__(DilicomService)
    metadata = service._get_metadatas_from_onix(product)  # pylint: disable=W0212

    assert metadata["ref_bnf"] == "FRBNF468557930000005"
    assert metadata["notice_bnf"] == "http://catalogue.bnf.fr/ark:/12148/cb46855793p"


def test_get_values_from_onix_returns_sqlalchemy_object_price() -> None:
    """
    Le dictionnaire métier doit exposer un `ObjectPrices` complet pour la
    persistance du prix courant.
    """
    product = Notice.parse_full(
        Path("tests/back/fixtures/dilicom/in/DIF499492052/499492052.xml"),
        version="3.0",
    ).products[0]

    service = object.__new__(DilicomService)
    service.supplier_repo = type(   # type: ignore
        "S",
        (),
        {
            "get_by_gln13": lambda self,
            gln: type(
                "Supplier",
                (),
                {
                    "id": 1,
                    "name": "Supplier"
                }
            )()
        }
    )()
    service.objects_repo = type(    # type: ignore
        "O",
        (),
        {"get_current_vat_rates": lambda self: {5.5: 2}}
    )()
    service.refresh_vat_rate_cache = lambda: None
    service.vat_rates_by_value = {5.5: 2}

    values = service._get_values_from_onix(product)  # pylint: disable=W0212

    assert values is not None
    assert isinstance(values["object_price"], ObjectPrices)
    assert float(values["object_price"].price) == 7.58
    assert values["object_price"].vat_rate_id == 2


def test_save_or_update_from_object_keeps_taxable_amount_and_vat_rate_id(
    db_session_main: Session,
    supplier,
) -> None:
    """Le prix courant doit conserver la base taxable HT et l'identifiant de TVA associé."""
    vat_5 = VatRate(
        code=1,
        rate=5.5,
        label="Taux réduit",
        date_start=datetime.now(timezone.utc),
    )
    db_session_main.add(vat_5)
    db_session_main.flush()

    repo = ObjectsRepository(db_session_main)
    obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="book",
        ean13="9780000000011",
        name="Livre HT/VAT",
        description="Vérification de la base taxable",
    )

    repo.save_or_update_from_object(
        obj,
        object_price=ObjectPrices(
            price=7.58,
            vat_rate_id=vat_5.id,
        ),
    )

    saved = repo.get_by_ref("9780000000011")
    assert saved is not None
    assert float(saved.get_price()) == 7.58
    assert saved._current_price_row().vat_rate_id == vat_5.id  # pylint: disable=protected-access # type: ignore


def test_dilicom_service_uses_cached_vat_rates(db_session_main: Session) -> None:
    """
    Le service doit charger les TVA actives au début du workflow pour éviter les requêtes répétées.
    """
    vat_5 = VatRate(
        code=1,
        rate=5.5,
        label="Taux réduit",
        date_start=datetime.now(timezone.utc),
    )
    vat_20 = VatRate(
        code=3,
        rate=20.0,
        label="Taux normal",
        date_start=datetime.now(timezone.utc),
    )
    db_session_main.add_all([vat_5, vat_20])
    db_session_main.flush()

    service = object.__new__(DilicomService)
    service.objects_repo = ObjectsRepository(db_session_main)
    service.refresh_vat_rate_cache()

    assert service.vat_rates_by_value[5.5] == vat_5.id
    assert service.vat_rates_by_value[20.0] == vat_20.id
    assert service._get_vat_rate_id("5.50") == vat_5.id  # pylint: disable=W0212


def test_update_status_handles_already_created_reference(
        db_session_main: Session,
        supplier
    ) -> None:
    """Un statut déjà final ne doit plus provoquer une erreur lors de la route de sync."""
    obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="book",
        ean13="9780000000010",
        name="Objet sync",
        description="Objet de test pour la synchronisation Dilicom",
    )
    db_session_main.add(obj)
    db_session_main.flush()

    ref = DilicomReferencial(
        ean13=obj.ean13,
        gln13=supplier.gln13,
        create_ref=True,
        delete_ref=False,
        dilicom_synced=True,
    )
    db_session_main.add(ref)
    db_session_main.flush()

    repo = DilicomReferencialRepository(db_session_main)
    updated = repo.update_status(obj.ean13)

    assert updated.dilicom_synced is True
    assert updated.ean13 == obj.ean13


def test_save_or_update_from_object_is_idempotent_on_same_ean(
    db_session_main: Session,
    supplier,
) -> None:
    """Le même EAN doit être mis à jour plutôt que réinséré plusieurs fois dans la même session."""
    repo = ObjectsRepository(db_session_main)
    first = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="book",
        ean13="9782081222199",
        name="Marlaguette",
        description="version initiale",
    )
    second = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="book",
        ean13="9782081222199",
        name="Marlaguette updated",
        description="version corrigée",
    )

    repo.save_or_update_from_object(
        first,
        object_price=ObjectPrices(price=9.95, vat_rate_id=None),
    )
    repo.save_or_update_from_object(
        second,
        object_price=ObjectPrices(price=12.50, vat_rate_id=None),
    )

    stored = repo.get_by_ref("9782081222199")
    assert stored is not None
    assert stored.name == "Marlaguette updated"
    assert stored.description == "version corrigée"
    assert db_session_main.execute(
        select(func.count())    #pylint: disable=E1102
        .select_from(GeneralObjects)
        .where(GeneralObjects.ean13 == "9782081222199")
    ).scalar_one() == 1
