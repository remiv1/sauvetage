#!/bin/bash

# Script pour générer les fichiers de configuration MongoDB à partir des templates


set -e

echo "[DEBUG] Variables d'environnement utilisées :"
for var in "${required_vars[@]}"; do
    echo "  $var = '${!var}'"
done

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

echo "[DEBUG] INIT_DIR=$INIT_DIR"
echo "[DEBUG] CONFIG_DIR=$CONFIG_DIR"

# Générer mongod.conf à partir du template
if [ -f "$CONFIG_DIR/mongod.conf.pattern" ]; then
    echo "Génération de mongod.conf..."
    envsubst < "$CONFIG_DIR/mongod.conf.pattern" > "$CONFIG_DIR/mongod.conf"
    chmod 644 "$CONFIG_DIR/mongod.conf"
    echo "✓ mongod.conf créé"
fi

# Générer les fichiers JS d'initialisation à partir des templates

js_count=0
for template in "$INIT_DIR"/*.js.pattern; do
    if [ -f "$template" ]; then
        output="${template%.pattern}"
        echo "Génération de $(basename $output)..."
        envsubst < "$template" > "$output"
        chmod 644 "$output"
        echo "✓ $(basename $output) créé"
        js_count=$((js_count+1))
    fi
done

if [ "$js_count" -eq 0 ]; then
    echo "[WARN] Aucun fichier JS généré depuis les templates dans $INIT_DIR !"
    ls -l "$INIT_DIR"
else
    echo "[DEBUG] Fichiers JS générés :"
    ls -l "$INIT_DIR"/*.js
fi

echo "✓ Tous les fichiers de configuration MongoDB ont été générés avec succès"