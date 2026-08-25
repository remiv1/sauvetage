# TDList : Où est-ce que j'en suis quand je m'arrête de coder ?

## Validation des cas d'usage

- [X] Création d'un client particulier
  - [X] Adresse
  - [X] Mail
  - [X] Téléphone
- [X] Création d'un client professionnel
  - [X] Adresse
  - [X] Mail
  - [X] Téléphone
- [X] Création de produits
  - [X] Création d'un livre
  - [X] Création d'un objet
  - [X] Synchronisation WooCommerce
- [X] Création d'une commande client
  - [X] Ajout de lignes de commandes
  - [X] Validation de la commande
  - [X] Facturation client Partielle
  - [X] Facturation client Totale
  - [X] Expédition de la commande
  - [X] Annulation de la commande
  - [X] Retour de la commande
- [ ] Création d'une commande fournisseur
  - [X] Ajout de lignes de commandes
  - [X] Validation de la commande
    - [X] Réception DILICOM
    - [X] Réception message DILICOM
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
- [X] Revoir la gestion des variations produits lors des synchronisations WooCommerce, il faut que les variations soient créées sur WooCommerce si elles n'existent pas.
- [X] Mettre en place tous les tests sur les stocks : commandes, suppression d'une ligne, réservations, annulations, etc.
- [!] Gérer les imports et commandes de produits composés avec plusieurs prix/tva. → Mail Dilicom
- [X] Traiter les retours de commandes fournisseurs.