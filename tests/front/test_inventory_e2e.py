"""Tests end-to-end du workflow complet d'inventaire.

Parcours testé :
  parse  →  prepare  →  validate  →  commit

Chaque test traverse la pile complète Flask → proxy HTTP → FastAPI → DB.
"""

from decimal import Decimal

from db_models.objects import GeneralObjects, InventoryMovements


# ── helpers ───────────────────────────────────────────────────────────────── #

def _post(client, path, payload):
    return client.post(path, json=payload)


def _parse(client, raw, inventory_type="partial", category="book"):
    return _post(client, "/inventory/data/parse", {
        "raw": raw,
        "inventory_type": inventory_type,
        "category": category,
    })


def _prepare(client, ean13_list, inventory_type="partial"):
    return _post(client, "/inventory/data/prepare", {
        "ean13": ean13_list,
        "inventory_type": inventory_type,
    })


def _validate(client, recon_lines, inventory_type="partial"):
    lines = [
        {
            "ean13": l["ean13"],
            "stock_theorique": l["stock_theorique"],
            "stock_reel": l["stock_reel"],
            "motifs": ["initial_inventory"],
            "commentaire": "test e2e",
        }
        for l in recon_lines
    ]
    return _post(client, "/inventory/data/validate", {
        "lines": lines,
        "inventory_type": inventory_type,
    })


# ── tests ─────────────────────────────────────────────────────────────────── #

class TestInventoryE2E:
    """Workflow e2e d'inventaire à travers la pile complète."""

    def test_workflow_single_product(
        self, client_direction, book_object, fastapi_test_client,   # pylint: disable=unused-argument
    ):
        """Workflow complet avec un seul produit connu, scanné 3 fois."""
        client = client_direction
        ean = book_object.ean13  # "9781234567890"

        # ── 1. Parse ──────────────────────────────────────────────────
        resp = _parse(client, f"{ean},{ean},{ean}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert ean in data["known"]
        assert data["unknown"] == []
        assert len(data["ean13"]) == 3

        # ── 2. Prepare ────────────────────────────────────────────────
        resp = _prepare(client, [ean, ean, ean])
        assert resp.status_code == 200
        recon = resp.get_json()
        assert len(recon) == 1
        line = recon[0]
        assert line["ean13"] == ean
        assert line["title"] == "Test Book"
        assert line["stock_reel"] == 3
        assert line["stock_theorique"] == 0  # pas de mouvement préexistant
        assert line["difference"] == 3

        # ── 3. Validate ──────────────────────────────────────────────
        resp = _validate(client, recon)
        assert resp.status_code == 200
        planned = resp.get_json()["planned"]
        # delta=+3 → 1 mouvement "in" (qty 3) + 1 mouvement "inventory" (qty 3)
        assert len(planned) == 2
        ecart = next(m for m in planned if m["movement_type"] == "in")
        inventaire = next(m for m in planned if m["movement_type"] == "inventory")
        assert ecart["quantity"] == 3
        assert ecart["ean13"] == ean
        assert inventaire["quantity"] == 3

    def test_workflow_with_unknown_product(
        self, client_direction, book_object, fastapi_test_client, db_session_main,  # pylint: disable=unused-argument
    ):
        """Parse détecte un produit inconnu → on le crée → on relance le workflow."""
        client = client_direction
        known_ean = book_object.ean13
        unknown_ean = "9780000000001"
        supplier_id = book_object.supplier_id

        # ── 1. Parse : détecte connu / inconnu ───────────────────────
        resp = _parse(client, f"{known_ean},{unknown_ean}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert known_ean in data["known"]
        assert unknown_ean in data["unknown"]

        # ── 2. Créer le produit inconnu ──────────────────────────────
        resp = _post(client, "/inventory/data/products", {
            "ean13": unknown_ean,
            "name": "Nouveau produit e2e",
            "product_type": "book",
            "supplier_id": supplier_id,
            "author": "Auteur E2E",
            "diffuser": "Diffuseur E2E",
            "editor": "Éditeur E2E",
            "genre": "Test",
            "publication_year": 2025,
            "pages": 200,
            "category": "book",
            "price": 15.0,
        })
        assert resp.status_code == 201
        product = resp.get_json()
        assert product["status"] == "created"
        assert product["ean13"] == unknown_ean

        # ── 3. Re-parse : tous les EAN sont désormais connus ─────────
        resp = _parse(client, f"{known_ean},{unknown_ean},{unknown_ean}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data["known"]) == {known_ean, unknown_ean}
        assert data["unknown"] == []

        # ── 4. Prepare ───────────────────────────────────────────────
        resp = _prepare(client, [known_ean, unknown_ean, unknown_ean])
        assert resp.status_code == 200
        recon = resp.get_json()
        assert len(recon) == 2
        by_ean = {l["ean13"]: l for l in recon}
        assert by_ean[known_ean]["stock_reel"] == 1
        assert by_ean[unknown_ean]["stock_reel"] == 2

        # ── 5. Validate ──────────────────────────────────────────────
        resp = _validate(client, recon)
        assert resp.status_code == 200
        planned = resp.get_json()["planned"]
        # 2 produits × (1 écart + 1 inventaire) = 4 mouvements
        assert len(planned) == 4

    def test_workflow_with_existing_stock(
        self, client_direction, supplier, fastapi_test_client,  # pylint: disable=unused-argument
        db_session_main,
    ):
        """Workflow avec stock préexistant — vérifie le calcul du stock théorique."""
        client = client_direction

        # Créer 2 objets avec des EAN13 valides (13 chiffres)
        obj1 = GeneralObjects(
            supplier_id=supplier.id,
            general_object_type="generic",
            ean13="9780000000011",
            name="Objet stock A",
            description="Objet de test A pour inventaire.",
            price=Decimal("19.99"),
        )
        obj2 = GeneralObjects(
            supplier_id=supplier.id,
            general_object_type="generic",
            ean13="9780000000028",
            name="Objet stock B",
            description="Objet de test B pour inventaire.",
            price=Decimal("25.42"),
        )
        db_session_main.add_all([obj1, obj2])
        db_session_main.flush()

        # Mouvements préexistants :
        #   obj1 : inventory(10) + out(5) → stock_théorique = 5
        #   obj2 : in(3) (pas d'inventaire initial) → stock_théorique = 3
        db_session_main.add_all([
            InventoryMovements(
                general_object_id=obj1.id, movement_type="inventory",
                quantity=10, price_at_movement=Decimal("19.99"),
                source="supplier", destination="stock",
                notes="inventaire initial obj1",
            ),
            InventoryMovements(
                general_object_id=obj1.id, movement_type="out",
                quantity=5, price_at_movement=Decimal("19.99"),
                source="stock", destination="customer",
                notes="vente obj1",
            ),
            InventoryMovements(
                general_object_id=obj2.id, movement_type="in",
                quantity=3, price_at_movement=Decimal("25.42"),
                source="supplier", destination="stock",
                notes="réception obj2",
            ),
        ])
        db_session_main.flush()

        ean1, ean2 = obj1.ean13, obj2.ean13

        # On scanne : obj1 ×3, obj2 ×4
        scanned = [ean1] * 3 + [ean2] * 4

        # ── Parse ░────────────────────────────────────────────────────
        resp = _parse(client, ",".join(scanned))
        assert resp.status_code == 200
        assert set(resp.get_json()["known"]) == {ean1, ean2}

        # ── Prepare ──────────────────────────────────────────────────
        resp = _prepare(client, scanned)
        assert resp.status_code == 200
        recon = resp.get_json()
        by_ean = {l["ean13"]: l for l in recon}

        # obj1 : attendu stock_théorique=5, stock_réel=3, diff=-2
        assert by_ean[ean1]["stock_theorique"] == 5
        assert by_ean[ean1]["stock_reel"] == 3
        assert by_ean[ean1]["difference"] == -2

        # obj2 : attendu stock_théorique=3, stock_réel=4, diff=+1
        assert by_ean[ean2]["stock_theorique"] == 3
        assert by_ean[ean2]["stock_reel"] == 4
        assert by_ean[ean2]["difference"] == 1

        # ── Validate ─────────────────────────────────────────────────
        resp = _validate(client, recon)
        assert resp.status_code == 200
        planned = resp.get_json()["planned"]
        # obj1 diff=-2 → mouvement "out" (qty 2) + "inventory" (qty 3)
        # obj2 diff=+1 → mouvement "in"  (qty 1) + "inventory" (qty 4)
        assert len(planned) == 4

        mvt_types = {(m["ean13"], m["movement_type"]): m["quantity"] for m in planned}
        assert mvt_types[(ean1, "out")] == 2
        assert mvt_types[(ean1, "inventory")] == 3
        assert mvt_types[(ean2, "in")] == 1
        assert mvt_types[(ean2, "inventory")] == 4
