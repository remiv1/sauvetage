# Architecture - Projet Sauvetage

Ce document fournit une vue d'ensemble de l'architecture du système Sauvetage. Pour plus de détails techniques, consultez la [documentation technique complète](docs/technical/architecture.md).

## Vision Globale

Sauvetage est conçu comme un système distribué basé sur une architecture microservices, permettant une évolution indépendante des composants et une scalabilité optimale.

## Principes Architecturaux

### 1. Séparation des Préoccupations (SoC)
Chaque service a une responsabilité unique et bien définie :
- **Service Catalogue** : Gestion des produits
- **Service Commandes** : Traitement des commandes
- **Service Stock** : Gestion de l'inventaire
- **Service Clients** : Gestion des utilisateurs
- **Service Auth** : Authentification et autorisation

### 2. Indépendance des Services
- Services déployables indépendamment
- Base de code séparée par service
- Communication via APIs définies
- Couplage faible, cohésion forte

### 3. API-First Design
- APIs REST bien définies
- Documentation OpenAPI/Swagger
- Versionnement des APIs
- Contrats d'interface clairs

### 4. Scalabilité Horizontale
- Services stateless
- Load balancing
- Auto-scaling basé sur la charge
- Cache distribué (Redis)

### 5. Résilience
- Circuit breakers pour éviter les cascades de pannes
- Retry policies avec backoff exponentiel
- Timeouts configurables
- Dégradation gracieuse des services

## Diagramme d'Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COUCHE PRÉSENTATION                          │
├──────────────────────────────┬──────────────────────────────────────┤
│   Frontend E-commerce        │      Frontend ERP (Admin)            │
│   (React + Next.js)          │      (React + Ant Design)            │
│   - Catalogue                │      - Dashboard                     │
│   - Panier                   │      - Gestion produits              │
│   - Compte client            │      - Gestion stocks                │
└──────────────┬───────────────┴──────────────┬───────────────────────┘
               │                              │
               │         HTTPS / WSS          │
               │                              │
┌──────────────┴──────────────────────────────┴───────────────────────┐
│                        COUCHE API GATEWAY                            │
│                     (Express.js / Kong)                              │
│   - Routage intelligent                                              │
│   - Authentification JWT                                             │
│   - Rate limiting                                                    │
│   - Load balancing                                                   │
│   - Logging / Monitoring                                             │
└──────────┬────────────┬────────────┬────────────┬────────────────────┘
           │            │            │            │
┌──────────┴────┐  ┌────┴───────┐  ┌┴───────────┐ ┌┴──────────────┐
│   Service     │  │  Service   │  │  Service   │ │   Service     │
│  Catalogue    │  │ Commandes  │  │   Stock    │ │   Clients     │
│               │  │            │  │            │ │               │
│  - CRUD       │  │ - Création │  │ - Suivi    │ │ - Profils     │
│  - Recherche  │  │ - Status   │  │ - Alertes  │ │ - Historique  │
│  - Catégories │  │ - Factures │  │ - Mouvmts  │ │ - Auth        │
└───────┬───────┘  └─────┬──────┘  └──────┬─────┘ └───────┬───────┘
        │                │                 │               │
        └────────────────┴─────────────────┴───────────────┘
                                │
                   ┌────────────┴────────────┐
                   │   Message Queue         │
                   │   (RabbitMQ/Redis)      │
                   │   - Events              │
                   │   - Async Tasks         │
                   └────────────┬────────────┘
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                        COUCHE DONNÉES                                │
├─────────────────────┬───────────────────────┬───────────────────────┤
│   PostgreSQL        │      Redis            │   Elasticsearch       │
│   (Base principale) │      (Cache)          │   (Recherche)         │
│   - Produits        │      - Sessions       │   - Full-text         │
│   - Commandes       │      - Cache API      │   - Facettes          │
│   - Clients         │      - Queue          │   - Analytics         │
│   - Stock           │                       │                       │
└─────────────────────┴───────────────────────┴───────────────────────┘
```

## Flux de Données

### 1. Flux de Consultation (Lecture)

```
Client → API Gateway → Service → Cache (Redis)
                                    ↓ (cache miss)
                                 Database (PostgreSQL)
                                    ↓
                                 Cache (mise à jour)
                                    ↓
                              Client (réponse)
```

### 2. Flux de Commande (Écriture)

```
Client → API Gateway → Service Commandes
                            ↓
                       Validation
                            ↓
                    Database (Write)
                            ↓
                    Event (Message Queue)
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
Service Stock       Service Email       Service Analytics
(Déduction)         (Confirmation)      (Statistiques)
```

### 3. Flux d'Authentification

```
Client → API Gateway → Service Auth
                            ↓
                    Validation credentials
                            ↓
                    Database (User check)
                            ↓
                    JWT Token generation
                            ↓
                    Redis (Session)
                            ↓
                    Client (Token)
```

## Patterns Utilisés

### 1. API Gateway Pattern
Point d'entrée unique pour tous les clients, simplifiant la communication et centralisant les préoccupations transverses (auth, logging, rate limiting).

### 2. Service Registry Pattern
Services s'enregistrent automatiquement pour être découverts par l'API Gateway (service discovery).

### 3. Circuit Breaker Pattern
Protection contre les défaillances en cascade. Si un service échoue répétitivement, le circuit s'ouvre et renvoie une réponse par défaut.

### 4. Event-Driven Architecture
Communication asynchrone via événements pour les opérations non critiques (emails, notifications, analytics).

### 5. CQRS (Command Query Responsibility Segregation)
Séparation des opérations de lecture et d'écriture pour optimiser la performance (optionnel, pour phase 3).

### 6. Repository Pattern
Abstraction de la couche d'accès aux données, facilitant les tests et les changements de base de données.

### 7. Dependency Injection
Inversion de contrôle pour améliorer la testabilité et la maintenabilité.

## Sécurité

### Couches de Sécurité

```
┌─────────────────────────────────────┐
│  Firewall / WAF                     │
├─────────────────────────────────────┤
│  HTTPS / TLS 1.3                    │
├─────────────────────────────────────┤
│  API Gateway                         │
│  - Rate Limiting                    │
│  - JWT Validation                   │
│  - Input Validation                 │
├─────────────────────────────────────┤
│  Services                            │
│  - Authorization (RBAC)             │
│  - Business Logic Validation        │
├─────────────────────────────────────┤
│  Database                            │
│  - Encrypted at rest                │
│  - Access control                   │
│  - Prepared statements              │
└─────────────────────────────────────┘
```

### Principes de Sécurité
- **Defense in Depth** : Plusieurs couches de sécurité
- **Least Privilege** : Permissions minimales nécessaires
- **Zero Trust** : Vérification à chaque niveau
- **Security by Design** : Sécurité intégrée dès la conception

## Performance

### Stratégies d'Optimisation

#### 1. Caching
- **L1 Cache** : In-memory dans chaque service
- **L2 Cache** : Redis distribué
- **CDN** : CloudFlare pour assets statiques

#### 2. Database
- Index appropriés sur les colonnes fréquemment interrogées
- Connection pooling
- Read replicas pour les requêtes de lecture
- Partitioning pour les grandes tables

#### 3. Frontend
- Code splitting
- Lazy loading
- Image optimization (WebP, srcset)
- Service Worker pour PWA

#### 4. Backend
- Pagination des résultats
- Compression gzip/brotli
- Async/await pour I/O
- Load balancing

## Monitoring et Observabilité

### Les Trois Piliers

#### 1. Logs
- Logs structurés (JSON)
- Niveaux : ERROR, WARN, INFO, DEBUG
- Centralisation (ELK Stack ou équivalent)
- Correlation IDs pour tracer les requêtes

#### 2. Métriques
- Temps de réponse (latency)
- Throughput (requêtes/sec)
- Taux d'erreur
- Utilisation ressources (CPU, RAM, Disk)

#### 3. Traces
- Distributed tracing entre services
- Identification des goulots d'étranglement
- Analyse des performances end-to-end

## Évolutivité

### Scaling Vertical vs Horizontal

#### Vertical Scaling (Scale Up)
- Augmenter les ressources d'une machine
- Limité par le hardware
- Plus simple mais moins résilient

#### Horizontal Scaling (Scale Out) ✅
- Ajouter plus d'instances
- Illimité en théorie
- Nécessite load balancing
- Plus résilient

### Auto-scaling
Configuration de règles d'auto-scaling :
- CPU > 70% → +1 instance
- CPU < 30% pendant 10min → -1 instance
- Min instances : 2
- Max instances : 10

## Déploiement

### Environnements

```
Development (Local)
    ↓
    ↓ git push
    ↓
Staging (Cloud)
    ↓
    ↓ Tests automatisés
    ↓
Production (Cloud)
```

### Stratégies de Déploiement

#### Blue-Green Deployment
- Deux environnements identiques (Blue, Green)
- Déploiement sur l'environnement inactif
- Switch instantané du trafic
- Rollback facile

#### Canary Deployment
- Déploiement progressif (5%, 25%, 50%, 100%)
- Monitoring des métriques
- Rollback si problème détecté

## Technologies Clés

### Frontend
- **React 18+** : UI Library
- **TypeScript** : Type safety
- **TailwindCSS** : Styling
- **React Query** : Data fetching

### Backend
- **Node.js 20** : Runtime
- **Express.js** : Web framework
- **TypeScript** : Type safety
- **Prisma** : ORM

### Infrastructure
- **PostgreSQL 15** : Database
- **Redis 7** : Cache
- **Docker** : Containerization
- **GitHub Actions** : CI/CD

## Évolution Future

### Phase 1 - Actuel
Architecture microservices basique avec services essentiels.

### Phase 2 - Court terme (6-12 mois)
- Service mesh (Istio) pour communication inter-services
- Elasticsearch pour recherche avancée
- GraphQL en complément de REST

### Phase 3 - Moyen terme (1-2 ans)
- Kubernetes pour orchestration
- Event Sourcing pour traçabilité complète
- Machine Learning pour recommandations
- Application mobile native

## Décisions d'Architecture (ADRs)

Les décisions d'architecture importantes sont documentées dans `docs/technical/adr/`.

Format : `ADR-XXX-titre-de-la-decision.md`

Exemples :
- ADR-001 : Choix de PostgreSQL vs MongoDB
- ADR-002 : Architecture Microservices vs Monolithe
- ADR-003 : Node.js vs Python pour le backend

## Ressources

### Documentation Détaillée
- [Architecture Technique Complète](docs/technical/architecture.md)
- [Stack Technique](docs/technical/stack-technique.md)
- [Projet Technique](docs/technical/projet-technique.md)

### Références Externes
- [Microservices Patterns](https://microservices.io/patterns/index.html)
- [12 Factor App](https://12factor.net/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

---

**Maintenu par** : Lead Developer  
**Dernière mise à jour** : 2026-01-10
