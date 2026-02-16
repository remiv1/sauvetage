#!/bin/sh
set -e

if [ -d "$1/pki" ]; then
    PKI_DIR="$1/pki"
elif [ "$1" = "." ] || [ "$1" = ".." ]; then
    PKI_DIR="$1/pki"
else
    PKI_DIR="$1"
fi

echo "[PKI] Initialisation de l'autorité de certification..."

mkdir -p "$PKI_DIR"

if [ -f "$PKI_DIR/ca-cert.pem" ] && [ -f "$PKI_DIR/ca-key.pem" ]; then
    echo "[PKI] CA déjà existante"
    exit 0
fi

echo "[PKI] Génération de la CA (Autorité de Certification)..."

openssl genrsa -out "$PKI_DIR/ca-key.pem" 4096 2>/dev/null
openssl req -new -x509 -days 3650 -key "$PKI_DIR/ca-key.pem" -out "$PKI_DIR/ca-cert.pem" \
  -subj "/CN=Sauvetage-Internal-CA/O=Sauvetage/C=FR" 2>/dev/null

chmod 400 "$PKI_DIR/ca-key.pem"
chmod 444 "$PKI_DIR/ca-cert.pem"

echo "[PKI] CA créée avec succès"
echo "[PKI] Clé CA: $PKI_DIR/ca-key.pem"
echo "[PKI] Certificat CA: $PKI_DIR/ca-cert.pem"