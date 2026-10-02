"""Tests du nettoyage CSV et de l'import SQL dans un conteneur jetable."""

import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateTable

from db_models.objects import Books, GeneralObjects, ObjectTags, Suppliers, Tags

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datas" / "data-seed"
NOTEBOOK = DATA_DIR / "nettoyage_dilicom.ipynb"
SCRIPT = ROOT / "datas" / "import_dilicom.sql"


def notebook_cells() -> list[str]:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    return [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


@pytest.fixture
def cleaned_data(tmp_path, monkeypatch):
    sources = ["dilicom_pas_sur_site.csv", "retour_dilicom.csv"]
    originals = {name: (DATA_DIR / name).read_bytes() for name in sources}
    for name in sources:
        shutil.copyfile(DATA_DIR / name, tmp_path / name)
    monkeypatch.chdir(tmp_path)
    namespace = {}
    for code in notebook_cells():
        exec(compile(code, str(NOTEBOOK), "exec"), namespace)  # pylint: disable=exec-used
    for name, content in originals.items():
        assert (tmp_path / name).read_bytes() == content
    with (tmp_path / "dilicom_pas_sur_site_cleaned.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return tmp_path, namespace, rows


def test_notebook_exports_clean_keywords_and_preserves_sources(cleaned_data):
    _, namespace, rows = cleaned_data
    assert len(rows) == 285
    assert len({row["ean13"] for row in rows}) == 285
    assert list(rows[0]) == ["ean13", "title", "keywords_json", "author", "editor"]
    assert namespace["mapping"] == original_mapping()
    clean = namespace["clean_keywords"]
    assert clean("religion, Religion, , CE, cm, 4e, 6è,") == [
        "Religion", "CE", "CM", "4ème", "6ème",
    ]
    assert clean("BD 10ans, jeunesse lycée, Temoins") == [
        "BD", "10ans", "Jeunesse", "Lycée", "Témoins",
    ]
    assert clean(" ,, ") == []
    tags = {tag for row in rows for tag in json.loads(row["keywords_json"])}
    assert len(tags) == 19
    assert {"Jeunesse", "Religion", "Marie", "Histoire", "CE", "CM", "4ème", "6ème"} <= tags
    for row in rows:
        words = json.loads(row["keywords_json"])
        assert words == list(dict.fromkeys(words))
        assert all(word and word == word.strip() for word in words)
    assert namespace["valid_ean13"]("9791093096896")
    assert not namespace["valid_ean13"]("9791093096897")


def original_mapping() -> dict[str, str]:
    import ast  # pylint: disable=import-outside-toplevel

    notebook = json.loads((DATA_DIR / "concat_datas.ipynb").read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        for node in ast.parse("".join(cell["source"])).body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "mapping"
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
    raise AssertionError("Dictionnaire de corrections introuvable.")


@pytest.fixture
def sql_database(cleaned_data):
    container = os.environ.get("DILICOM_TEST_CONTAINER")
    if not container:
        pytest.skip("Définir DILICOM_TEST_CONTAINER pour les tests SQL isolés.")
    if not container.startswith("sauv-dilicom-validation-"):
        pytest.fail("Les tests SQL exigent un conteneur de validation jetable.")
    database = "dilicom_" + uuid4().hex

    def command(*args, **kwargs):
        return subprocess.run(
            ["podman", "exec", "-i", container, "psql", "-X", "-v", "ON_ERROR_STOP=1",
             "-U", "postgres", *args],
            text=True, capture_output=True, check=True, **kwargs,
        )

    def query(sql):
        return command("-d", database, "-At", input=sql).stdout.strip()

    command("-d", "postgres", "-c", f"CREATE DATABASE {database}")
    try:
        tables = [Suppliers, GeneralObjects, Books, Tags, ObjectTags]
        ddl = "CREATE SCHEMA app_schema;\n" + "\n".join(
            str(CreateTable(model.__table__).compile(dialect=dialect())) + ";"
            for model in tables
        )
        query(ddl)
        directory, namespace, rows = cleaned_data
        for path in [directory / "dilicom_pas_sur_site_cleaned.csv", directory / "retour_dilicom.csv", SCRIPT]:
            subprocess.run(
                ["podman", "cp", str(path), f"{container}:/tmp/{path.name}"],
                text=True, capture_output=True, check=True,
            )
        glns = sorted(namespace["links_df"]["Gencod distrib"].unique())
        for gln in glns:
            query(
                "INSERT INTO app_schema.suppliers "
                "(name, gln13, is_active, edi_active, created_at, updated_at) "
                f"VALUES ('Supplier {gln}', '{gln}', true, false, NOW(), NOW());"
            )

        def run_import(apply=None, check=True):
            variables = [] if apply is None else ["-v", f"apply={'true' if apply else 'false'}"]
            return subprocess.run(
                ["podman", "exec", container, "psql", "-X", "-U", "postgres",
                 "-d", database, *variables, "-f", "/tmp/import_dilicom.sql"],
                text=True, capture_output=True, check=check,
            )

        def replace_objects(updated_rows):
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(updated_rows)
            path = directory / "dilicom_pas_sur_site_cleaned.csv"
            path.write_text(buffer.getvalue(), encoding="utf-8")
            subprocess.run(
                ["podman", "cp", str(path), f"{container}:/tmp/{path.name}"],
                text=True, capture_output=True, check=True,
            )

        yield query, run_import, replace_objects, rows
    finally:
        command("-d", "postgres", "-c", f"DROP DATABASE {database}")


def test_sql_simulation_does_not_persist(sql_database):
    query, run_import, _, _ = sql_database
    result = run_import()
    assert "Simulation terminee" in result.stdout
    assert query(
        "SELECT (SELECT count(*) FROM app_schema.general_objects), "
        "(SELECT count(*) FROM app_schema.books), (SELECT count(*) FROM app_schema.tags), "
        "(SELECT count(*) FROM app_schema.object_tags)"
    ) == "0|0|0|0"


def test_sql_import_creates_all_objects_active_with_transaction_dates(sql_database):
    query, run_import, _, rows = sql_database
    run_import(apply=True)
    assert query("SELECT count(*) FROM app_schema.general_objects") == "285"
    assert query(
        "SELECT count(*) FROM app_schema.general_objects "
        "WHERE is_active AND general_object_type = 'book' AND description = '' "
        "AND created_at = updated_at AND created_at = last_inventory_timestamp"
    ) == "285"
    assert query(
        "SELECT count(*) FROM app_schema.books AS b JOIN app_schema.general_objects AS g "
        "ON g.id = b.general_object_id WHERE b.created_at = g.created_at "
        "AND b.updated_at = g.updated_at"
    ) == "285"
    assert query(
        "SELECT count(*) FROM app_schema.tags WHERE is_active AND created_at = updated_at"
    ) == "19"
    expected_links = sum(len(json.loads(row["keywords_json"])) for row in rows)
    assert query(
        "SELECT count(*) FROM app_schema.object_tags AS t JOIN app_schema.general_objects AS g "
        "ON g.id = t.general_object_id WHERE t.created_at = g.created_at "
        "AND t.updated_at = g.updated_at"
    ) == str(expected_links)


def test_sql_import_ignores_existing_objects_and_is_repeatable(sql_database):
    query, run_import, replace_objects, rows = sql_database
    existing = rows[0]["ean13"]
    query(
        "INSERT INTO app_schema.general_objects "
        "(supplier_id, general_object_type, ean13, name, description, purchase_price, "
        "is_active, created_at, updated_at, last_inventory_timestamp) "
        f"VALUES ((SELECT min(id) FROM app_schema.suppliers), 'book', '{existing}', "
        "'Ancien titre', 'Ancienne description', 9.50, false, "
        "'2000-01-01', '2000-01-01', '2000-01-01');"
        "INSERT INTO app_schema.books (general_object_id, author, created_at, updated_at) "
        "SELECT id, 'Ancien auteur', '2000-01-01', '2000-01-01' FROM app_schema.general_objects;"
        "INSERT INTO app_schema.tags (name, description, is_active, created_at, updated_at) "
        "VALUES ('Religion', 'Existant', false, '2000-01-01', '2000-01-01');"
    )
    rows[0]["keywords_json"] = '["Tag réservé à la fiche ignorée"]'
    replace_objects(rows)
    assert "Import valide et enregistre" in run_import(apply=True).stdout
    assert query("SELECT count(*) FROM app_schema.general_objects") == "285"
    assert query("SELECT count(*) FROM app_schema.books") == "285"
    assert query(
        f"SELECT name, description, purchase_price, is_active, created_at::date "
        f"FROM app_schema.general_objects WHERE ean13 = '{existing}'"
    ) == "Ancien titre|Ancienne description|9.50|f|2000-01-01"
    assert query(
        "SELECT count(*) FROM app_schema.object_tags AS t JOIN app_schema.general_objects AS g "
        f"ON g.id = t.general_object_id WHERE g.ean13 = '{existing}'"
    ) == "0"
    assert query("SELECT count(*) FROM app_schema.tags WHERE name = 'Tag réservé à la fiche ignorée'") == "0"
    assert query(
        "SELECT s.gln13 FROM app_schema.general_objects AS g "
        "JOIN app_schema.suppliers AS s ON s.id = g.supplier_id WHERE g.ean13 = '9791028538484'"
    ) == "3013861600100"
    assert query(
        "SELECT count(*) FROM app_schema.general_objects "
        f"WHERE ean13 <> '{existing}' AND is_active AND created_at = updated_at "
        "AND created_at = last_inventory_timestamp"
    ) == "284"
    assert query("SELECT is_active, created_at::date FROM app_schema.tags WHERE name = 'Religion'") == "f|2000-01-01"
    expected_links = sum(len(json.loads(row["keywords_json"])) for row in rows[1:])
    assert query("SELECT count(*) FROM app_schema.object_tags") == str(expected_links)
    snapshots = {
        table: query(f"SELECT row_to_json(t) FROM app_schema.{table} AS t ORDER BY id")
        for table in ["general_objects", "books", "tags", "object_tags"]
    }
    run_import(apply=True)
    for table, snapshot in snapshots.items():
        assert query(f"SELECT row_to_json(t) FROM app_schema.{table} AS t ORDER BY id") == snapshot


@pytest.mark.parametrize(
    "failure",
    ["supplier", "duplicate", "json", "keyword", "ean", "missing_return", "book_constraint"],
)
def test_sql_invalid_inputs_abort_without_partial_import(sql_database, failure):
    query, run_import, replace_objects, rows = sql_database
    if failure == "supplier":
        query("DELETE FROM app_schema.suppliers WHERE gln13 = '3017000002108'")
    elif failure == "duplicate":
        rows.append(dict(rows[0]))
    elif failure == "json":
        rows[0]["keywords_json"] = '{"not": "an array"}'
    elif failure == "keyword":
        rows[0]["keywords_json"] = '[""]'
    elif failure == "ean":
        rows[0]["ean13"] = "9791093096897"
    elif failure == "book_constraint":
        query("ALTER TABLE app_schema.books ADD CHECK (author = 'Auteur impossible')")
    else:
        rows[0]["ean13"] = "4006381333931"
    replace_objects(rows)
    result = run_import(apply=True, check=False)
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert query("SELECT count(*) FROM app_schema.general_objects") == "0"
    assert query("SELECT count(*) FROM app_schema.books") == "0"
    assert query("SELECT count(*) FROM app_schema.tags") == "0"
