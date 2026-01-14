# Sauvetage

Projet d'outil centralisé pour une librairie :

- ERP,
- Site e-commerce

## Branches

- [`selling`](sales/pre-selling/260110_notes.md) : branche de pré-commercialisation du projet. CdC, définitions techniques, maquettes, prototypes, etc.
- `erp` : Développement du projet ERP de base
  - `erp-stocks` : Module de gestion des stocks
  - `erp-accounting` : Module de comptabilité
  - `erp-billing` : Module de facturation
  - `erp-crm` : Module de gestion de la relation client
- `ecommerce` : Développement du site e-commerce
  - `ecommerce-frontend` : Développement de l'interface utilisateur du site e
  - `ecommerce-backend` : Développement de la logique serveur et de la base de données
- `integration` : Intégration des modules ERP avec le site e-commerce

## Architecture

```mermaid
flowchart LR

  %% --- Clients / UI ---
  A[Frontend<br/>Browser / App]

  %% --- Flask (Read Only) ---
  subgraph B[Flask API — Read Only]
    B1[Routes RO<br/>/dashboard<br/>/inventaires/:id<br/>/stocks<br/>/clients<br/>/fournisseurs]
    B2[(SQLAlchemy RO Engine)]
  end

  %% --- FastAPI (Read/Write + Métier) ---
  subgraph C[FastAPI — Write + Métier]
    C1[Routes RW<br/>/inventaires:POST<br/>/inventaires/:id/valider<br/>/mouvements<br/>/stocks<br/>/clients<br/>/fournisseurs]
    C2[Worker interne<br/>Traitements lourds<br/>Inventaires asynchrones<br/>Comparaison stock<br/>Génération écarts]
    C3[(SQLAlchemy RW Engine)]
  end

  %% --- Base de données ---
  subgraph D[Base de données]
    D1[(Utilisateur RO<br/>SELECT uniquement)]
    D2[(Utilisateur RW<br/>SELECT + INSERT + UPDATE + DELETE)]
    D3[(Tables :<br/>stocks<br/>inventaires<br/>mouvements<br/>clients<br/>fournisseurs<br/>anomalies)]
  end

  %% --- Flux ---
  A -->|Requêtes UI| B1
  B1 -->|Lecture| B2
  B2 -->|Connexion RO| D1
  D1 -->|SELECT| B2
  
  B1 -->|Sous-requête API| C1

  A -->|Actions métier<br/>inventaire, correction| C1
  C1 -->|Écriture| C3
  C3 -->|Connexion RW| D2
  D2 -->|SELECT/INSERT/UPDATE/DELETE| C3

  C1 -->|Déclenche job| C2
  C2 -->|Écrit résultats| C3

  B1 -->|Lecture état inventaire| B2
  B2 -->|SELECT| D1

  %% --- Styles ---
  classDef read fill:#1e88e5,stroke:#0d47a1,color:#ffffff;
  classDef write fill:#fb8c00,stroke:#e65100,color:#ffffff;
  classDef db fill:#757575,stroke:#424242,color:#ffffff;

  class B,B1,B2 read;
  class C,C1,C2,C3 write;
  class D,D1,D2,D3 db;

```

### 🧩 **Explication rapide du diagramme**

#### 🔵 Flask (RO)

- Sert l’interface utilisateur
- Ne fait que des **lectures**
- Utilise un utilisateur SQL **read-only**
- Peut être mis en cache et scalé sans risque

#### 🟠 FastAPI (RW)

- Contient **toute la logique métier**
- Gère les inventaires (complet, partiel, ponctuel)
- Gère les mouvements, corrections, anomalies
- Exécute les traitements lourds en **asynchrone interne**
- Utilise un utilisateur SQL **read-write**

#### ⚙️ Base de données

- Deux utilisateurs SQL :
  - `app_ro` → SELECT
  - `app_rw` → SELECT + INSERT + UPDATE + DELETE
- Tables partagées entre les deux services
- Cohérence garantie par FastAPI

#### 🔄 Flux d’inventaire

1. Front → Flask (RO) pour afficher l’écran
2. Front → FastAPI (RW) pour lancer l’inventaire
3. FastAPI crée un job interne
4. FastAPI écrit les résultats
5. Flask lit l’état et affiche les écarts
6. FastAPI valide et génère les mouvements

## Contributeurs

>_Rémi Verschuur | Audit-io : Lead Manager & Développeur Fullstack_
