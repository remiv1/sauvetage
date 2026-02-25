# Rapport qualitatif — Projet « Sauvetage »

Date : 25 février 2026

Résumé : synthèse qualitative du travail réalisé jusqu'à présent (front, styles, déploiement, debugging).

## Intensité de travail

- Observations : rythme soutenu et itératif. Travaux notables : migration CSS → SCSS, compilation d'assets, corrections de templates Jinja, résolution d'erreurs Gunicorn/Docker, rebuilds fréquents.
- Charge : élevée pour une phase de prototypage — beaucoup d'allers-retours (build, debug, tests locaux).
- Impact : changements rapides ont permis d'itérer l'UI et les routes; cependant, certaines tâches restent manuelles (compilation SCSS, rebuild image).
- Recommandations : automatiser la compilation d'assets (script ou step CI), ajouter des tâches de build locales (Makefile / NPM script / task runner).

## Architecture

- Structure : séparation front / back (`app_front/`, `app_back/`), modèles DB dans `db_models/`, services et repositories organisés — bonne séparation des responsabilités.
- Patterns : usage de blueprints/modularisation côté Flask, templates Jinja réutilisables (`templates/common/`), configuration par fichiers TOML pour pages.
- Déploiement : conteneurisation (Docker/Podman compose), proxy/traefik présent, Gunicorn pour le front — base solide pour environnement small-to-medium.
- Limites : pas (encore) de pipeline CI/CD visible, assets build manual, absence d’un catalogue clair des services et dépendances versionnées en un seul manifest.
- Recommandations : ajouter un pipeline CI (lint, tests, build image), documenter les services dans un README `deploy/` et centraliser les tâches répétitives (Makefile / small scripts).

## Gestion de la sécurité

- Bonnes pratiques observées : variables DB construites/encodées dans l'entrypoint, séparation des bases (DB principale / secure), versions des paquets pinées dans `requirements.txt`.
- Risques identifiés : secrets gérés via env/entrypoint (vérifier qu'ils ne sont pas committés), dépendances tierces non scannées régulièrement, images Docker potentiellement construites en root sans hardening.
- Recommandations prioritaires :
  - Externaliser les secrets (Vault, AWS Secrets Manager, ou au minimum fichiers `.env` hors repo).
  - Scanner les dépendances (safety, pip-audit, GitHub Dependabot) et corriger vulnérabilités.
  - Forcer l'exécution non-root dans les Dockerfiles, minima d'utilisateur non privilégié.
  - Ajouter en-têtes de sécurité HTTP (CSP, HSTS, X-Frame-Options) dans `app_front` via middleware.

## Maturité du projet

- Niveau actuel : prototype avancé / early product — composants principaux existants, déploiement conteneurisé, pages et styles livrés.
- Manques pour production : couverture de tests (unit/integration), CI/CD, monitoring/alerting centralisé, politique de release, playbooks de rollback.
- Roadmap courte (1–4 semaines) :
  1. Ajouter pipeline CI minimal (lint, tests unitaires, build image).
  2. Automatiser compilation SCSS et bundling d'assets dans le pipeline.
  3. Mettre en place scanning vulnérabilités et politique de dépendances.
  4. Standardiser la gestion des secrets (ex. fichier d’exemples `.env.example`).
- Roadmap moyenne (1–3 mois) : tests d’intégration, observabilité (logs centralisés, métriques), documentation d'architecture et runbook.

## Actions proposées (tâches concrètes)

- Script `make assets` ou `package.json` script pour compiler SCSS automatiquement.
- Pipeline CI (GitHub Actions / GitLab CI) avec étapes : lint → tests → build docker → publish (optionnel).
- Ajouter `pre-commit` + hooks (black/isort/ruff/pylint selon préférence) et tests unitaires basiques.
- Ajouter scan de dépendances (`pip-audit`/`safety`) dans CI.
- Audit rapide des Dockerfiles (exécution non-root, réduction de la taille d'image).
