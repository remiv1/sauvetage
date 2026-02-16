# Configuration des fichiers .env - Sauvetage

Ce script automatise la création de tous les fichiers `.env` nécessaires pour déployer l'application Sauvetage.

## 🚀 Utilisation

### Depuis la racine du projet

```bash
./scripts/setup-env.sh
```

### Le script va

1. ✅ **Générer automatiquement** les mots de passe pour **PostgreSQL**
   - Superuser (postgres)
   - Utilisateur app
   - Utilisateur secure

2. ✅ **Générer automatiquement** les mots de passe pour **MongoDB**
   - Admin
   - Utilisateur app

3. ✅ Configurer **Traefik Proxy**
   - Demande d'abord : **Configuration standard?** (oui/non)
   - Si **oui** : applique automatiquement (Europe/Paris, INFO)
   - Si **non** : permet de personnaliser

4. ✅ Configurer le **Backend FastAPI**
   - Domaine
   - Niveau de log
   - Mode DEBUG

5. ✅ Configurer le **Frontend Flask**
   - Domaine
   - Niveau de log
   - Mode DEBUG
   - Identifiants APIs (Factureur, Dilicom, Site e-commerce)
   - Clé secrète générée automatiquement

## 📁 Fichiers générés

Le script crée automatiquement :

```txt
databases/main/.env.db_main          # Configuration PostgreSQL
databases/logs/.env.db_logs          # Configuration MongoDB
proxy/.env.proxy                     # Configuration Traefik
app_back/.env.fast                   # Configuration FastAPI
app_front/.env.flask                 # Configuration Flask
```

## 🔐 Sécurité

- Les mots de passe sont **générés aléatoirement** (256 bits en base64)
- Les clés secrètes sont **générées automatiquement**
- Les fichiers `.env` sont générés **localement** et ne sont **jamais** committé au git
- Ajouter `.env*` au `.gitignore` du projet

## ⚙️ Valeurs par défaut

Certains champs proposent des valeurs par défaut que tu peux accepter en pressant **Entrée** :

- Proxy : **Configuration standard** (y/n) → Europe/Paris, INFO
- Fuseau horaire : `Europe/Paris`
- Niveau de log : `INFO` (Traefik), `info` (apps)
- Mode DEBUG : `false`
- IDs APIs : `your_xxxxx_id_here` (à remplir manuellement)

## 🔄 Mise à jour

la configuration peut être mise à jour à tout moment en relançant le script :

```bash
./scripts/setup-env.sh
```

> Les fichiers existants seront **remplacés** avec de **nouveaux** mots de passe.

## 📝 Exemple de session

```txt
[1/5] Configuration PostgreSQL

Génération de mots de passe sécurisés...
✓ Mots de passe générés

✓ databases/main/.env.db_main créé
[2/5] Configuration MongoDB

Génération de mots de passe sécurisés...
✓ Mots de passe générés

✓ databases/logs/.env.db_logs créé
...
```

## 🚀 Après la configuration

Une fois les fichiers `.env` créés, tu peux démarrer l'application :

```bash
podman compose up --build -d
```

Tous les conteneurs chargent automatiquement les fichiers `.env` appropriés.

## 💡 Tips

- Sauvegarde tes mots de passe quelque part de sûr (gestionnaire de mots de passe)
- Ne partage **jamais** tes fichiers `.env` avec d'autres personnes
- Pour les IDs APIs, ils sont optionnels et peuvent être remplis ultérieurement
