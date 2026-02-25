# PowerShell - Configuration des fichiers .env - Sauvetage

# Couleurs (pour Write-Host)
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"
$NC = "White"

# En-tête
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor $BLUE
Write-Host "║   Configuration des fichiers .env - Sauvetage          ║" -ForegroundColor $BLUE
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor $BLUE
Write-Host ""

# Racine du projet
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $PROJECT_ROOT

# Fonction pour générer un mot de passe sécurisé
function Generate-Password {
    [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 } | ForEach-Object { [byte]$_ })) -replace '=', ''
}

# Fonction pour demander une valeur avec défaut
function Prompt-Value {
    param(
        [string]$Prompt,
        [string]$Default = $null
    )
    if ($null -eq $Default -or $Default -eq "") {
        Write-Host "$Prompt : " -ForegroundColor $YELLOW -NoNewline
        $input = Read-Host
        if ([string]::IsNullOrWhiteSpace($input)) {
            Write-Host "ERREUR: Valeur requise" -ForegroundColor $RED
            exit 1
        }
        return $input
    } else {
        Write-Host "$Prompt [$Default] : " -ForegroundColor $YELLOW -NoNewline
        $input = Read-Host
        if ([string]::IsNullOrWhiteSpace($input)) { return $Default } else { return $input }
    }
}

# Fonction pour demander oui/non
function Prompt-YesNo {
    param(
        [string]$Prompt,
        [string]$Default = 'n'
    )
    Write-Host "$Prompt [$Default] : " -ForegroundColor $YELLOW -NoNewline
    $input = Read-Host
    if ([string]::IsNullOrWhiteSpace($input)) { $input = $Default }
    if ($input -match '^[Yy]$') { return 'yes' } else { return 'no' }
}

# ============================================================================
# ÉTAPE 1 : PostgreSQL
# ============================================================================
Write-Host "[1/6] Configuration PostgreSQL" -ForegroundColor $BLUE
Write-Host ""

Write-Host "Génération de mots de passe sécurisés..." -ForegroundColor $YELLOW
$PG_ROOT_PASSWORD = Generate-Password
$PG_APP_PASSWORD = Generate-Password
$PG_SECURE_PASSWORD = Generate-Password
$PG_MIGR_PASSWORD = Generate-Password
Write-Host "✓ Mots de passe générés" -ForegroundColor $GREEN
Write-Host ""

$envDbMain = @"
# PostgreSQL Configuration - Bases de données
POSTGRES_DB_MAIN=sauvetage_main
POSTGRES_DB_USERS=sauvetage_users

# PostgreSQL Configuration - Superuser (postgres)
POSTGRES_PASSWORD=$PG_ROOT_PASSWORD

# PostgreSQL Configuration - Utilisateurs et mots de passe
POSTGRES_USER_APP=app
POSTGRES_PASSWORD_APP=$PG_APP_PASSWORD

POSTGRES_USER_SECURE=secure
POSTGRES_PASSWORD_SECURE=$PG_SECURE_PASSWORD

POSTGRES_USER_MIGR=migr
POSTGRES_PASSWORD_MIGR=$PG_MIGR_PASSWORD

# Host et port
POSTGRES_HOST=db-main
POSTGRES_PORT=5432

# Security
POSTGRES_INITDB_ARGS=-c shared_preload_libraries=pg_stat_statements -c password_encryption=scram-sha-256

# Backup
PGBACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"
"@
$envDbMainPath = "databases/main/.env.db_main"
$envDbMain | Set-Content -Path $envDbMainPath -Encoding UTF8
Write-Host "✓ $envDbMainPath créé" -ForegroundColor $GREEN

# ============================================================================
# ÉTAPE 2 : Alembic Migrations
# ============================================================================
Write-Host "[2/6] Configuration Alembic" -ForegroundColor $BLUE
Write-Host ""
$envMigr = @"
# PostgreSQL Configuration - Bases de données
POSTGRES_DB_MAIN=sauvetage_main
POSTGRES_DB_USERS=sauvetage_users

# PostgreSQL Configuration - Superuser (postgres)
POSTGRES_PASSWORD=$PG_ROOT_PASSWORD

# PostgreSQL Configuration - Utilisateurs et mots de passe
POSTGRES_USER_MIGR=migr
POSTGRES_PASSWORD_MIGR=$PG_MIGR_PASSWORD

# Host et port
POSTGRES_HOST=db-main
POSTGRES_PORT=5432

# Backup
PGBACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"
"@
$envMigrPath = "migrations/.env.migr"
$envMigr | Set-Content -Path $envMigrPath -Encoding UTF8
Write-Host "✓ $envMigrPath créé" -ForegroundColor $GREEN

# ============================================================================
# ÉTAPE 3 : MongoDB
# ============================================================================
Write-Host "[3/6] Configuration MongoDB" -ForegroundColor $BLUE
Write-Host ""
Write-Host "Génération de mots de passe sécurisés..." -ForegroundColor $YELLOW
$MONGO_ADMIN_PASSWORD = Generate-Password
$MONGO_APP_PASSWORD = Generate-Password
Write-Host "✓ Mots de passe générés" -ForegroundColor $GREEN
Write-Host ""
$envDbLogs = @"
# MongoDB Configuration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=$MONGO_ADMIN_PASSWORD

# Base de données et utilisateur applicatif
MONGO_DB_LOGS=sauvetage_logs
MONGO_USER_APP=app
MONGO_PASSWORD_APP=$MONGO_APP_PASSWORD

# Host et port
MONGO_HOST=db-logs
MONGO_PORT=27017

# Backup
MONGO_BACKUP_ENABLED=true
MONGO_BACKUP_RETENTION_DAYS=30
"@
$envDbLogsPath = "databases/logs/.env.db_logs"
$envDbLogs | Set-Content -Path $envDbLogsPath -Encoding UTF8
Write-Host "✓ $envDbLogsPath créé" -ForegroundColor $GREEN

# ============================================================================
# ÉTAPE 4 : Traefik Proxy
# ============================================================================
Write-Host "[4/6] Configuration Traefik Proxy" -ForegroundColor $BLUE
Write-Host ""
$PROXY_STANDARD = Prompt-YesNo "  → Utiliser configuration standard?" "y"
if ($PROXY_STANDARD -eq "y" -or $PROXY_STANDARD -eq "yes") {
    $TRAEFIK_TZ = "Europe/Paris"
    $TRAEFIK_LOG_LEVEL = "INFO"
    Write-Host "✓ Configuration standard appliquée" -ForegroundColor $GREEN
} else {
    $TRAEFIK_TZ = Prompt-Value "  → Fuseau horaire" "Europe/Paris"
    $TRAEFIK_LOG_LEVEL = Prompt-Value "  → Niveau de log Traefik" "INFO"
}
Write-Host ""
$envProxy = @"
TZ=$TRAEFIK_TZ
TRAEFIK_LOG_LEVEL=$TRAEFIK_LOG_LEVEL
"@
$envProxyPath = "proxy/.env.proxy"
$envProxy | Set-Content -Path $envProxyPath -Encoding UTF8
Write-Host "✓ $envProxyPath créé" -ForegroundColor $GREEN

# ============================================================================
# ÉTAPE 5 : Backend FastAPI
# ============================================================================
Write-Host "[5/6] Configuration Backend FastAPI" -ForegroundColor $BLUE
Write-Host ""
$BACKEND_LOG_LEVEL = Prompt-Value "  → Niveau de log" "info"
$BACKEND_DEBUG = Prompt-Value "  → Mode DEBUG (true/false)" "false"
Write-Host ""
$envFast = @"
# Application
LOG_LEVEL=\"$BACKEND_LOG_LEVEL\"
DEBUG=\"$BACKEND_DEBUG\"
"@
$envFastPath = "app_back/.env.fast"
$envFast | Set-Content -Path $envFastPath -Encoding UTF8
Write-Host "✓ $envFastPath créé" -ForegroundColor $GREEN

# ============================================================================
# ÉTAPE 6 : Frontend Flask
# ============================================================================
Write-Host "[6/6] Configuration Frontend Flask" -ForegroundColor $BLUE
Write-Host ""
$FRONTEND_LOG_LEVEL = Prompt-Value "  → Niveau de log" "info"
$FRONTEND_DEBUG = Prompt-Value "  → Mode DEBUG (true/false)" "false"
Write-Host ""
Write-Host "Identifiants APIs externes (optionnels)" -ForegroundColor $YELLOW
Write-Host ""
$INVOICER_ID = Prompt-Value "  → ID de votre factureur" "your_id_here"
$INVOICER_SECRET = Prompt-Value "  → Secret de votre factureur" "your_secret_here"
$DILICOM_ID = Prompt-Value "  → ID de Dilicom" "your_dilicom_id_here"
$DILICOM_SECRET = Prompt-Value "  → Secret de Dilicom" "your_dilicom_secret_here"
$EBUSINESS_ID = Prompt-Value "  → ID du site de e-commerce" "your_id_here"
$EBUSINESS_SECRET = Prompt-Value "  → Secret du site de e-commerce" "your_secret_here"
Write-Host ""
Write-Host "Génération de la clé secrète Flask..." -ForegroundColor $YELLOW
$FLASK_SECRET_KEY = Generate-Password
Write-Host "✓ Clé générée" -ForegroundColor $GREEN
Write-Host ""
$envFlask = @"
# Gestion des identifiants de l'API de votre outil de facturation
INVOICER_ID=$INVOICER_ID
INVOICER_SECRET=$INVOICER_SECRET

# Gestion des identifiants Dilicom API
DILICOM_ID=$DILICOM_ID
DILICOM_SECRET=$DILICOM_SECRET

# Gestion des identifiants E-business API (site de e-commerce)
EBUSINESS_ID=$EBUSINESS_ID
EBUSINESS_SECRET=$EBUSINESS_SECRET

# Gestion Flask
FLASK_SECRET_KEY=$FLASK_SECRET_KEY

# Logging
LOG_LEVEL=$FRONTEND_LOG_LEVEL
DEBUG=$FRONTEND_DEBUG
"@
$envFlaskPath = "app_front/.env.flask"
$envFlask | Set-Content -Path $envFlaskPath -Encoding UTF8
Write-Host "✓ $envFlaskPath créé" -ForegroundColor $GREEN

# ============================================================================
# Résumé
# ============================================================================
Write-Host ""; Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor $BLUE
Write-Host "║          Configuration terminée avec succès!           ║" -ForegroundColor $BLUE
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor $BLUE
Write-Host ""
Write-Host "Fichiers créés :" -ForegroundColor $GREEN
Write-Host "  ✓ databases/main/.env.db_main"
Write-Host "  ✓ migrations/.env.migr"
Write-Host "  ✓ databases/logs/.env.db_logs"
Write-Host "  ✓ proxy/.env.proxy"
Write-Host "  ✓ app_back/.env.fast"
Write-Host "  ✓ app_front/.env.flask"
Write-Host ""
Write-Host "Prochaines étapes:" -ForegroundColor $YELLOW
Write-Host "  1. Vérifier les fichiers .env créés"
Write-Host "  2. Lancer: podman compose up --build"
Write-Host ""
