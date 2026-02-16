#!/bin/bash

# Script pour générer les fichiers de configuration MongoDB à partir des templates

set -e

INIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(dirname "$INIT_DIR")"

# Vérifier que les variables nécessaires sont définies
required_vars=(
    "MONGO_INITDB_ROOT_USERNAME"
    "MONGO_INITDB_ROOT_PASSWORD"
    "MONGO_DB_LOGS"
    "MONGO_USER_APP"
    "MONGO_PASSWORD_APP"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Erreur: Variable $var non définie"
        exit 1
    fi
done

# Générer mongod.conf à partir du template
if [ -f "$CONFIG_DIR/mongod.conf.pattern" ]; then
    echo "Génération de mongod.conf..."
    envsubst < "$CONFIG_DIR/mongod.conf.pattern" > "$CONFIG_DIR/mongod.conf"
    chmod 644 "$CONFIG_DIR/mongod.conf"
    echo "✓ mongod.conf créé"
fi

# Générer les fichiers JS d'initialisation à partir des templates
for template in "$INIT_DIR"/*.js.pattern; do
    if [ -f "$template" ]; then
        output="${template%.pattern}"
        echo "Génération de $(basename $output)..."
        
        # Remplacer tous les patterns ${VAR} par leurs valeurs
        envsubst < "$template" > "$output"
        chmod 644 "$output"
        echo "✓ $(basename $output) créé"
    fi
done

echo "✓ Tous les fichiers de configuration MongoDB ont été générés avec succès"