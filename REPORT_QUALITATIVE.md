# Rapport qualitatif -- Projet Sauvetage

Date : 31 mars 2026

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

| Indicateur | Valeur |
| --- | --- |
| Fichiers Python | 159 |
| Lignes Python totales | ~16 600 |
| Templates HTML | 97 |
| Fichiers SCSS | 22 |
| Tests collectes | 93 |
| Fonctions avec type hints | ~114 / 289 (39 %) |

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

### Court terme (1-2 semaines)

1. **Supprimer les `print()` de debug** dans `routes_htmx_search.py`, `routes_htmx.py` (supplier), `orders.py`, `dilicom.py` --> les remplacer par `get_logger()`.
2. **Enregistrer `_SessionMain.remove()`** via `@app.teardown_appcontext` dans `app_front/main.py` pour eviter les fuites de connexion en production.
3. **Ajouter `USER appuser`** dans `Dockerfile.flask` et `Dockerfile.fast` (creer un utilisateur non-root).
4. **Implementer les 3 TODO du dashboard** (`routes_data.py`) pour que les widgets affichent des donnees reelles.

### Moyen terme (2-6 semaines)

1. **Retablir un pipeline CI** (GitHub Actions) : lint ruff/pylint --> tests pytest --> build image.
2. **Ajouter la compilation SCSS** dans le pipeline CI et dans un hook pre-commit.
3. **Ajouter `pytest-cov`** et viser un seuil minimal de 60 % de couverture.
4. **En-tetes de securite HTTP** : configurer CSP, HSTS, X-Frame-Options dans Traefik (`dynamic/`) ou Flask middleware.
5. **Remplacer les `except Exception`** dans les repositories par `except SQLAlchemyError`.
6. **Scanner les dependances** : integrer `pip-audit` dans le CI.

### Long terme (1-3 mois)

1. Monitoring applicatif : exposer `/health` et `/metrics` pour Prometheus.
2. Tests API back-end : implementer `tests/back/` avec des tests FastAPI (`TestClient`).
3. Implementer l'integration Dilicom (`app_back/v1/dilicom/orders.py` est vide).
4. Documentation d'architecture (`docs/architecture.md`) decrivant les flux, les services et les decisions de conception.

---

**Derniere mise a jour** : 31 mars 2026
