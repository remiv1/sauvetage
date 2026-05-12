# Gestion des images et jetons WooCommerce

[Retour au README principal](../README.md)

Date: 9 mai 2026
Commit documenté: c18c126779673948bbe50c9b7568cad0ab2bb8e7

## Objectif

Ce commit remplace le stockage binaire des images en base par un stockage fichier sur volume partagé, ajoute un pipeline de compression WebP, et introduit un mécanisme de jetons temporaires pour servir les images à WooCommerce.

## Résumé des changements

- Stockage des médias:
  - suppression du champ binaire `file_data` dans le modèle SQLAlchemy.
  - usage de `file_link` pour stocker soit une URL externe, soit un nom de fichier local.
  - ajout du booléen `is_local` pour distinguer les deux cas.
- Traitement image:
  - nouveau module partagé `db_models/services/pictures.py`.
  - redimensionnement max `800x1200`.
  - conversion WebP.
  - réduction de qualité itérative jusqu'à une cible de `100 Ko`.
- Sécurité d'accès WooCommerce:
  - nouvelle table `app_schema.media_access_tokens`.
  - jetons valides 1 heure, à usage unique.
  - création du jeton côté backend FastAPI uniquement.
  - consommation du jeton côté frontend Flask au premier téléchargement.
- Infrastructure:
  - volume partagé `sauv-pictures` monté dans `app-front` et `app-back`.
  - répertoire local du volume: `./documents/shared/pictures`.

## Détails techniques

## 1 Modèle de données

Fichier: `db_models/objects/objects.py`

- `MediaFiles`:
  - suppression: `file_data` (`LargeBinary`).
  - conservation/usage: `file_link` (`String`).
  - ajout: `is_local` (`Boolean`, défaut `False`).
- `MediaAccessToken` (nouveau modèle):
  - table: `app_schema.media_access_tokens`.
  - clé primaire: `token` (nom de fichier, ex. UUID.webp).
  - `valid_from`, `valid_until`, `used_at`.
  - méthode `is_valid()`:
    - jeton non consommé (`used_at is None`),
    - et non expiré (`now <= valid_until`).

## 2 Pipeline de traitement image

Fichier: `db_models/services/pictures.py`

Fonctions exposées:

- `read_upload_from_entry(entry)`:
  - lit le champ `file_data` WTForms,
  - retourne `(bytes, nom_original)` ou `(None, None)`.
- `compress_to_webp(content, original_filename)`:
  - ouvre l'image via Pillow,
  - applique `thumbnail((800, 1200), Image.Resampling.LANCZOS)`,
  - convertit en WebP,
  - diminue la qualité de 80 à 10 par pas de 5,
  - s'arrête dès que la taille est <= 100 Ko.
  - fallback: si non-image ou Pillow absent, retourne le contenu d'origine.
- `save_picture_to_disk(content, original_filename, upload_dir)`:
  - compresse si possible,
  - génère un nom `UUID + extension`,
  - écrit le fichier dans `upload_dir`,
  - retourne le nom de fichier généré.

## 3 Persistance des médias depuis les formulaires

Fichier: `db_models/repositories/objects/media.py`

Méthode principale: `save_from_form(...)`

- synchronise la collection de médias de l'objet,
- lit les uploads via le module `pictures`,
- si upload présent:
  - écrit sur disque,
  - renseigne `file_link` avec le nom de fichier,
  - force `is_local = True`.
- sinon, si `file_link` saisi:
  - garde ce lien externe,
  - force `is_local = False`.
- supprime les médias retirés du formulaire.

## 4 Jetons d'accès WooCommerce

### Création du jeton (backend sécurisé)

Fichier: `app_back/v1/woocommerce/media.py`

- Route: `POST /api/v1/woo-commerce/media/{filename}/access`
- Protection: `X-Internal-Token` (via `access_control`).
- Comportement:
  - réutilise un jeton valide existant pour le même fichier,
  - sinon crée un nouveau jeton valable 1 heure.
- Réponse JSON:

```json
{
  "token": "<filename>",
  "valid_until": "2026-05-09T12:43:22.000000+00:00"
}
```

### Consommation du jeton (frontend public)

Fichier: `app_front/blueprints/woocommerce/routes.py`

- Route: `GET /woocommerce/media/<filename>`
- Comportement:
  - vérifie que le jeton existe, est valide, et non consommé,
  - sert le fichier depuis `MEDIA_UPLOAD_DIR`,
  - marque le jeton comme consommé après envoi réussi.
- Codes d'erreur:
  - `403` jeton invalide/expiré/consommé,
  - `404` fichier absent,
  - `503` `MEDIA_UPLOAD_DIR` non configuré.

## 5 Route interne de lecture média (interface stock)

Fichier: `app_front/blueprints/stock/routes_htmx_search.py`

- Route: `GET /stock/htmx/search/media/<filename>`
- Sert le fichier depuis `MEDIA_UPLOAD_DIR`.
- Usage: affichage interne dans l'interface stock.

## 6 Pré-requis d'environnement

## Variables

- `MEDIA_UPLOAD_DIR`:
  - doit pointer vers le dossier monté dans les deux services.
  - valeur attendue dans les containers: `/home/root/app/documents/shared/pictures`.
- `SECURITY_TOKEN`:
  - partagé entre le service appelant et `app_back`.
  - transmis dans l'en-tête `X-Internal-Token`.

## Dépendance

- `Pillow==12.2.0` ajoutée dans `app_front/requirements.txt`.

## Volume partagé

Fichier: `docker-compose.yml`

- volume nommé: `sauv-pictures`.
- binding local: `./documents/shared/pictures`.
- montage:
  - `app-front` -> `/home/root/app/documents/shared/pictures`
  - `app-back` -> `/home/root/app/documents/shared/pictures`

## 7 Impacts et points d'attention

- Migration DB nécessaire pour:
  - suppression logique de `file_data`,
  - ajout de `is_local`,
  - création de la table `media_access_tokens`.
- Les jetons sont à usage unique:
  - un second téléchargement avec le même lien doit échouer en `403`.
- Le nom de fichier (UUID.webp) est aussi la valeur du jeton:
  - simplifie l'association fichier/jeton,
  - impose de conserver ce nom dans les échanges techniques.

## 8 Vérification rapide (manuel)

1. Uploader une image depuis l'interface stock.
2. Vérifier la présence d'un fichier WebP dans `documents/shared/pictures`.
3. Créer un jeton via l'endpoint backend sécurisé.
4. Appeler l'URL frontend `GET /woocommerce/media/<token>`:
   - 1er appel: succès, fichier servi.
   - 2e appel: `403` attendu.
