# TDList : Où est-ce que j'en suis quand je m'arrête de coder ?

- [x] Créer le proxy inversé Traefik
- [x] Modifier le modèle Customers
- [x] Modifier les Customers pour pouvoir être Pro ou Part.
- [x] Réprendre la partie Adresses, Mails, Phones, SyncLog.
- [x] Modifier les méthodes to_dict et from_dict sur les objets restants.
- [x] Créer les objets Objets, Livres, Autres objets, etc.
- [x] Créer les modèles de commandes clients et fournisseurs.
- [x] Créer le modèle de factures clients.
- [x] Comprendre la refactorisation proposée par copilot pour update_object.
- [x] Créer les repositories pour les inventaires, les factures et les objets.
- [x] Premier build du compose
- [x] Créer la migration propre avec les modèles réalisés.
- [x] Créer la connexion avec la base de données PostgreSQL
- [x] Passer la session de SQLAlchemy dans les repositories.
- [x] Faire la migration en démarrage de l'application backend pour que le front puisse fonctionner.
- [x] Créer l'interface dashboard (dashboard_sprint)
- [x] Créer l'interface clients (customers_sprint)
- [x] Créer l'interface d'accueil (home_sprint)
- [ ] Créer l'interface catalogue/stocks/inventaires (inventory_sprint)
  - [ ] Créer les formulaires htmx pour création de commandes et retours de commandes.
  - [ ] Créer les formulaires pour l'ajout de lignes de commandes et de retours de commandes.
  - [ ] Créer la logique d'ajout de formulaires dynamiques avec htmx.
  - [ ] Nettoyer les dépôts sur la collab ou supprimer et recloner :

  ```bash
  git fetch origin --prune
  git checkout main
  git reset --hard origin/main
  ```
