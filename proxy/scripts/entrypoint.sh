#!/bin/sh
set -e

echo "[ENTRYPOINT] Starting Traefik with internal PKI..."

PKI_DIR="/app/pki"
mkdir -p "$PKI_DIR"

echo "[ENTRYPOINT] Initializing CA..."
sh /usr/local/bin/init-pki.sh "$PKI_DIR" || {
    echo "[ENTRYPOINT] ERROR: Failed to init PKI"
    exit 1
}

echo "[ENTRYPOINT] Generating certificates..."
sh /usr/local/bin/generate-certs.sh "$PKI_DIR" server "*.internal,app.internal,api.internal,localhost" 365 || {
    echo "[ENTRYPOINT] ERROR: Failed to generate certificates"
    exit 1
}

echo "[ENTRYPOINT] Verifying certificates..."
if [ -f "$PKI_DIR/server-cert.pem" ]; then
    echo "[ENTRYPOINT] Certificate found"
    openssl x509 -in "$PKI_DIR/server-cert.pem" -noout -subject -issuer -dates 2>/dev/null | grep -iE "subject[=:]|issuer[=:]|not(before|after)" || echo "[ENTRYPOINT] Could not read certificate"
else
    echo "[ENTRYPOINT] ERROR: Certificate not found at $PKI_DIR/server-cert.pem"
    ls -la "$PKI_DIR/"
    exit 1
fi

echo "[ENTRYPOINT] PKI configuration OK, launching Traefik..."

exec traefik --configFile=/etc/traefik/traefik.yml
