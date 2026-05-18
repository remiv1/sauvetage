# Rapport qualitatif -- Projet Sauvetage

Date : 18 mai 2026

Resume : rapport qualitatif complet couvrant l'etat du code, les decisions architecturales et structurelles, et la qualite globale depuis le debut du projet. Ce rapport integre une mise a jour couvrant 74 commits supplementaires deposes entre le 01/04/2026 et le 18/05/2026 sur les branches `administration_sprint`, `customer_order_sprint`, `dilicom_sprint` et `woocommerce_sprint` (325 fichiers, +32 036 / -2 184 lignes).

---

## Mise a jour -- Sprint du 01/04/2026 au 18/05/2026

### Vue d'ensemble de la periode

| Indicateur | Valeur |
| --- | --- |
| Commits (branche courante) | 74 |
| Fichiers modifies | 325 |
| Insertions | +32 036 |
| Suppressions | -2 184 |
| Branches mergees | 3 (`administration_sprint`, `customer_order_sprint`, `dilicom_sprint`) |
| Branche en cours | `woocommerce_sprint` |
| Fichiers Python (projet) | ~26 700 lignes |
| Templates HTML | 193 |
| Fichiers SCSS | 25 |
| Fonctions de test | 72 (64 front + 8 db_objects) |

### Sprint administration (merge 01/04/2026)

Livraison de l'interface d'administration complete :

- **Gestion des utilisateurs** (`routes_htmx_users.py`, 193 lignes) : creation, modification, desactivation des comptes depuis l'interface admin.
- **Gestion des TVA** (`routes_htmx_vat.py`, 142 lignes) : CRUD des taux de TVA via HTMX.
- **Consultation des logs** (`routes_htmx_logs.py`, 62 lignes) : lecture des logs MongoDB directement dans l'interface.
- `admin/utils.py` (253 lignes) : logique applicative centralisee pour le blueprint admin.
- Configuration TOML ajoutee pour les pages admin (`admin.toml`, `admin/logs.toml`, `admin/users.toml`, `admin/vat.toml`).
- **Pages d'erreur** (`4xx.html`, `5xx.html`) avec illustrations dediees.
- Amelioration des rollbacks SQLAlchemy : ajout de blocs `try/except` manquants dans plusieurs routes.

### Sprint customer_order (merge 10/04/2026)

Livraison complete de la gestion des commandes clients :

- **Blueprint `order`** : creation, edition, liste des commandes avec selection d'adresse (`routes_htmx_create.py` 298 lignes, `order/utils.py` 649 lignes).
- **Factures et expeditions** : gestion du cycle de vie complet depuis la creation jusqu'a l'expedition.
- **Templates PDF** : `customer_order_slip.html` (277 lignes) et `supplier_order_slip.html` (158 lignes) pour les bons de commande.
- **Securite app_back** : decorateurs de controle d'acces ajoutes sur FastAPI (`app_back/config/security.py`).
- **Arret propre du backend** : gestionnaire de signal `SIGTERM` ajoute dans `bootstrap.py` pour eviter les connexions orphelines en production.
- **Configuration SMTP** integree dans le script `setup-env.sh`.
- **Service systemd** : fichiers de configuration pour le deploiement en production (`systemd/sauvetage.service`, `systemd/README.md`).
- **Correctif sessions SQLAlchemy** : `_SessionMain.remove()` enregistre via `@app.teardown_appcontext` dans `app_front/main.py` -- **item roadmap court terme accompli**.
- Refactoring des modales HTML : remplacement des `<button>` par des elements `<dialog>` natifs.

### Sprint dilicom (merge 22/04/2026)

Livraison de l'integration Dilicom SFTP et de la chaine ONIX :

- **`db_models/services/dilicom.py`** (580 lignes) : `DilicomService` complet avec `send_updates()` (envoi des referentiels au format FEL) et `fetch_returns()` (recuperation et ingestion des fiches). L'endpoint `app_back/v1/dilicom/orders.py` est desormais partiellement implemente avec les routes `send-referentials` et `fetch-returns` -- **item roadmap long terme partiellement accompli**.
- **`app_back/scheduler/dilicom_scheduler.py`** (52 lignes) : planificateur pour les taches Dilicom recurrentes.
- **`app_back/v1/dilicom/background_transactions.py`** (90 lignes) : transactions asynchrones Dilicom.
- **SFTP** : connexion, depot de fichiers et lecture des dossiers distants valides par test Jupyter concluant.
- **Bibliotheque `onixlib`** : creation d'une bibliotheque separee pour le parsing des fichiers ONIX (25/04/2026). Definitions des produits ONIX et routage SEO.
- Amelioration du modele fournisseur (champs supplementaires) et du formulaire (annee de publication et pages en `IntegerField` avec validation).
- Nettoyage : suppression des notebooks de test Dilicom obsoletes.
- Documentation technique ajoutee : `DOC TECH REVENDEUR - REF-FEL.pdf`, `Guide pratique ONIX - V07.pdf`, description des tests.
- **Sous-module `datas`** rattache et reference correctement.

### Sprint woocommerce (en cours, 05/05 -- 18/05/2026)

Demarrage de l'integration e-commerce avec WooCommerce :

- **Package `db_models/services/woo_commerce/`** :
  - `products.py` (757 lignes) : export des produits, taux de TVA, tags.
  - `customers.py` (281 lignes) : synchronisation des clients par email.
  - `orders.py` (208 lignes) : gestion des commandes WooCommerce.
  - `base.py` (124 lignes) : classe de base pour les services WooCommerce.
- **`db_models/repositories/sync_log.py`** (227 lignes) : repository de journal de synchronisation.
- **`db_models/repositories/stocks/stock.py`** (268 lignes) : nouveau repository de gestion du stock.
- **`db_models/repositories/objects/variations.py`** (154 lignes) : gestion des variations d'objets.
- **`db_models/config/woocommerce.py`** (43 lignes) : configuration de l'integration WooCommerce.
- **`app_back/v1/woocommerce/`** : module avec transactions en arriere-plan (`background_transactions.py`) et gestion des medias (`media.py`).
- **Migration** `integration_woocommerce_wordpress.py` (174 lignes) : schema base de donnees pour WooCommerce.
- **Gestion des tokens d'acces** WooCommerce.
- **Blueprint `app_front/blueprints/woocommerce/`** : interface front pour la gestion WooCommerce.
- Descriptions detaillees ajoutees sur les modeles `MediaFiles` et objets.

### Infrastructure buyer (WordPress e-commerce)

- **SSL** : script `generate-certs.sh` (64 lignes) pour la generation de certificats TLS.
- **Outils de sauvegarde WordPress** :
  - `buyer/backup/` : service Docker dedie (`Dockerfile`, `entrypoint.sh`, `README.md` 299 lignes).
  - `buyer/tools/backup_wp.py` (177 lignes), `restore_wp.py` (127 lignes), `bkpctl.py` (173 lignes, outil CLI), `functions.py` (218 lignes).
- `buyer/docker-compose.yml` significativement enrichi (+76 lignes).

### Securite et infrastructure

- **Rate limiting login** : middleware Traefik `login-rate-limit` (5 req/10 min, burst 10) sur `/user/login` -- **item roadmap court terme accompli**.
- **Blocage de bots** : regles Traefik bloquant les chemins d'attaque courants (`wp-*`, `.env`, `.git`, `.htaccess`, `.php`, `/actuator`, etc.) avec retour 403.
- **`X-Robots-Tag: noindex`** : en-tete ajoute pour empecher l'indexation.
- Servicedsystemd pour un deploiement production stable.

### Evolution de la dette technique

| Item roadmap | Statut |
| --- | --- |
| `_SessionMain.remove()` via `teardown_appcontext` | ✅ Accompli |
| Rate limiting login | ✅ Accompli (Traefik) |
| Blocage bots Traefik | ✅ Accompli |
| DilicomService implemente | ✅ Accompli partiellement |
| Pages d'erreur 4xx/5xx | ✅ Accompli |
| Service systemd production | ✅ Accompli |
| `print()` de debug (routes_htmx_search.py, routes_htmx.py supplier) | ❌ Toujours present |
| `USER appuser` dans Dockerfiles | ❌ Non traite |
| 3 TODO dashboard (endpoints stubs) | ❌ Toujours presents |
| Pipeline CI/CD (GitHub Actions) | ❌ Non retabli |
| `pytest-cov` / seuil de couverture | ❌ Non configure |
| En-tetes HTTP CSP, HSTS, X-Frame-Options | ❌ Non configures |
| `except Exception` trop larges dans les repositories | ❌ Toujours presents |

---

## Ancienne version du rapport (31 mars 2026)

Resume : rapport qualitatif complet couvrant l'etat du code, les decisions architecturales et structurelles, et la qualite globale suite aux 93 commits deposes entre le 21/02/2026 et le 31/03/2026 (373 fichiers, +30 501 / -3 927 lignes).

---

## 1. Intensite et rythme de travail

Le rythme est reste soutenu et les iterations rapides : fonctionnalites completes (dashboard, clients, commandes fournisseurs, inventaire, Dilicom, emails/PDF) livrees en environ cinq semaines. La masse de code produite (~16 600 lignes Python + 97 templates + 22 fichiers SCSS) depasse le scope habituel d'un prototype.

Points notables :

- Developpement tres fonctionnel-first : les features metier sont operationnelles avant d'etre robustifiees.
- Iterations frequentes sur les memes fichiers (utils.py stock remanie plusieurs fois), signe d'une architecture qui s'ajuste au fil des besoins.
- Problemes d'outillage git repetes (rebases accidentels, `pull.rebase=true` mal configure) ont coute du temps. Corrige en definitive (`pull.rebase=false`).

---

## 2. Decisions structurelles et architecturales

### 2.1 Separation des responsabilites -- bien etablie

La structure en couches est coherente et respectee :

```txt
app_front/blueprints/<module>/
    routes.py          # pages HTML (rendu Jinja)
    routes_data.py     # endpoints JSON (fetch/AJAX)
    routes_htmx*.py    # fragments HTMX
    forms.py           # WTForms
    utils.py           # logique applicative front
db_models/
    objects/           # modeles SQLAlchemy
    repositories/      # acces donnees (pattern Repository)
app_back/v1/           # API FastAPI (routes backend)
```

Cette separation est l'un des points les plus solides du projet : les blueprints ne font pas directement de requetes SQL, les repositories encapsulent toute la logique d'acces aux donnees, et les utils front font le pont entre formulaires et repositories.

### 2.2 Pattern Repository -- implemente proprement

- `BaseRepository` fournit `get_one` / `get_many` generiques.
- Tous les sous-repositories en heritent et ajoutent les methodes metier specifiques.
- Les repositories les plus complexes (`OrderRepository` : 680 lignes, `CustomersRepository` : 424 lignes) restent coherents dans leur interface.
- Usage de `namedtuple` pour les objets de transfert de valeurs (`Order`, `OrderTuple`) evite les dicts non types.

**Point d'attention :** `db_models/repositories/stock.py` (213 lignes) coexiste avec `db_models/repositories/stock/orders.py` -- doublon partiel a clarifier ou fusionner.

### 2.3 Configuration par fichiers TOML -- decision originale et efficace

Chaque page front est decrite par un fichier `.toml` (`pages/<page>.toml`) listant ses CSS, JS et flags (ex. `htmx = true`). Cela permet d'activer/desactiver des ressources par page sans modifier le code Python. Bonne decision pour la maintenabilite des assets.

**Limite :** un flag manquant (`htmx = true` oublie dans `inventory.toml`) peut silencieusement casser toute une fonctionnalite HTMX sans message d'erreur explicite -- difficile a diagnostiquer.

### 2.4 Sessions SQLAlchemy -- probleme resolu, vigilance maintenue

La correction du pattern singleton (`_engine_main` et `_SessionMain` en module-level) a elimine la saturation du pool PostgreSQL. La configuration actuelle (`pool_size=5, max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=1800`) est correcte pour l'usage actuel.

**Risque residuel :** le front utilise `scoped_session` mais aucun `_SessionMain.remove()` n'est enregistre via `@app.teardown_appcontext`. En production avec Gunicorn, les sessions pourraient ne pas etre correctement fermees en fin de requete, conduisant a terme a des connexions orphelines.

### 2.5 Double backend (Flask + FastAPI) -- par design, acceptable

Flask (`app_front`) gere le rendu HTML et les appels HTMX, FastAPI (`app_back`) expose l'API REST. Les deux partagent `db_models/` en commun. Cette architecture est coherente pour un intranet avec un frontend server-side rendering, mais augmente la complexite de deploiement et les risques de duplication de logique entre les deux backends.

### 2.6 HTMX pour les interactions dynamiques -- bon choix contextuel

L'usage de HTMX pour les fragments (recherche fournisseur, formulaires de lignes de commande, autocompletion) reduit la quantite de JavaScript custom necessaire. La structure `routes_htmx*.py` par domaine est lisible. Le recours a `HX-Trigger` pour la communication entre composants (ex. `inventoryObjectCreated`) est une pratique correcte.

---

## 3. Qualite du code

### 3.1 Metriques de base

*Valeurs au 31/03/2026 -- voir section mise a jour pour les valeurs actuelles.*

| Indicateur | Valeur (31/03/2026) | Valeur (18/05/2026) |
| --- | --- | --- |
| Fichiers Python | 159 | ~220 |
| Lignes Python totales | ~16 600 | ~26 700 |
| Templates HTML | 97 | 193 |
| Fichiers SCSS | 22 | 25 |
| Fonctions de test | 93 | 72 (fonctions, 14 fichiers) |

### 3.2 Points positifs

- **Docstrings** : les fonctions des repositories et utils ont quasi-systematiquement une docstring avec `Args` et `Returns` documentes -- bonne tracabilite.
- **Gestion d'erreurs metier** : utilisation correcte de `ValueError` / `RuntimeError` remontees depuis les repositories avec messages explicites.
- **Validation des entrees** : WTForms valide les entrees utilisateur cote formulaire, les repositories valident les preconditions metier (`ValueError` si commande inexistante, si etat incompatible, etc.).
- **Logging utilisateur** : le decorateur `permission_required` logue les acces refuses via `MongoDBLogger`, ce qui est une bonne pratique de tracabilite.
- **Separation des bases** : la base `users/secure` pour l'authentification est distincte de la base applicative `main` -- decision correcte de cloisonnement.

### 3.3 Dette technique identifiee

**`print()` de debug en production (6 occurrences dans le code fonctionnel) :**

- `app_front/blueprints/stock/routes_htmx_search.py` : 4 `print("DEBUG ...")`
- `app_front/blueprints/supplier/routes_htmx.py` : 1 `print(f"Erreur ...")`
- `db_models/repositories/stock/orders.py` : 1 `print("DEBUG Calculated total...")`
- `db_models/repositories/stock/dilicom.py` : 1 `print("Reference Dilicom creee...")`

Ces `print()` polluent les logs Gunicorn et peuvent exposer des informations sensibles. Ils doivent etre remplaces par le logger applicatif (`get_logger()`).

**TODO non implementes (8 occurrences) :**

- `dashboard/routes_data.py` : 3 endpoints retournent des stubs vides -- le dashboard affiche des donnees incompletes.
- `stock/routes.py` : 2 TODO sur le formulaire de mise a jour des prix.
- `stock/routes.py` : 1 TODO sur le formulaire de retour.
- `app_back/v1/dilicom/orders.py` : endpoint Dilicom entierement vide (`pass`).

**Couverture des type hints : 39 %** -- correcte pour un prototype mais insuffisante pour une base de code en croissance. Les repositories ont une meilleure couverture (~60 %) que les blueprints (~25 %).

**`except Exception` trop larges (11 occurrences)** : dans les repositories stock et quelques utils front. Ces blocs capturent toutes les exceptions indistinctement, ce qui peut masquer des bugs. Preferer `except SQLAlchemyError` dans les repositories.

**`inventory.utils` : bloc `except Exception as e` sans re-raise ni log** (ligne 174) -- erreur silencieuse.

### 3.4 Complexite cyclomatique notable

- `app_back/v1/inventory.py` : 550 lignes -- module le plus volumineux du back, a surveiller.
- `db_models/repositories/stock/orders.py` : 680 lignes -- le repository le plus complexe, couvrant creation/edition/annulation/confirmation/reception. Bien structure mais beneficierait d'une separation en sous-classes ou mixins.
- `app_front/blueprints/stock/utils.py` : 460 lignes -- point de passage de toute la logique stock front. Acceptable mais a surveiller si de nouvelles fonctionnalites s'y ajoutent.

---

## 4. Gestion de la securite

### 4.1 Bonnes pratiques en place

- **Secrets hors depot** : `.env` et `.env.*` dans `.gitignore`, fichier `.env.exemple` versionne -- correct.
- **Hashage des mots de passe** : `PasswordHasher` dedie, mots de passe jamais stockes en clair.
- **Controle d'acces granulaire** : decorateur `permission_required` avec 9 niveaux (ADMIN, COMPTA, COMMERCIAL...), logs des acces refuses dans MongoDB.
- **Separation des bases** : authentification sur `db-secure`, donnees applicatives sur `db-main` -- bon cloisonnement.
- **`pool_pre_ping=True`** : evite l'utilisation de connexions perimees.

### 4.2 Risques persistants

- **Dockerfiles sans USER non-root** : les conteneurs `app_front` et `app_back` s'executent en root. En cas de compromission applicative, l'attaquant obtient les droits root dans le conteneur.
- **Absence de CI/CD** : le workflow GitHub Actions a ete supprime (`d8c22e3 - Suppression du workflow`). Il n'y a plus de controle automatique avant merge dans `main`. Les erreurs peuvent partir directement en production.
- **En-tetes de securite HTTP absents** : pas de CSP, HSTS, X-Frame-Options ni X-Content-Type-Options configures dans Flask ou Traefik. Une XSS ou clickjacking reste possible.
- **Pas de scan de dependances** : `pip-audit` ou `safety` non integres. Les `requirements.txt` sont pinnes (bonne pratique) mais les vulnerabilites connues ne sont pas detectees automatiquement.
- **`FLASK_SECRET_KEY` avec valeur par defaut** : `getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")` -- si la variable d'environnement n'est pas definie, la cle de session Flask est previsible.

---

## 5. Infrastructure et deploiement

### 5.1 Points solides

- Orchestration Podman Compose avec 5 services bien definis (`proxy`, `db-main`, `db-logs`, `app-back`, `app-front`).
- Health checks sur tous les services avec retries et timeouts adaptes.
- Traefik comme reverse proxy avec PKI interne -- architecture correcte pour un intranet.
- `migration.py` avec advisory lock PostgreSQL pour eviter les migrations concurrentes lors du demarrage multi-worker -- decision technique avancee et correcte.
- Submodule `sales` rattache a `remiv1/sauvetage_sales` -- bonne separation d'un domaine futur.

### 5.2 Manques

- **Pas de CI/CD** : reconstruction des images, execution des tests et deploiement sont 100 % manuels.
- **Compilation SCSS manuelle** : `npx sass` doit etre lance a la main apres chaque modification de style -- risque d'oubli en production.
- **Pas de monitoring applicatif** : pas de metriques (Prometheus/Grafana), pas d'alerting sur erreurs 5xx, pas de health check applicatif expose.
- **Images construites en root** sans `USER appuser` dans les Dockerfiles.

---

## 6. Tests

### 6.1 Etat actuel

- **93 tests collectes**, repartis en tests front (routes Flask) et tests db_objects (repositories).
- **Fixtures bien structurees** : `tests/fixtures/` avec `f_customers.py`, `f_orders.py`, `f_stock.py`, `f_objects.py`, `f_users.py` -- reutilisables entre les suites.
- **Tests e2e inventaire** (`test_inventory_e2e.py`) : scenario complet de workflow.
- **Rapport HTML** genere par `generate_test_report.py`.

### 6.2 Limites

- **Couverture fonctionnelle non mesuree** : `pytest-cov` n'est pas configure, le pourcentage de lignes couvertes est inconnu.
- **Tests back FastAPI absents** : `tests/back/` ne contient que `__init__.py` -- les routes API (`inventory.py`, `user.py`, `mails.py`, `documents.py`) ne sont pas testees.
- **Pas de tests d'integration inter-couches** entre `app_back` et `app_front`.
- **Tests front limites au statut HTTP** pour la plupart : verifient le code de retour mais pas le contenu ou l'effet en base.

---

## 7. Roadmap qualite (actions concretes prioritaires)

### Court terme (1-2 semaines) -- mise a jour 18/05/2026

1. **Supprimer les `print()` de debug** dans `routes_htmx_search.py` (2 occurrences) et `routes_htmx.py` (supplier) --> les remplacer par `get_logger()`. *Non traite depuis le rapport precedent.*
2. **Ajouter `USER appuser`** dans `Dockerfile.flask` et `Dockerfile.fast` (creer un utilisateur non-root). *Non traite depuis le rapport precedent.*
3. **Implementer les 3 TODO du dashboard** (`routes_data.py`) pour que les widgets affichent des donnees reelles. *Non traite depuis le rapport precedent.*
4. **Finaliser l'endpoint `send_dilicom_order`** (`app_back/v1/dilicom/orders.py`) qui retourne encore `pass`.
5. **Tests WooCommerce** : la branche `woocommerce_sprint` ne dispose d'aucun test couvrant les nouveaux services et repositories WooCommerce.

### Moyen terme (2-6 semaines)

1. **Retablir un pipeline CI** (GitHub Actions) : lint ruff/pylint --> tests pytest --> build image. *Toujours absent.*
2. **Ajouter la compilation SCSS** dans le pipeline CI et dans un hook pre-commit.
3. **Ajouter `pytest-cov`** et viser un seuil minimal de 60 % de couverture.
4. **En-tetes de securite HTTP** : configurer CSP, HSTS, X-Frame-Options dans Traefik (`dynamic/middlewares.yml`). Les regles de blocage de bots et le rate limiting sont en place, mais les en-tetes de protection des navigateurs manquent encore.
5. **Remplacer les `except Exception`** dans les repositories par `except SQLAlchemyError`.
6. **Scanner les dependances** : integrer `pip-audit` dans le CI.
7. **Monitorer la synchronisation WooCommerce** : le repository `sync_log` est cree mais les alertes sur echecs de synchronisation ne sont pas implementees.

### Long terme (1-3 mois)

1. Monitoring applicatif : exposer `/health` et `/metrics` pour Prometheus.
2. Tests API back-end : implementer `tests/back/` avec des tests FastAPI (`TestClient`).
3. Documentation d'architecture (`docs/architecture.md`) decrivant les flux, les services et les decisions de conception -- d'autant plus necessaire avec l'ajout des services WooCommerce et Dilicom.
4. **Separation des responsabilites WooCommerce** : `db_models/services/woo_commerce/products.py` (757 lignes) commence a atteindre une complexite elevee, a surveiller.

---

**Derniere mise a jour** : 18 mai 2026 *(rapport initial : 31 mars 2026)*
