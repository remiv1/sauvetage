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
-[X] Ajout de nouveaux modèles pour les clients, adresses, mails et téléphones, ainsi qu'une classe générique pour les méthodes communes
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

**Dernière mise à jour** : 13 février 2026

> _Note : Cette roadmap est un document vivant et sera mise à jour régulièrement en fonction de l'avancement du projet et des priorités changeantes._
