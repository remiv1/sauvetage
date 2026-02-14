#!/bin/sh
set -e

if [ -d "$1/pki" ]; then
    PKI_DIR="$1/pki"
elif [ "$1" = "." ] || [ "$1" = ".." ]; then
    PKI_DIR="$1/pki"
else
    PKI_DIR="$1"
fi

CERT_NAME="${2:-server}"
DOMAINS="${3:-*.internal,app.internal,api.internal,localhost}"
DAYS="${4:-365}"

echo "[CERTS] Génération du certificat pour: $CERT_NAME"
echo "[CERTS] PKI_DIR: $PKI_DIR"

mkdir -p "$PKI_DIR"

if [ ! -f "$PKI_DIR/ca-cert.pem" ] || [ ! -f "$PKI_DIR/ca-key.pem" ]; then
    echo "[CERTS] ERREUR: CA introuvable à $PKI_DIR"
    ls -la "$PKI_DIR/" 2>/dev/null || echo "  Le répertoire n'existe pas ou est inaccessible"
    exit 1
fi

CERT_KEY="$PKI_DIR/${CERT_NAME}-key.pem"
CERT_CSR="$PKI_DIR/${CERT_NAME}.csr"
CERT_FILE="$PKI_DIR/${CERT_NAME}-cert.pem"

if [ -f "$CERT_FILE" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || echo "0")
    
    if [ "$EXPIRY_EPOCH" = "0" ]; then
        echo "[CERTS] WARNING: Impossible de lire la date d'expiration, régénération..."

    else
        CURRENT_EPOCH=$(date +%s)
        DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))
        
        if [ $DAYS_LEFT -gt 30 ]; then
            echo "[CERTS] Certificate $CERT_NAME valid for $DAYS_LEFT more days"
            exit 0
        fi
        echo "[CERTS] WARNING: Certificate expires in $DAYS_LEFT days, renewing..."
    fi
fi

echo "[CERTS] Génération de la clé privée..."
openssl genrsa -out "$CERT_KEY" 4096 2>/dev/null

echo "[CERTS] Création de la CSR (Certificate Signing Request)..."

SAN_LIST=$(echo "$DOMAINS" | sed 's/,/,DNS:/g' | sed 's/^/DNS:/')

openssl req -new -key "$CERT_KEY" -out "$CERT_CSR" \
  -subj "/CN=*.internal/O=Sauvetage/C=FR" \
  -addext "subjectAltName=$SAN_LIST" 2>/dev/null

echo "[CERTS] Signature du certificat avec la CA..."

EXT_FILE=$(mktemp)
cat > "$EXT_FILE" << EOF
[v3_ext]
subjectAltName=$SAN_LIST
EOF

openssl x509 -req -in "$CERT_CSR" \
  -CA "$PKI_DIR/ca-cert.pem" \
  -CAkey "$PKI_DIR/ca-key.pem" \
  -CAcreateserial -out "$CERT_FILE" \
  -days $DAYS \
  -extfile "$EXT_FILE" \
  -extensions v3_ext 2>/dev/null

rm -f "$EXT_FILE"
rm -f "$CERT_CSR"

chmod 400 "$CERT_KEY"
chmod 444 "$CERT_FILE"

echo "[CERTS] Certificate generated: $CERT_FILE"
echo "[CERTS] Private key: $CERT_KEY"