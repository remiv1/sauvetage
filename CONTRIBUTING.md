# Guide de Contribution - Sauvetage

Merci de votre intérêt pour contribuer au projet Sauvetage ! Ce guide vous aidera à comprendre comment participer efficacement.

## Code de Conduite

### Nos Engagements
- Respecter tous les contributeurs
- Accepter les critiques constructives
- Se concentrer sur ce qui est le mieux pour le projet
- Faire preuve d'empathie envers les autres membres

### Comportements Attendus
- ✅ Utiliser un langage accueillant et inclusif
- ✅ Respecter les points de vue différents
- ✅ Accepter gracieusement les critiques constructives
- ✅ Se concentrer sur l'intérêt de la communauté

### Comportements Inacceptables
- ❌ Harcèlement ou discrimination
- ❌ Insultes ou attaques personnelles
- ❌ Publication d'informations privées d'autrui
- ❌ Tout comportement inapproprié en milieu professionnel

## Comment Contribuer

### 1. Reporter un Bug

#### Avant de Reporter
- Vérifiez que le bug n'a pas déjà été reporté dans les [Issues](https://github.com/remiv1/sauvetage/issues)
- Assurez-vous d'utiliser la dernière version

#### Comment Reporter
1. Créez une nouvelle issue avec le template "Bug Report"
2. Utilisez un titre clair et descriptif
3. Décrivez les étapes pour reproduire le bug
4. Indiquez le comportement attendu vs observé
5. Ajoutez des captures d'écran si pertinent
6. Mentionnez votre environnement (OS, version, etc.)

### 2. Proposer une Fonctionnalité

#### Avant de Proposer
- Vérifiez que la fonctionnalité n'a pas déjà été proposée
- Assurez-vous qu'elle correspond à la vision du projet

#### Comment Proposer
1. Ouvrez une [Discussion](https://github.com/remiv1/sauvetage/discussions) pour en discuter
2. Expliquez le problème que cela résout
3. Décrivez la solution proposée
4. Proposez des alternatives considérées
5. Attendez les retours avant de commencer à coder

### 3. Contribuer au Code

#### Setup de l'Environnement
```bash
# Cloner le dépôt
git clone https://github.com/remiv1/sauvetage.git
cd sauvetage

# Consulter la documentation pour setup complet
# (Voir subprojects/README.md pour sous-projets)
```

#### Workflow Git

##### 1. Créer une Branche
```bash
# Depuis la branche develop
git checkout develop
git pull origin develop

# Créer une branche feature
git checkout -b feature/ma-fonctionnalite

# Ou une branche fix
git checkout -b fix/mon-bug
```

##### 2. Conventions de Nommage

**Branches** :
- `feature/nom-fonctionnalite` : Nouvelles fonctionnalités
- `fix/nom-bug` : Corrections de bugs
- `docs/sujet` : Documentation
- `refactor/sujet` : Refactorisation
- `test/sujet` : Ajout de tests

**Commits** :
Format : `type(scope): message`

Types :
- `feat` : Nouvelle fonctionnalité
- `fix` : Correction de bug
- `docs` : Documentation
- `style` : Formatage, point-virgules manquants, etc.
- `refactor` : Refactorisation du code
- `test` : Ajout ou modification de tests
- `chore` : Maintenance, dépendances

Exemples :
```
feat(erp): add inventory alert system
fix(auth): resolve JWT expiration issue
docs(readme): update installation instructions
test(api): add integration tests for orders
```

##### 3. Développer

**Standards de Code** :
- Suivre les conventions définies dans [Lead Dev Guide](docs/technical/lead-dev-guide.md)
- Écrire du code propre et lisible
- Commenter uniquement le code complexe
- Respecter les linters configurés

**Tests** :
- Écrire des tests unitaires pour le nouveau code
- Maintenir une couverture > 80%
- S'assurer que tous les tests passent

**Documentation** :
- Mettre à jour la documentation si nécessaire
- Documenter les APIs avec JSDoc/TypeDoc
- Ajouter des exemples d'utilisation

##### 4. Commiter
```bash
# Vérifier les changements
git status
git diff

# Ajouter les fichiers
git add .

# Commiter avec un message conventionnel
git commit -m "feat(module): description de la fonctionnalité"
```

##### 5. Pousser et Créer une PR
```bash
# Pousser la branche
git push origin feature/ma-fonctionnalite

# Sur GitHub, créer une Pull Request
```

#### Pull Request

**Template de PR** :

```markdown
## Description
[Description claire des changements]

## Type de Changement
- [ ] Bug fix (changement non-breaking qui corrige un problème)
- [ ] Nouvelle fonctionnalité (changement non-breaking qui ajoute une fonctionnalité)
- [ ] Breaking change (fix ou feature qui causerait un problème avec l'existant)
- [ ] Documentation

## Comment Tester
[Étapes pour tester les changements]

## Checklist
- [ ] Mon code suit les standards du projet
- [ ] J'ai effectué une auto-revue de mon code
- [ ] J'ai commenté le code difficile à comprendre
- [ ] J'ai mis à jour la documentation
- [ ] Mes changements ne génèrent pas de nouveaux warnings
- [ ] J'ai ajouté des tests qui prouvent que mon fix/feature fonctionne
- [ ] Les tests unitaires passent localement
- [ ] Les tests d'intégration passent localement

## Screenshots (si applicable)
[Ajouter des captures d'écran]

## Issues Liées
Closes #[numéro_issue]
```

**Revue de Code** :
- Attendez l'approbation d'au moins un mainteneur
- Répondez aux commentaires de manière constructive
- Effectuez les modifications demandées
- Re-demandez une revue après les changements

##### 6. Après le Merge
```bash
# Retourner sur develop et mettre à jour
git checkout develop
git pull origin develop

# Supprimer la branche locale
git branch -d feature/ma-fonctionnalite
```

### 4. Contribuer à la Documentation

La documentation est aussi importante que le code !

**Types de Documentation** :
- README et guides
- Documentation technique
- Exemples et tutoriels
- Commentaires de code

**Comment Contribuer** :
1. Identifier une lacune ou une erreur
2. Créer une branche `docs/sujet`
3. Améliorer la documentation
4. Créer une PR

**Style** :
- Utiliser le Markdown
- Être clair et concis
- Ajouter des exemples
- Vérifier l'orthographe

## Standards de Qualité

### Code Quality

#### Linting
```bash
# Node.js/TypeScript
npm run lint
npm run lint:fix

# Python
ruff check .
ruff format .
```

#### Tests
```bash
# Exécuter les tests
npm test

# Avec couverture
npm run test:coverage
```

### Performance
- Éviter les boucles imbriquées inutiles
- Utiliser le cache quand approprié
- Optimiser les requêtes DB
- Utiliser la pagination

### Sécurité
- Ne jamais commit de secrets (API keys, passwords)
- Valider toutes les entrées utilisateur
- Utiliser des requêtes paramétrées (SQL injection)
- Échapper les données (XSS)

## Structure des Commits

### Commits Atomiques
- Un commit = une modification logique
- Éviter les commits fourre-tout
- Facilite les reviews et les rollbacks

### Messages Clairs
```bash
# Bon
git commit -m "feat(auth): add JWT refresh token mechanism"

# Mauvais
git commit -m "update files"
```

## Communication

### Canaux
- **Issues** : Bugs et features
- **Discussions** : Questions et idées
- **Pull Requests** : Revues de code
- **Wiki** : Documentation détaillée (si activé)

### Langue
- Français ou Anglais acceptés
- Être cohérent dans un même fil de discussion

### Réactivité
- Répondre aux commentaires dans les 48h si possible
- Demander de l'aide si bloqué
- Être patient avec les revues

## Reconnaissance

### Contributeurs
Tous les contributeurs sont reconnus dans :
- Le fichier CONTRIBUTORS.md
- Les release notes
- Les remerciements dans la documentation

### Types de Contributions Valorisées
- Code
- Documentation
- Tests
- Revues de code
- Rapports de bugs
- Suggestions de fonctionnalités
- Design et UX
- Support communautaire

## Ressources Utiles

### Documentation Projet
- [Architecture](docs/technical/architecture.md)
- [Stack Technique](docs/technical/stack-technique.md)
- [Guide Lead Dev](docs/technical/lead-dev-guide.md)

### Outils
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

### Apprendre Git
- [Pro Git Book](https://git-scm.com/book/fr/v2)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)

## Questions ?

Si vous avez des questions :
1. Consultez la [documentation](docs/)
2. Cherchez dans les [issues existantes](https://github.com/remiv1/sauvetage/issues)
3. Ouvrez une [discussion](https://github.com/remiv1/sauvetage/discussions)
4. Contactez les mainteneurs

## Licence

En contribuant, vous acceptez que vos contributions soient sous licence Apache 2.0, la même que le projet.

---

**Merci de contribuer à Sauvetage ! 🚀**
