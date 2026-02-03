#!/bin/bash

ENV_PROXY=("../proxy/.env.exemple" "../proxy/.env.proxy")
ENV_FLASK=("../app_front/.env.exemple" "../app_front/.env.flask")
ENV_FAST=("../app_back/.env.exemple" "../app_back/.env.fast")
ENV_DB_MAIN=("../databases/main/.env.exemple" "../databases/main/.env.db_main")
ENV_DB_LOGS=("../databases/logs/.env.exemple" "../databases/logs/.env.db_logs")

# Fonction pour traiter chaque paire
process_env_pair() {
    local source="$1"
    local destination="$2"
    
    if [ ! -f "$destination" ]; then
        cp "$source" "$destination"
        # Utiliser | comme délimiteur au lieu de / pour éviter les conflits
        sed -i "s|__MDP__|$(openssl rand -base64 30)|g" "$destination"
        echo "Created $destination from $source"
    else
        echo "$destination already exists, skipping."
    fi
}

# Traiter chaque paire
process_env_pair "${ENV_PROXY[0]}" "${ENV_PROXY[1]}"
process_env_pair "${ENV_FLASK[0]}" "${ENV_FLASK[1]}"
process_env_pair "${ENV_FAST[0]}" "${ENV_FAST[1]}"
process_env_pair "${ENV_DB_MAIN[0]}" "${ENV_DB_MAIN[1]}"
process_env_pair "${ENV_DB_LOGS[0]}" "${ENV_DB_LOGS[1]}"
