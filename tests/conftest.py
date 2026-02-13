"""La configuration de pytest pour les tests unitaires du projet."""
pytest_plugins = [
    "tests.fixtures.sqlite_fixture",
    "tests.fixtures.f_customers",
    "tests.fixtures.f_objects",
    "tests.fixtures.f_orders",
    "tests.fixtures.f_suppliers",
]
