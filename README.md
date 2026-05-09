# Sauvetage

Projet d'outil centralisé pour une librairie :

- ERP,
- Site e-commerce

## Architecture

```mermaid
flowchart TB

  Browser([Navigateur utilisateur])
  WooCommerce([WooCommerce externe])

  subgraph PROXY[Proxy — Traefik]
    direction TB
    P1[":80 → :443 redirect"]
    P2[":443 TLS<br/>rate-limit /user/login<br/>blocage bots"]
  end

  subgraph FRONT[app_front — Flask :5000]
    direction TB
    F1[Interface HTML + HTMX<br/>/dashboard /stock /inventory<br/>/customer /order /supplier]
    F2[Admin<br/>/admin — utilisateurs, droits, TVA, logs]
    F3[Auth<br/>/user — login, session]
    F4[Médias WooCommerce<br/>GET /woocommerce/media/token]
  end

  subgraph BACK[app_back — FastAPI /api/v1]
    direction TB
    B1[Utilisateurs et droits<br/>POST /users — base sécurisée]
    B2[Inventaires asynchrones<br/>POST /inventory — thread interne]
    B3[Dilicom<br/>GET POST /dilicom]
    B4[Documents PDF<br/>POST /documents]
    B5[WooCommerce sync<br/>POST /woo-commerce<br/>POST /woo-commerce/media/f/access]
    B_auth[Toutes routes protégées<br/>par X-Internal-Token]
  end

  subgraph SHARED[db_models — couche partagée]
    direction TB
    S1[models / repositories / services]
    S2[Traitement image WebP<br/>resize 800x1200 — cible 100 Ko]
  end

  subgraph PG[PostgreSQL — db-main]
    direction TB
    PG1[(sauvetage_main<br/>schéma app_schema<br/>stocks, commandes, clients<br/>inventaires, fournisseurs<br/>objets, médias, jetons)]
    PG2[(sauvetage_users<br/>schéma auth_schema<br/>utilisateurs, mots de passe<br/>rôles, permissions)]
  end

  MONGO[(MongoDB — db-logs<br/>logs applicatifs<br/>Flask + FastAPI)]

  VOL[(Volume partagé<br/>documents/shared/pictures<br/>images WebP)]

  Browser -->|HTTPS| PROXY
  WooCommerce -->|HTTPS| PROXY
  PROXY -->|tout le trafic| FRONT

  FRONT -->|appels internes<br/>X-Internal-Token<br/>réseau sauv-secure| BACK

  FRONT --> SHARED
  BACK --> SHARED
  SHARED --> VOL

  FRONT -->|RW app_schema| PG1
  FRONT -->|écriture logs| MONGO

  BACK -->|RW app_schema| PG1
  BACK -->|RW auth_schema| PG2
  BACK -->|écriture logs| MONGO

  classDef ext fill:#37474f,stroke:#263238,color:#eceff1;
  classDef proxy fill:#6a1b9a,stroke:#4a148c,color:#ffffff;
  classDef front fill:#1565c0,stroke:#0d47a1,color:#ffffff;
  classDef back fill:#e65100,stroke:#bf360c,color:#ffffff;
  classDef shared fill:#4e342e,stroke:#3e2723,color:#ffffff;
  classDef db fill:#558b2f,stroke:#33691e,color:#ffffff;
  classDef vol fill:#00695c,stroke:#004d40,color:#ffffff;

  class Browser,WooCommerce ext;
  class PROXY,P1,P2 proxy;
  class FRONT,F1,F2,F3,F4 front;
  class BACK,B1,B2,B3,B4,B5,B_auth back;
  class SHARED,S1,S2 shared;
  class PG,PG1,PG2 db;
  class MONGO db;
  class VOL vol;

```

### Rôle de chaque composant

#### Proxy — Traefik

- Unique point d'entrée réseau (ports 8080/8443 en dev, 80/443 en prod).
- Redirige HTTP → HTTPS, bloque les bots sur les chemins sensibles.
- Applique un rate-limit strict sur `/user/login` (5 req / 10 min).
- Route tout le trafic HTTPS vers **app-front** (Flask).

#### app_front — Flask

- Rendu HTML server-side et fragments HTMX.
- Modules ERP : dashboard, stock, inventaire, commandes, clients, fournisseurs.
- Gestion des sessions utilisateur et contrôle des droits.
- Administration : utilisateurs, rôles, TVA, consultation des logs.
- Service d'images par jeton (`GET /woocommerce/media/<token>`) pour WooCommerce.
- Connexion : base principale PostgreSQL en lecture/écriture, MongoDB pour les logs.

#### app_back — FastAPI

Réservé aux opérations **longues, sécurisées ou sensibles**. Toutes les routes requièrent l'en-tête `X-Internal-Token`.

| Route | Responsabilité | Base |
| --- | --- | --- |
| `POST /api/v1/users` | Création/modification d'utilisateurs et droits | sécurisée |
| `POST /api/v1/inventory` | Inventaire asynchrone (thread Python) | principale |
| `/api/v1/dilicom` | Import/export flux Dilicom | principale |
| `POST /api/v1/documents` | Génération de PDF | principale |
| `/api/v1/woo-commerce` | Synchronisation produits WooCommerce | principale |
| `POST /api/v1/woo-commerce/media/.../access` | Création de jetons images (usage unique, 1 h) | principale |

#### db_models — couche partagée

- Package Python monté dans les deux conteneurs (`app-front` et `app-back`).
- Modèles SQLAlchemy, repositories, services métier.
- Pipeline de traitement image : compression WebP, resize max 800 x 1200, qualité itérative jusqu'à < 100 Ko.

#### PostgreSQL — db-main

Serveur unique hébergeant deux bases distinctes.

| Base | Schéma | Contenu | Accès Flask | Accès FastAPI |
| --- | --- | --- | --- | --- |
| `sauvetage_main` | `app_schema` | stocks, commandes, clients, inventaires, médias, jetons | RW `user_app` | RW `user_app` |
| `sauvetage_users` | `auth_schema` | utilisateurs, mots de passe, rôles, permissions | — | RW `user_secure` |

Un troisième rôle `user_migr` (Alembic) dispose des droits DDL sur les schémas de migration des deux bases.

#### MongoDB — db-logs

- Stockage des logs applicatifs (module partagé `logs/logger.py`).
- Écrit par Flask et FastAPI via `MongoDBLogger`.
- Collections par type d'événement : `users`, `logs`, `clients`, `métiers`.

#### Volume partagé — sauv-pictures

- Monté dans `app-front` et `app-back` au même chemin `/home/root/app/documents/shared/pictures`.
- Contient les images compressées en WebP.
- FastAPI les écrit lors des uploads ; Flask les lit et les sert.

### Flux principaux

#### Flux ERP (quotidien)

1. Navigateur → Traefik → Flask
2. Flask lit/écrit `sauvetage_main` via `db_models`
3. Flask délègue les opérations longues (inventaire, PDF, Dilicom) à FastAPI via le réseau interne `sauv-secure`
4. Flask et FastAPI écrivent les événements dans MongoDB

#### Flux image WooCommerce

1. Flask (admin) appelle FastAPI : `POST /api/v1/woo-commerce/media/<filename>/access` avec `X-Internal-Token`
2. FastAPI enregistre un jeton temporaire (1 h, usage unique) dans `sauvetage_main`
3. WooCommerce télécharge l'image via `GET /woocommerce/media/<token>` (Traefik → Flask)
4. Flask vérifie le jeton, sert le fichier depuis le volume, marque le jeton consommé

#### Flux gestion des utilisateurs

1. Flask (admin) appelle FastAPI : `POST /api/v1/users` avec `X-Internal-Token`
2. FastAPI écrit dans `sauvetage_users` (schéma `auth_schema`)
3. Flask relit les droits depuis `sauvetage_main` pour les contrôles de session

## Avancement du projet

```mermaid
gantt
    title Projet Sauvetage
    dateFormat  DD-MM-YYYY
    axisFormat  %d-%m
    section Cadrage
    Pré-vente :done, a1, 25-01-2026, 9d
    Vente :active, a21, 28-01-2026, 7d
    section Développement
    Analyse :a2, after a1, 10d
    Développement :crit, a3, after a2, 120d
    section Tests
    Tests unitaires :a4, after a3, 15d
    Tests d'intégration :a5, after a4, 15d
    section Déploiement
    Déploiement :a6, after a5, 10d
    Recette :a7, after a6, 7d
```

## Tests

- Documentation et instructions de test : [tests/README.md](tests/README.md)

## Documentation technique

- Gestion des images et jetons WooCommerce : [documentations/gestion_images_woocommerce.md](documentations/gestion_images_woocommerce.md)

## Contributeurs

>_Rémi Verschuur | Audit-io : Lead Manager & Développeur Fullstack_
