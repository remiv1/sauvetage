#!/bin/bash
set -e

# Si le chemin existe déjà avec /pki, c'est un parent dir
# Sinon, c'est directement le dossier PKI
if [ -d "$1/pki" ] || [ "$1" = "." ] || [ "$1" = ".." ]; then
    PKI_DIR="${1:-.}/pki"
else
    # C'est déjà le chemin PKI direct
    PKI_DIR="$1"
fi

echo "[PKI] Initialisation de l'autorité de certification..."

mkdir -p "$PKI_DIR"

# Vérifier si la CA existe déjà
if [ -f "$PKI_DIR/ca-cert.pem" ] && [ -f "$PKI_DIR/ca-key.pem" ]; then
    echo "[PKI] ✓ CA déjà existante"
    exit 0
fi

echo "[PKI] Génération de la CA (Autorité de Certification)..."

openssl genrsa -out "$PKI_DIR/ca-key.pem" 4096 2>/dev/null
openssl req -new -x509 -days 3650 -key "$PKI_DIR/ca-key.pem" -out "$PKI_DIR/ca-cert.pem" \
  -subj "/CN=Sauvetage-Internal-CA/O=Sauvetage/C=FR" 2>/dev/null

chmod 400 "$PKI_DIR/ca-key.pem"
chmod 444 "$PKI_DIR/ca-cert.pem"

echo "[PKI] ✓ CA créée avec succès"
echo "[PKI] CA Key: $PKI_DIR/ca-key.pem"
echo "[PKI] CA Cert: $PKI_DIR/ca-cert.pem"