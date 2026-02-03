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

**Dernière mise à jour** : 3 février 2026

> _Note : Cette roadmap est un document vivant et sera mise à jour régulièrement en fonction de l'avancement du projet et des priorités changeantes._
