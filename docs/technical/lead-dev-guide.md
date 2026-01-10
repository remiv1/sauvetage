# Guide Lead Developer - Projet Sauvetage

## Rôle et Responsabilités

### Vue d'ensemble
Le Lead Developer est responsable de la direction technique du projet, de la qualité du code et du mentoring de l'équipe.

### Responsabilités Principales

#### 1. Architecture et Conception
- Définir et maintenir l'architecture technique
- Prendre les décisions techniques majeures
- Assurer la cohérence architecturale entre les services
- Veiller à la scalabilité et la performance

#### 2. Qualité du Code
- Établir et faire respecter les standards de code
- Effectuer les revues de code critiques
- Mettre en place les outils de qualité (linting, tests)
- Garantir la maintenabilité du code

#### 3. Leadership Technique
- Guider l'équipe de développement
- Mentorer les développeurs juniors
- Résoudre les blocages techniques
- Faciliter les décisions techniques

#### 4. Documentation
- Maintenir la documentation technique à jour
- Documenter les décisions d'architecture (ADR)
- Créer des guides pour l'équipe

## Standards de Code

### Principes SOLID
- **S**ingle Responsibility
- **O**pen/Closed
- **L**iskov Substitution
- **I**nterface Segregation
- **D**ependency Inversion

### Clean Code
- Noms explicites et significatifs
- Fonctions courtes et focalisées
- Commentaires uniquement quand nécessaire
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)

### Convention de Nommage

#### TypeScript/JavaScript
```typescript
// Classes : PascalCase
class UserService {}

// Fonctions/Variables : camelCase
const getUserById = () => {}
let userId = 123

// Constantes : UPPER_SNAKE_CASE
const API_BASE_URL = 'https://api.example.com'

// Interfaces/Types : PascalCase avec préfixe I (optionnel)
interface User {}
type UserRole = 'admin' | 'user'

// Fichiers : kebab-case
// user-service.ts
// auth-middleware.ts
```

#### Python
```python
# Classes : PascalCase
class UserService:
    pass

# Fonctions/Variables : snake_case
def get_user_by_id():
    pass

user_id = 123

# Constantes : UPPER_SNAKE_CASE
API_BASE_URL = 'https://api.example.com'

# Fichiers : snake_case
# user_service.py
# auth_middleware.py
```

### Structure des Fichiers

#### Backend (TypeScript)
```
src/
├── config/          # Configuration
├── controllers/     # Contrôleurs API
├── services/        # Logique métier
├── repositories/    # Accès aux données
├── models/          # Modèles de données
├── middlewares/     # Middlewares Express
├── routes/          # Définition des routes
├── utils/           # Utilitaires
├── types/           # Types TypeScript
└── tests/           # Tests
```

#### Frontend (React)
```
src/
├── components/      # Composants réutilisables
│   ├── ui/         # Composants UI de base
│   └── features/   # Composants métier
├── pages/          # Pages de l'application
├── hooks/          # Custom hooks
├── services/       # Services API
├── store/          # State management
├── utils/          # Utilitaires
├── types/          # Types TypeScript
├── assets/         # Images, fonts, etc.
└── tests/          # Tests
```

## Processus de Revue de Code

### Checklist de Revue

#### Fonctionnalité
- [ ] Le code fait ce qu'il est censé faire
- [ ] Les cas limites sont gérés
- [ ] Les erreurs sont correctement traitées

#### Qualité
- [ ] Le code est lisible et compréhensible
- [ ] Pas de code dupliqué
- [ ] Nommage approprié
- [ ] Commentaires pertinents uniquement

#### Tests
- [ ] Tests unitaires présents et passants
- [ ] Couverture de code acceptable (>80%)
- [ ] Tests des cas limites

#### Sécurité
- [ ] Pas de données sensibles en dur
- [ ] Validation des entrées
- [ ] Protection contre les vulnérabilités courantes

#### Performance
- [ ] Pas de code inefficace évident
- [ ] Requêtes DB optimisées
- [ ] Utilisation appropriée du cache

### Feedback Constructif
- Être respectueux et professionnel
- Expliquer le "pourquoi" derrière les suggestions
- Proposer des alternatives
- Reconnaître les bonnes pratiques

## Gestion des Dettes Techniques

### Identification
- Marquer avec `// TODO:` ou `// FIXME:`
- Créer des issues GitHub avec label `tech-debt`
- Documenter dans un registre de dette technique

### Priorisation
1. **Critique** : Bloque le développement ou affecte la production
2. **Haute** : Impact significatif sur la productivité
3. **Moyenne** : Amélioration souhaitable
4. **Basse** : Nice to have

### Remboursement
- Allouer 20% du temps de sprint à la dette technique
- Intégrer dans les sprints de maintenance
- Ne pas accumuler au-delà d'un seuil défini

## Décisions d'Architecture (ADR)

### Format
Utiliser le template ADR pour documenter les décisions importantes :

```markdown
# ADR-XXX: Titre de la Décision

Date: YYYY-MM-DD

## Statut
[Proposé | Accepté | Déprécié | Remplacé par ADR-YYY]

## Contexte
Quel est le problème/la situation qui nécessite une décision ?

## Décision
Quelle décision a été prise ?

## Conséquences
Quelles sont les implications positives et négatives ?

## Alternatives Considérées
Quelles autres options ont été évaluées ?
```

### Localisation
Stocker les ADR dans `docs/technical/adr/`

## Outils du Lead Developer

### Analyse de Code
- **SonarQube** : Qualité et sécurité
- **ESLint** / **Ruff** : Linting
- **Prettier** / **Black** : Formatage

### Monitoring
- Métriques de performance
- Logs centralisés
- Alertes sur erreurs

### Communication
- Documentation claire et accessible
- Réunions techniques régulières
- Pair programming quand nécessaire

## Mentoring

### Développeurs Juniors
- Pair programming régulier
- Revues de code éducatives
- Partage de ressources d'apprentissage
- Encourager les questions

### Développeurs Intermédiaires
- Déléguer des décisions techniques
- Impliquer dans l'architecture
- Encourager la prise d'initiative

## Veille Technologique

### Rester à Jour
- Suivre les blogs techniques
- Participer à des conférences
- Expérimenter avec de nouvelles technologies
- Partager les connaissances avec l'équipe

### Évaluation de Nouvelles Technologies
- Prouver la valeur ajoutée
- Considérer le coût d'apprentissage
- Évaluer la maturité et le support
- Faire des POCs avant adoption

## Gestion des Crises

### Bugs Critiques en Production
1. Identifier et isoler le problème
2. Déployer un hotfix si possible
3. Communiquer avec les parties prenantes
4. Post-mortem pour éviter la récurrence

### Escalade
Savoir quand et comment escalader les problèmes critiques.

## Amélioration Continue

### Rétrospectives Techniques
- Organiser des sessions régulières
- Identifier les problèmes récurrents
- Implémenter des améliorations

### KPIs Techniques
- Vélocité de l'équipe
- Taux de bugs
- Temps de revue de code
- Dette technique

## Conclusion

Le rôle de Lead Developer est autant technique qu'humain. L'objectif est de créer une équipe productive, un code de qualité et un produit performant.

**Questions?** N'hésitez pas à ouvrir une discussion ou contacter le Lead Developer actuel.
