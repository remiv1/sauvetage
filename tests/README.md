# Tests (repo)

[<-- Retour à la racine du projet](../README.md)

Informations et scripts pour lancer les tests d'intégration et unitaires.

## Prérequis

- Python 3.12+ (venv recommandé)
- `docker` ou `podman` pour lancer les bases PostgreSQL et MongoDB de test

## Scripts principaux

- `tests/run_db_test_up.sh` : démarre PostgreSQL et MongoDB de test, applique les migrations (main + users) et lance les suites de tests.
- `tests/run_db_test_down_cleanup.sh` : arrête les conteneurs de test (docker/podman) et supprime les caches (`__pycache__`, `.pytest_cache`, `test_migrations` et le fichier XML de résultat).
- `tests/scripts/run_tests_db_objects.sh` : exécute `pytest` sur `tests/db_objects/`, génère `test_results.xml` et appelle l'imprimeur de JUnit.
- `tests/scripts/print_junit_table.py` : parse `test_results.xml` et affiche un tableau lisible des résultats.

## Usage rapide

- Démarrer les bases et lancer les tests :

```bash
bash tests/run_db_test_up.sh
```

- Nettoyer et arrêter les services de test :

```bash
bash tests/run_db_test_down_cleanup.sh
```

## Notes

- Les scripts détectent automatiquement `podman` ou `docker` et choisissent la commande `compose` appropriée.
- Le serveur Postgres de test écoute par défaut sur `127.0.0.1:5433` pour les exécutions locales (cf. `tests/run_db_test_up.sh`).
- MongoDB de test écoute sur `127.0.0.1:27018` ; le lanceur fournit automatiquement `HENRRI_TEST_MONGO_URI` pour le test de concurrence. Un lancement direct de pytest nécessite cette variable et une base de test accessible.
- `test_results.xml` est écrit dans le répertoire `tests/` par le runner ; `print_junit_table.py` l'utilise pour afficher un résumé lisible.

Besoin d'aide ? Ouvrez une issue ou demandez directement dans le projet.

[<-- Retour à la racine du projet](../README.md)
