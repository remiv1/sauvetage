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
echo -e "${BLUE}[1/10] Configuration PostgreSQL${NC}"
echo ""

echo -e "${YELLOW}Génération de mots de passe sécurisés...${NC}"
PG_ROOT_PASSWORD=$(generate_password)
PG_APP_PASSWORD=$(generate_password)
PG_SECURE_PASSWORD=$(generate_password)
PG_MIGR_PASSWORD=$(generate_password)

echo -e "${GREEN}✓ Mots de passe générés${NC}"
echo ""

mkdir -p "config/env"

# Créer le fichier .env.db_main
cat > "config/env/.env.db_main" << EOF
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

echo -e "${GREEN}✓ config/env/.env.db_main créé${NC}"
chmod 600 "config/env/.env.db_main"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

# ============================================================================
# ÉTAPE 2 : Alembic Migrations
# ============================================================================

echo -e "${BLUE}[2/10] Configuration Alembic${NC}"
echo ""

# Créer le fichier environnement pour les migrations
cat > "config/env/.env.migr" << EOF
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

echo -e "${GREEN}✓ config/env/.env.migr créé${NC}"
chmod 600 "config/env/.env.migr"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

# ============================================================================
# ÉTAPE 3 : MongoDB
# ============================================================================
echo -e "${BLUE}[3/10] Configuration MongoDB${NC}"
echo ""

echo -e "${YELLOW}Génération de mots de passe sécurisés...${NC}"
MONGO_ADMIN_PASSWORD=$(generate_password)
MONGO_APP_PASSWORD=$(generate_password)

echo -e "${GREEN}✓ Mots de passe générés${NC}"
echo ""

# Créer le fichier .env.db_logs
cat > "config/env/.env.db_logs" << EOF
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

echo -e "${GREEN}✓ config/env/.env.db_logs créé${NC}"
chmod 600 "config/env/.env.db_logs"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

# ============================================================================
# ÉTAPE 4 : Traefik Proxy
# ============================================================================
echo -e "${BLUE}[4/10] Configuration Traefik Proxy${NC}"
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
cat > "config/env/.env.proxy" << EOF
TZ=${TRAEFIK_TZ}
TRAEFIK_LOG_LEVEL=${TRAEFIK_LOG_LEVEL}
EOF
chmod 600 "config/env/.env.proxy"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ config/env/.env.proxy créé${NC}"

# ============================================================================
# ÉTAPE 5 : Backend FastAPI
# ============================================================================
echo -e "${BLUE}[5/10] Configuration Backend FastAPI${NC}"
echo ""

BACKEND_LOG_LEVEL=$(prompt_value "  → Niveau de log" "info")
BACKEND_DEBUG=$(prompt_value "  → Mode DEBUG (true/false)" "false")
SECURITY_TOKEN=$(generate_password)

echo -e "${BLUE}[5bis/10] Configuration mailer SMTP${NC}"

SMTP_SERVER=$(prompt_value "  → Serveur SMTP" "smtp.example.com")
SMTP_PORT=$(prompt_value "  → Port SMTP" "587")
SMTP_USERNAME=$(prompt_value "  → Nom d'utilisateur SMTP" "example_user")
SMTP_PASSWORD=$(prompt_value "  → Mot de passe SMTP" "your_smtp_password_here")
MAIL_DEFAULT_SENDER=$(prompt_value "  → Expéditeur par défaut des mails" "First Name & Last Name | Company Name <your_email@example.com>")
SMTP_USE_TLS=$(prompt_yesno "  → Utiliser TLS pour SMTP?" "y")
SMTP_USE_SSL=$(prompt_yesno "  → Utiliser SSL pour SMTP?" "n")

echo ""

# Créer le fichier .env.fast
cat > "config/env/.env.fast" << EOF
# Application
LOG_LEVEL="${BACKEND_LOG_LEVEL}"
DEBUG="${BACKEND_DEBUG}"

# Communication FastAPI - Flask
SECURITY_TOKEN="${SECURITY_TOKEN}"

# SMTP Configuration
SMTP_SERVER="${SMTP_SERVER}"
SMTP_PORT="${SMTP_PORT}"
SMTP_USERNAME="${SMTP_USERNAME}"
SMTP_PASSWORD="${SMTP_PASSWORD}"
MAIL_DEFAULT_SENDER="${MAIL_DEFAULT_SENDER}"
SMTP_USE_TLS="${SMTP_USE_TLS}"
SMTP_USE_SSL="${SMTP_USE_SSL}"

EOF
chmod 600 "config/env/.env.fast"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ config/env/.env.fast créé${NC}"

# ============================================================================
# ÉTAPE 6 : Frontend Flask
# ============================================================================
echo -e "${BLUE}[6/10] Configuration Frontend Flask${NC}"
echo ""

FRONTEND_LOG_LEVEL=$(prompt_value "  → Niveau de log" "info")
FRONTEND_DEBUG=$(prompt_value "  → Mode DEBUG (true/false)" "false")

echo ""
echo -e "${YELLOW}Identifiants APIs externes (optionnels)${NC}"
echo ""

INVOICER_ID=$(prompt_value "  → ID de votre factureur" "your_id_here")
INVOICER_SECRET=$(prompt_value "  → Secret de votre factureur" "your_secret_here")

EBUSINESS_ID=$(prompt_value "  → ID du site de e-commerce" "your_id_here")
EBUSINESS_SECRET=$(prompt_value "  → Secret du site de e-commerce" "your_secret_here")

echo ""
echo -e "${YELLOW}Génération de la clé secrète Flask...${NC}"
FLASK_SECRET_KEY=$(generate_password)
echo -e "${GREEN}✓ Clé générée${NC}"

echo ""

# Créer le fichier .env.flask
cat > "config/env/.env.flask" << EOF
# Gestion des identifiants de l'API de votre outil de facturation
INVOICER_ID=${INVOICER_ID}
INVOICER_SECRET=${INVOICER_SECRET}

# Gestion des identifiants E-business API (site de e-commerce)
EBUSINESS_ID=${EBUSINESS_ID}
EBUSINESS_SECRET=${EBUSINESS_SECRET}

# Gestion Flask
FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
SECURITY_TOKEN=${SECURITY_TOKEN}

# Adresse de l'API FastAPI
API_URL=http://app-back:8000/api/v1

# Logging
LOG_LEVEL=${FRONTEND_LOG_LEVEL}
DEBUG=${FRONTEND_DEBUG}
EOF
chmod 600 "config/env/.env.flask"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ config/env/.env.flask créé${NC}"

# ============================================================================
# ÉTAPE 7 : Gestion WooCommerce
# ============================================================================
echo -e "${BLUE}[7/8] Configuration WooCommerce${NC}"
echo ""

if [ -f "config/env/.env.woo" ]; then
    set -a
    source "config/env/.env.woo"
    set +a
fi

WOOCOMMERCE_BASE_URL=$(prompt_value "  → URL de base WooCommerce" "${WOOCOMMERCE_BASE_URL:-https://shop.editions-sauvetage.fr}")
WOOCOMMERCE_VERIFY_SSL=$(prompt_yesno "  → Vérifier le certificat SSL WooCommerce?" "${WOOCOMMERCE_VERIFY_SSL:-y}")
WOOCOMMERCE_VERSION=$(prompt_value "  → Version de l'API WooCommerce" "${WOOCOMMERCE_VERSION:-wc/v3}")
WOOCOMMERCE_WP_API=$(prompt_yesno "  → Utiliser l'API WordPress WooCommerce?" "${WOOCOMMERCE_WP_API:-y}")
WOOCOMMERCE_READER_KEY=$(prompt_value "  → Clé WooCommerce lecture" "${WOOCOMMERCE_READER_KEY:-your_reader_key}")
WOOCOMMERCE_READER_SECRET=$(prompt_value "  → Secret WooCommerce lecture" "${WOOCOMMERCE_READER_SECRET:-your_reader_secret}")
WOOCOMMERCE_WRITER_KEY=$(prompt_value "  → Clé WooCommerce écriture" "${WOOCOMMERCE_WRITER_KEY:-your_writer_key}")
WOOCOMMERCE_WRITER_SECRET=$(prompt_value "  → Secret WooCommerce écriture" "${WOOCOMMERCE_WRITER_SECRET:-your_writer_secret}")
WOOCOMMERCE_CONSUMER_KEY=$(prompt_value "  → Clé WooCommerce consommateur" "${WOOCOMMERCE_CONSUMER_KEY:-your_consumer_key}")
WOOCOMMERCE_CONSUMER_SECRET=$(prompt_value "  → Secret WooCommerce consommateur" "${WOOCOMMERCE_CONSUMER_SECRET:-your_consumer_secret}")

cat > "config/env/.env.woo" << EOF
WOOCOMMERCE_BASE_URL=${WOOCOMMERCE_BASE_URL}
WOOCOMMERCE_VERIFY_SSL=${WOOCOMMERCE_VERIFY_SSL}
WOOCOMMERCE_VERSION=${WOOCOMMERCE_VERSION}
WOOCOMMERCE_WP_API=${WOOCOMMERCE_WP_API}
WOOCOMMERCE_READER_KEY=${WOOCOMMERCE_READER_KEY}
WOOCOMMERCE_READER_SECRET=${WOOCOMMERCE_READER_SECRET}
WOOCOMMERCE_WRITER_KEY=${WOOCOMMERCE_WRITER_KEY}
WOOCOMMERCE_WRITER_SECRET=${WOOCOMMERCE_WRITER_SECRET}
WOOCOMMERCE_CONSUMER_KEY=${WOOCOMMERCE_CONSUMER_KEY}
WOOCOMMERCE_CONSUMER_SECRET=${WOOCOMMERCE_CONSUMER_SECRET}
EOF
chmod 600 "config/env/.env.woo"
echo -e "${GREEN}✓ config/env/.env.woo créé${NC}"

# ============================================================================
# ÉTAPE 8 : Gestion Henrri
# ============================================================================
echo -e "${BLUE}[8/9] Configuration Henrri${NC}"
echo ""

if [ -f "config/env/.env.henrri" ]; then
    set -a
    source "config/env/.env.henrri"
    set +a
fi

HENRRI_BASE_URL=$(prompt_value "  → URL de base Henrri" "${HENRRI_BASE_URL:-https://api.henrri.com}")
HENRRI_API_KEY=$(prompt_value "  → Clé API Henrri" "${HENRRI_API_KEY:-your_api_key}")
HENRRI_API_SECRET=$(prompt_value "  → Secret API Henrri" "${HENRRI_API_SECRET:-your_api_secret}")

cat > "config/env/.env.henrri" << EOF
HENRRI_BASE_URL=${HENRRI_BASE_URL}
HENRRI_API_KEY=${HENRRI_API_KEY}
HENRRI_API_SECRET=${HENRRI_API_SECRET}
EOF
chmod 600 "config/env/.env.henrri"
echo -e "${GREEN}✓ config/env/.env.henrri créé${NC}"

# ============================================================================
# ÉTAPE 9 : Gestion Dilicom
# ============================================================================
echo -e "${BLUE}[9/10] Configuration Dilicom${NC}"
echo ""

DILICOM_ID=$(prompt_value "  → ID de Dilicom" "your_dilicom_id_here")
DILICOM_SECRET=$(prompt_value "  → Secret de Dilicom" "your_dilicom_secret_here")
DILICOM_HOST=$(prompt_value "  → Host de Dilicom" "ftpack.centprod.com")
DILICOM_PORT=$(prompt_value "  → Port de Dilicom" "10022")
DILICOM_OUT_DIR=$(prompt_value "  → Répertoire de sortie pour Dilicom" "/home/root/app/dilicom_out")
DILICOM_IN_DIR=$(prompt_value "  → Répertoire d'entrée pour Dilicom" "/home/root/app/dilicom_in")

echo ""

# Créer le fichier .env.dilicom
cat > "config/env/.env.dilicom" << EOF
# Configuration des dossiers et des points de montage pour Dilicom
DILICOM_OUT_DIR=${DILICOM_OUT_DIR}
DILICOM_IN_DIR=${DILICOM_IN_DIR}

# Configuration de connexion au serveur SFTP de Dilicom
DILICOM_HOST=${DILICOM_HOST}
DILICOM_PORT=${DILICOM_PORT}
DILICOM_USER=${DILICOM_ID}
DILICOM_SECRET=${DILICOM_SECRET}

EOF
chmod 600 "config/env/.env.dilicom"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ config/env/.env.dilicom créé${NC}"

cp "config/env/.env.dilicom" "config/env/.env.dilicom"

chmod 600 "config/env/.env.dilicom"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ config/env/.env.dilicom créé${NC}"

# ============================================================================
# ÉTAPE 7bis : Gestion du .env racine pour le docker-compose
# ============================================================================
echo -e "${BLUE}[7bis/10] Configuration du .env racine pour le docker-compose${NC}"
echo ""

# Créer le fichier .env
cat > ".env" << EOF
# Configuration des dossiers et des points de montage pour Dilicom
DILICOM_OUT_DIR=${DILICOM_OUT_DIR}
DILICOM_IN_DIR=${DILICOM_IN_DIR}
EOF
chmod 600 ".env"
echo -e "${GREEN}✓ Permissions appliquées (600)${NC}"

echo -e "${GREEN}✓ .env créé${NC}"


# ============================================================================
# Résumé
# ============================================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Configuration terminée avec succès!           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}Fichiers créés :${NC}"
echo "  ✓ config/env/.env.db_main"
echo "  ✓ config/env/.env.migr"
echo "  ✓ config/env/.env.db_logs"
echo "  ✓ config/env/.env.proxy"
echo "  ✓ config/env/.env.fast"
echo "  ✓ config/env/.env.flask"
echo "  ✓ config/env/.env.woo"
echo "  ✓ config/env/.env.henrri"
echo ""

echo -e "${YELLOW}Prochaines étapes:${NC}"
echo "  1. Vérifier les fichiers .env créés"
echo "  2. Lancer: podman compose up --build"
echo ""
