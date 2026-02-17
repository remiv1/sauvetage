#!/bin/bash

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# En-tête
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Configuration des fichiers .env - Sauvetage          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Racine du projet
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Fonction pour générer un mot de passe sécurisé
generate_password() {
    openssl rand -base64 32 | tr -d '='
}

# Fonction pour demander une valeur avec défault
prompt_value() {
    local prompt="$1"
    local default="$2"
    local input=""
    
    if [ -z "$default" ]; then
        echo -en "${YELLOW}$prompt${NC}: " >&2
        read input
        [ -z "$input" ] && echo "ERROR: Valeur requise" >&2 && exit 1
        echo "$input"
    else
        echo -en "${YELLOW}$prompt${NC} [${GREEN}$default${NC}]: " >&2
        read input
        echo "${input:-$default}"
    fi
}

# Fonction pour demander oui/non
prompt_yesno() {
    local prompt="$1"
    local default="${2:-n}"
    local input=""
    
    echo -en "${YELLOW}$prompt${NC} [${GREEN}$default${NC}]: " >&2
    read input
    input="${input:-$default}"
    
    if [[ "$input" =~ ^[Yy]$ ]]; then
        echo "yes"
    else
        echo "no"
    fi
}

# ============================================================================
# ÉTAPE 1 : PostgreSQL
# ============================================================================
echo -e "${BLUE}[1/6] Configuration PostgreSQL${NC}"
echo ""

echo -e "${YELLOW}Génération de mots de passe sécurisés...${NC}"
PG_ROOT_PASSWORD=$(generate_password)
PG_APP_PASSWORD=$(generate_password)
PG_SECURE_PASSWORD=$(generate_password)
PG_MIGR_PASSWORD=$(generate_password)

echo -e "${GREEN}✓ Mots de passe générés${NC}"
echo ""

# Créer le fichier .env.db_main
cat > "databases/main/.env.db_main" << EOF
# PostgreSQL Configuration - Bases de données
POSTGRES_DB_MAIN=sauvetage_main
POSTGRES_DB_USERS=sauvetage_users

# PostgreSQL Configuration - Superuser (postgres)
POSTGRES_PASSWORD=${PG_ROOT_PASSWORD}

# PostgreSQL Configuration - Utilisateurs et mots de passe
POSTGRES_USER_APP=app
POSTGRES_PASSWORD_APP=${PG_APP_PASSWORD}

POSTGRES_USER_SECURE=secure
POSTGRES_PASSWORD_SECURE=${PG_SECURE_PASSWORD}

POSTGRES_USER_MIGR=migr
POSTGRES_PASSWORD_MIGR=${PG_MIGR_PASSWORD}

# Host et port
POSTGRES_HOST=db-main
POSTGRES_PORT=5432

# Security
POSTGRES_INITDB_ARGS=-c shared_preload_libraries=pg_stat_statements -c password_encryption=scram-sha-256

# Backup
PGBACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"
EOF

echo -e "${GREEN}✓ databases/main/.env.db_main créé${NC}"
chmod 600 "databases/main/.env.db_main"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

# ============================================================================
# ÉTAPE 2 : Alembic Migrations
# ============================================================================

echo -e "${BLUE}[2/6] Configuration Alembic${NC}"
echo ""

# Créer le fichier environnement pour les migrations
cat > "migrations/.env.migr" << EOF
# PostgreSQL Configuration - Bases de données
POSTGRES_DB_MAIN=sauvetage_main
POSTGRES_DB_USERS=sauvetage_users

# PostgreSQL Configuration - Superuser (postgres)
POSTGRES_PASSWORD=${PG_ROOT_PASSWORD}

# PostgreSQL Configuration - Utilisateurs et mots de passe
POSTGRES_USER_MIGR=migr
POSTGRES_PASSWORD_MIGR=${PG_MIGR_PASSWORD}

# Host et port
POSTGRES_HOST=db-main
POSTGRES_PORT=5432

# Backup
PGBACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"
EOF

echo -e "${GREEN}✓ migrations/.env.migr créé${NC}"
chmod 600 "migrations/.env.migr"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

# ============================================================================
# ÉTAPE 3 : MongoDB
# ============================================================================
echo -e "${BLUE}[3/6] Configuration MongoDB${NC}"
echo ""

echo -e "${YELLOW}Génération de mots de passe sécurisés...${NC}"
MONGO_ADMIN_PASSWORD=$(generate_password)
MONGO_APP_PASSWORD=$(generate_password)

echo -e "${GREEN}✓ Mots de passe générés${NC}"
echo ""

# Créer le fichier .env.db_logs
cat > "databases/logs/.env.db_logs" << EOF
# MongoDB Configuration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=${MONGO_ADMIN_PASSWORD}
MONGO_INITDB_DATABASE=sauvetage_logs

# Base de données et utilisateur applicatif
MONGO_DB_LOGS=sauvetage_logs
MONGO_USER_APP=app
MONGO_PASSWORD_APP=${MONGO_APP_PASSWORD}

# Host et port
MONGO_HOST=db-logs
MONGO_PORT=27017

# Backup
MONGO_BACKUP_ENABLED=true
MONGO_BACKUP_RETENTION_DAYS=30
EOF

echo -e "${GREEN}✓ databases/logs/.env.db_logs créé${NC}"
chmod 600 "databases/logs/.env.db_logs"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

# ============================================================================
# ÉTAPE 4 : Traefik Proxy
# ============================================================================
echo -e "${BLUE}[4/6] Configuration Traefik Proxy${NC}"
echo ""

PROXY_STANDARD=$(prompt_yesno "  → Utiliser configuration standard?" "y")

if [ "$PROXY_STANDARD" = "y" ] || [ "$PROXY_STANDARD" = "yes" ]; then
    TRAEFIK_TZ="Europe/Paris"
    TRAEFIK_LOG_LEVEL="INFO"
    echo -e "${GREEN}✓ Configuration standard appliquée${NC}"
else
    TRAEFIK_TZ=$(prompt_value "  → Fuseau horaire" "Europe/Paris")
    TRAEFIK_LOG_LEVEL=$(prompt_value "  → Niveau de log Traefik" "INFO")
fi

echo ""

# Créer le fichier .env.proxy
cat > "proxy/.env.proxy" << EOF
TZ=${TRAEFIK_TZ}
TRAEFIK_LOG_LEVEL=${TRAEFIK_LOG_LEVEL}
EOF
chmod 600 "proxy/.env.proxy"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ proxy/.env.proxy créé${NC}"

# ============================================================================
# ÉTAPE 5 : Backend FastAPI
# ============================================================================
echo -e "${BLUE}[5/6] Configuration Backend FastAPI${NC}"
echo ""

BACKEND_LOG_LEVEL=$(prompt_value "  → Niveau de log" "info")
BACKEND_DEBUG=$(prompt_value "  → Mode DEBUG (true/false)" "false")

echo ""

# Créer le fichier .env.fast
cat > "app_back/.env.fast" << EOF
# Application
LOG_LEVEL="${BACKEND_LOG_LEVEL}"
DEBUG="${BACKEND_DEBUG}"
EOF
chmod 600 "app_back/.env.fast"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ app_back/.env.fast créé${NC}"

# ============================================================================
# ÉTAPE 6 : Frontend Flask
# ============================================================================
echo -e "${BLUE}[6/6] Configuration Frontend Flask${NC}"
echo ""

FRONTEND_LOG_LEVEL=$(prompt_value "  → Niveau de log" "info")
FRONTEND_DEBUG=$(prompt_value "  → Mode DEBUG (true/false)" "false")

echo ""
echo -e "${YELLOW}Identifiants APIs externes (optionnels)${NC}"
echo ""

INVOICER_ID=$(prompt_value "  → ID de votre factureur" "your_id_here")
INVOICER_SECRET=$(prompt_value "  → Secret de votre factureur" "your_secret_here")

DILICOM_ID=$(prompt_value "  → ID de Dilicom" "your_dilicom_id_here")
DILICOM_SECRET=$(prompt_value "  → Secret de Dilicom" "your_dilicom_secret_here")

EBUSINESS_ID=$(prompt_value "  → ID du site de e-commerce" "your_id_here")
EBUSINESS_SECRET=$(prompt_value "  → Secret du site de e-commerce" "your_secret_here")

echo ""
echo -e "${YELLOW}Génération de la clé secrète Flask...${NC}"
FLASK_SECRET_KEY=$(generate_password)
echo -e "${GREEN}✓ Clé générée${NC}"

echo ""

# Créer le fichier .env.flask
cat > "app_front/.env.flask" << EOF
# Gestion des identifiants de l'API de votre outil de facturation
INVOICER_ID=${INVOICER_ID}
INVOICER_SECRET=${INVOICER_SECRET}

# Gestion des identifiants Dilicom API
DILICOM_ID=${DILICOM_ID}
DILICOM_SECRET=${DILICOM_SECRET}

# Gestion des identifiants E-business API (site de e-commerce)
EBUSINESS_ID=${EBUSINESS_ID}
EBUSINESS_SECRET=${EBUSINESS_SECRET}

# Gestion Flask
FLASK_SECRET_KEY=${FLASK_SECRET_KEY}

# Logging
LOG_LEVEL=${FRONTEND_LOG_LEVEL}
DEBUG=${FRONTEND_DEBUG}
EOF
chmod 600 "app_front/.env.flask"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ app_front/.env.flask créé${NC}"

# ============================================================================
# Résumé
# ============================================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Configuration terminée avec succès!           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}Fichiers créés :${NC}"
echo "  ✓ databases/main/.env.db_main"
echo "  ✓ migrations/.env.migr"
echo "  ✓ databases/logs/.env.db_logs"
echo "  ✓ proxy/.env.proxy"
echo "  ✓ app_back/.env.fast"
echo "  ✓ app_front/.env.flask"
echo ""

echo -e "${YELLOW}Prochaines étapes:${NC}"
echo "  1. Vérifier les fichiers .env créés"
echo "  2. Lancer: podman compose up --build"
echo ""
