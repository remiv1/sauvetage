# Roadmap Rétrospective du Projet Sauvetage

## 🔧 Travail de Développement Réalisé

-[X] Configuration Docker multi-conteneurs avec PostgreSQL 18.1, MongoDB 8.2 et Traefik
-[X] Authentification sécurisée avec deux bases de données PostgreSQL séparées (users/main) et permissions granulaires
-[X] Support JSON/JSONB natif dans PostgreSQL pour stockage flexible des données
-[X] Système de logs immuables avec MongoDB et collections annuelles avec TTL automatique
-[X] Module Python `MongoDBLogger` pour enregistrement centralisé des logs avec PyMongo
-[X] Scripts d'initialisation avec substitution de variables d'environnement (`envsubst`)
-[X] Gestion sécurisée des secrets avec fichiers `.env` et patterns `.pattern`
-[X] Health checks intégrés pour tous les services
-[X] Architecture réseau Docker isolée avec `sauv-secure` et `sauv-network`
-[X] Framework FastAPI pour backend et Flask pour frontend avec Gunicorn en production
-[X] Début de création des modèles de données SQLAlchemy pour les entités principales
-[X] Création de la base d'initialisation Alembic pour migrations de schéma
-[X] Création d'un conteneur pour la boutique en ligne (WordPress + WooCommerce) afin d'utiliser les API REST
-[X] Refactorisation de `AuthService` pour utiliser Flask-Session avec PostgreSQL pour la gestion des sessions côté serveur
-[X] Suppression du modèle `UsersSessions` et mise à jour des dépendances associées
-[X] Ajout de la classe `PasswordHasher` pour le hachage et la vérification des mots de passe
-[X] Implémentation de `UserService` pour la gestion des utilisateurs (création, activation, désactivation, permissions)
-[X] Ajout de la classe `ObjectsRepository` avec des méthodes pour interagir avec les objets vendus par la librairie
-[X] Création de nouveaux dépôts pour la gestion des utilisateurs, des fournisseurs, des expéditions et des commandes
-[X] Ajout des services d'authentification et de gestion des utilisateurs
-[X] Ajout des méthodes `to_dict` et `from_dict` pour les modèles Invoice, Order, OrderLine, Shipment, UsersPasswords et UsersSessions
-[X] Ajout des modèles de données pour les commandes, factures, envois et utilisateurs, avec mise à jour des relations entre entités
-[X] Ajout des modèles pour les mouvements d'inventaire et les fournisseurs
-[X] Ajout de nouveaux modèles pour les clients, adresses, emails et téléphones, ainsi qu'une classe générique pour les méthodes communes
-[X] Mise à jour de la documentation sur la gestion des stocks
-[X] Ajout de la gestion des webhooks WooCommerce dans le README du proxy
-[X] Ajout de la configuration Traefik avec PKI interne et scripts de génération de certificats
-[X] Création d'un système de fixtures pytest robuste avec `conftest.py` pour enregistrement global des fixtures
-[X] Correction et amélioration des fixtures pour les commandes, factures et envois
-[X] Mise en place d'une structure de test robuste avec gestion correcte des dépendances entre fixtures
-[X] Tests avec création d'une base SQLite en mémoire pour les tests unitaires et nettoyage par une méthode de cleanup à la fin des tests
-[X] Validation complète de la suite de tests (7 tests passants)

## 📊 Partie Vente (Dossier sales)

- ⏳ Modèles de données pour clients et devis (à implémenter avec SQLAlchemy/Alembic)
- ⏳ API REST pour gestion des prospects et pipeline commercial
- ⏳ Système de génération de devis automatisés (PDF/docx)
- ⏳ Dashboard analytics pour suivi des ventes en temps réel
- ⏳ Notifications et rappels automatiques pour suivi clients
- ⏳ Intégration CRM avec historique des interactions
- ⏳ Permissions et rôles pour équipe commerciale
- ⏳ Export/Import données clients (CSV/Excel)
- ⏳ Rapports mensuels et indicateurs KPI
- ⏳ Système d'archivage des ventes clôturées

---

## 🆕 Évolutions depuis le 13/02/2026

- **Gestion des utilisateurs :** implémentation complète de l'authentification (création, connexion, vérification d'existence), pages et formulaires `login` / `register`, pages de modification et changement de mot de passe, et utilitaires front (`routes`, `forms`, `templates`, `js`).
- **Sécurité des mots de passe :** ajout du hachage et de la vérification des mots de passe côté dépôt (`UsersRepository`) et intégration lors de la création et modification d'utilisateurs.
- **Refactorisation front-end :** réorganisation des assets SCSS/JS (`core/`), séparation des styles et scripts utilisateur (`app_front/static/css/user`, `app_front/static/js/user`), et modernisation des templates associés.
- **Migrations & DB :** création des migrations initiales (Alembic) pour `main` et `users`, automatisation de l'application des migrations au démarrage de l'`app-back` et ajout des scripts d'initialisation SQL pour les environnements de test et production.
- **Tests & CI :** ajout d'une infra de tests (Dockerfile pour tests, `docker-compose.test.yml`, scripts d'init) permettant d'exécuter la suite avec une base SQLite/Postgres et préparation d'un workflow GitHub Actions pour déploiement/tests.
- **Docker et scripts d'exploitation :** mise à jour des `Dockerfile` pour front/back, ajout/ajustement de scripts d'initialisation (`setup-env.sh`, `start_sequence.sh`, `cleanup.sh`, récupération de logs) et génération de fichiers de logs pour faciliter le debug.
- **Améliorations back :** ajout de `app_back/db_connection` et de nouvelles routes API (`app_back/v1/user.py`), corrections de bugs (recherche du premier utilisateur) et refactor des repositories (`db_models/repositories/user.py`).
- **Observabilité & logs :** création/ajout de logs de migration et fichiers de logs front/back pour faciliter les diagnostics.

---

## 🆕 Évolutions depuis le 21/02/2026

> 93 commits · 373 fichiers modifiés · +30 501 / -3 927 lignes

### 🏠 Tableau de bord

- **Dashboard dynamique** avec onglets (`fetch` API) pour données financières, commandes en cours et état du stock en temps réel.
- **Endpoints back-end** dédiés (`/dashboard/data/...`) pour alimenter les widgets.
- **Masquage conditionnel** de la carte Admin sur la page d'accueil selon les permissions de session.

### 👥 Gestion des clients

- **Modèles complets** : `Customers`, `CustomerAddresses`, `CustomerMails`, `CustomerPhones` avec toutes les relations SQLAlchemy.
- **Blueprint `customer`** avec routes CRUD, formulaires WTForms et templates associés.
- **Repository `CustomersRepository`** avec méthodes de recherche et gestion des adresses/contacts.
- **Tests unitaires** : `tests/db_objects/test_customers.py` et `tests/front/test_customer.py`.

### 📦 Gestion des stocks & inventaire

- **Workflow d'inventaire complet** : préparation, validation et commit des mouvements de stock avec gestion des types (`IN`, `OUT`, `ADJUST`).
- **Prix de revient au mouvement** : capture du `price_at_movement` à chaque mouvement d'inventaire.
- **Correction N+1 queries** dans `inventory.py` via requêtes `IN` groupées.
- **Autocomplétion** sur les champs auteur, diffuseur, éditeur, genre dans le formulaire de création d'objet (HTMX + back-end).
- **Gestion des articles à prix zéro** avec interface de correction depuis l'inventaire.
- **Fragments HTMX** pour la gestion des objets et l'autocomplétion (`blueprints/inventory/routes_htmx.py`).
- **Blueprint `inventory`** avec routes, formulaires, utils et templates HTMX dédiés.
- **Tests** : `tests/db_objects/test_inventory.py` et `tests/front/test_inventory.py` (+ e2e).

### 🛒 Gestion des commandes fournisseurs

- **Modèle `OrderIn` / `OrderInLine`** avec statuts (`draft`, `sended`, `received`, `cancelled`).
- **`OrderRepository`** : création, édition, annulation, confirmation, réception partielle avec split de lignes.
- **Workflow complet commandes** : création → confirmation → réception (qty_received / qty_cancelled) → clôture.
- **Blueprint `stock`** découpé en routes spécialisées : `routes_htmx_orders.py`, `routes_htmx_reservations.py`, `routes_htmx_return.py`, `routes_htmx_search.py`, `routes_htmx_council.py`.
- **Gestion des réservations** : workflow dédié avec statuts et retours de réservation.
- **Gestion des retours fournisseur** : saisie des retours avec mouvement d'inventaire inverse automatique.
- **Formulaire de création de commande** avec recherche dynamique fournisseur (HTMX).
- **Vue conseil** (`council`) : tableau de synthèse du stock avec indicateurs.
- **Taux de TVA** : modèle `VatRate`, migration, sélect dynamique dans les formulaires de ligne de commande, calcul du prix moyen pondéré.

### 🏭 Gestion des fournisseurs

- **Blueprint `supplier`** avec routes CRUD, routes HTMX de recherche, formulaires et utils.
- **Modèle `Suppliers`** avec champ GLN13 et migration dédiée.

### 🔗 Intégration Dilicom

- **Module `app_back/v1/dilicom/`** : routes API pour la gestion des commandes Dilicom (`orders.py`).
- **`DilicomReferencialRepository`** : création/suppression de références dans le référentiel Dilicom.
- **Schémas Pydantic** `dilicom.py` pour la validation des données échangées.
- **Planification de tâches** (`to_create` / `to_delete`) avec statuts de synchronisation.

### 📧 Emails & Documents

- **Module `app_back/utils/mails.py`** : envoi d'e-mails transactionnels via SMTP (bons de commande, notifications).
- **Module `app_back/utils/documents.py`** : génération de PDF (bons de commande) via template Jinja2.
- **Templates e-mail** (`templates/emails/purchase_order_email.html`) et **PDF** (`templates/pdf/purchase_order.html`).
- **Route API** `app_back/v1/mails.py` et `app_back/v1/documents.py` exposant les endpoints d'envoi et de génération.
- **Schémas Pydantic** `mails.py`, `documents.py` pour la validation des requêtes.

### 🗄️ Modèles de données & migrations

- **Modèle `VatRate`** avec gestion des périodes de validité (`date_start`, `date_end`).
- **Modèle `Tags`** et `ObjectTags` pour le tagging des articles.
- **Modèle `ObjMetadatas`** avec champ JSONB semi-structuré pour métadonnées flexibles.
- **Modèles `Books`, `OtherObjects`, `Media`** pour les sous-types d'articles.
- **Migration `main`** : tables `customers`, `invoices`, `shipments`, `suppliers`, `tags`, `vat_rates`, `general_objects`, `orders_in`, `orders_in_lines`, `inventory_movements`.
- **Migration `users`** : tables `users`, `users_passwords`, `users_permissions`.
- **Refactorisation des repositories** : `ObjectsRepository`, `OtherObjectsRepository`, `TagsRepository`, `StockRepository` avec méthodes paginées et filtres avancés.

### 🧪 Tests

- **Suite de tests front** (`tests/front/`) : couverture des blueprints `admin`, `customer`, `dashboard`, `inventory`, `order`, `stock`, `supplier`, `user`.
- **Suite de tests DB objects** (`tests/db_objects/`) : `test_customers`, `test_inventory`, `test_objects`, `test_orders`, `test_users`.
- **Scripts de tests** : `run_tests_front.sh`, `run_tests_db_objects.sh` avec rapports HTML.
- **Refactorisation des fixtures** pour utiliser `client_all` (permissions complètes) dans les tests de routes.
- **Rapport qualitatif** ajouté (`REPORT_QUALITATIVE.md`).

### 🔧 Infrastructure & Performance

- **Singleton SQLAlchemy** : `create_engine` déplacé en module-level dans `app_front/config/db_conf.py` et `app_back/db_connection/config.py` pour éviter la saturation des connexions PostgreSQL (`pool_size=5, max_overflow=10`).
- **Correction `pull.rebase=false`** dans `.git/config` pour éviter les boucles de conflits lors des synchronisations.
- **Submodule `sales`** rattaché au dépôt `remiv1/sauvetage_sales` pour la gestion des ventes.
- **Désactivation CSRF** sur les formulaires imbriqués (sous-formulaires WTForms).

**Dernière mise à jour** : 31 mars 2026

> _Note : Cette roadmap est un document vivant et sera mise à jour régulièrement en fonction de l'avancement du projet et des priorités changeantes._
