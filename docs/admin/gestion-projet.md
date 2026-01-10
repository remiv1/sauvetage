# Gestion de Projet - Sauvetage

## Organisation du Projet

### Équipe

- **Product Owner** : À définir
- **Scrum Master** : À définir
- **Lead Developer** : À définir
- **Développeurs** : À définir
- **Testeurs** : À définir
- **Designer UX/UI** : À définir

### Méthodologie

Le projet suit une approche **Agile/Scrum** :
- Sprints de 2 semaines
- Réunions quotidiennes (daily stand-up)
- Revues de sprint
- Rétrospectives

## Workflow Git

### Branches

- `main` : Branche de production
- `develop` : Branche de développement
- `feature/*` : Branches de fonctionnalités
- `hotfix/*` : Corrections urgentes
- `release/*` : Préparation des releases

### Conventions de Commit

Format : `type(scope): message`

Types :
- `feat` : Nouvelle fonctionnalité
- `fix` : Correction de bug
- `docs` : Documentation
- `style` : Formatage
- `refactor` : Refactorisation
- `test` : Tests
- `chore` : Maintenance

Exemple : `feat(erp): add inventory management module`

## Outils de Gestion

- **GitHub** : Gestion du code et des issues
- **GitHub Projects** : Suivi des tâches
- **GitHub Actions** : CI/CD
- **Discussions** : Communication asynchrone

## Communication

- **Réunions régulières** : Planifiées selon l'équipe
- **Issues GitHub** : Suivi des bugs et fonctionnalités
- **Pull Requests** : Revue de code
- **Documentation** : Mise à jour continue

## Processus de Release

1. Créer une branche `release/vX.Y.Z`
2. Tests finaux et corrections
3. Mise à jour de la documentation
4. Merge dans `main` et `develop`
5. Tag de version
6. Déploiement en production

## Qualité

### Pratiques

- Revue de code obligatoire
- Tests unitaires (couverture > 80%)
- Tests d'intégration
- Analyse statique du code
- Documentation du code

### Critères de Définition of Done

- [ ] Code écrit et testé
- [ ] Tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Code review approuvée
- [ ] Documentation à jour
- [ ] Accepté par le Product Owner
