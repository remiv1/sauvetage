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
- [x] Créer l'interface catalogue/stocks/inventaires (inventory_sprint)
  - [x] Créer les formulaires htmx pour création de commandes et retours de commandes.
  - [x] Créer les formulaires pour l'ajout de lignes de commandes et de retours de commandes.
  - [x] Créer la logique d'ajout de formulaires dynamiques avec htmx.
- [x] Gérer les produits/clients sur Henrri lors de la création d'une facture client.
- [x] Gestion plus fine des sessions Flask pour les déconnexions, les expirations, etc.
- [x] Création du tableau de bord

## Validation des cas d'usage

- [X] Création d'un client particulier
  - [X] Adresse
  - [X] Mail
  - [X] Téléphone
- [X] Création d'un client professionnel
  - [X] Adresse
  - [X] Mail
  - [X] Téléphone
- [ ] Création de produits
  - [ ] Création d'un livre
  - [ ] Création d'un objet
  - [ ] Synchronisation WooCommerce
- [ ] Création d'une commande client
  - [X] Ajout de lignes de commandes
  - [X] Validation de la commande
  - [X] Facturation client Partielle
  - [X] Facturation client Totale
  - [X] Expédition de la commande
  - [X] Annulation de la commande
  - [ ] Retour de la commande
- [ ] Création d'une commande fournisseur
  - [X] Ajout de lignes de commandes
  - [X] Validation de la commande
    - [ ] Réception DILICOM
    - [ ] Réception message DILICOM
  - [X] Création d'une réservation de stock
  - [X] Retour de la réservation de stock
- [X] Gestion d'un inventaire

## Validation du staging

- [X] Voir les erreur lors du push de la commande vers WooCommerce
- [X] Problèmes de création de tags depuis la fiche produit
- [!] Problèmes de synchro diffuseurs sur les réceptions ONIX → Mail envoyé à Dilicom
- [X] Problèmes de miniatures images sur les fiches produits
- [X] Décalage des mouvements de stocks sur ISBN 9782740315736 lors d'ajout/suppression de réservations
- [X] Sur les commandes clients, il faut ajouter la possibilité de faire :
  - [X] une modification de ligne de commande
  - [X] la création d'un bon de commande/Devis
- [X] Sur les commandes fournisseurs, lors de la récupération d'un produit, il faut récupérer le prix de vente pour l'affichage ainsi que le taux de TVA.
- [X] Voir pourquoi lors de l'inventaire, lors de l'existance de qté négative, le stock est mis à jour à 0.
- [X] Bug sur la création d'un fournisseur.
- [X] Le formulaire de création d'objet est différent de celui de modification d'objet, il faut unifier les deux.
- [ ] Revoir la gestion des variations produits lors des synchronisations WooCommerce, il faut que les variations soient créées sur WooCommerce si elles n'existent pas.
- [X] Mettre en place tous les tests sur les stocks : commandes, suppression d'une ligne, réservations, annulations, etc.