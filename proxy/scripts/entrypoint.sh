#!/bin/bash
set -e

echo "[ENTRYPOINT] Démarrage de Traefik avec PKI interne..."

# Chemin absolu pour la PKI
PKI_DIR="/app/pki"
mkdir -p "$PKI_DIR"

# Initialiser la CA
echo "[ENTRYPOINT] Initialisation CA..."
bash /usr/local/bin/init-pki.sh "$PKI_DIR" || {
    echo "[ENTRYPOINT] ✗ Erreur lors de l'init PKI"
    exit 1
}

# Générer les certificats
echo "[ENTRYPOINT] Génération certificats..."
bash /usr/local/bin/generate-certs.sh "$PKI_DIR" server "*.internal,app.internal,api.internal,localhost" 365 || {
    echo "[ENTRYPOINT] ✗ Erreur lors de la génération des certs"
    exit 1
}

# Vérifier les certificats
echo "[ENTRYPOINT] Vérification des certificats..."
if [ -f "$PKI_DIR/server-cert.pem" ]; then
    echo "[ENTRYPOINT] ✓ Certificat trouvé"
    openssl x509 -in "$PKI_DIR/server-cert.pem" -noout -subject -issuer -dates 2>/dev/null | grep -E "Subject:|Issuer:|Not" || echo "[ENTRYPOINT] Impossible de lire le cert"
else
    echo "[ENTRYPOINT] ✗ Certificat non trouvé à $PKI_DIR/server-cert.pem"
    ls -la "$PKI_DIR/"
    exit 1
fi

echo "[ENTRYPOINT] ✓ Configuration PKI OK, lancement de Traefik..."

# Lancer Traefik avec les arguments standards
exec traefik --configFile=/etc/traefik/traefik.yml