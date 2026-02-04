#!/bin/bash
set -e

# Logique : si le chemin a /pki dedans ou est . ou .., c'est un parent
# Sinon c'est directement le chemin PKI
if [ -d "$1/pki" ] || [ "$1" = "." ] || [ "$1" = ".." ]; then
    PKI_DIR="${1:-.}/pki"
else
    PKI_DIR="$1"
fi

CERT_NAME="${2:-server}"
DOMAINS="${3:-*.internal,app.internal,api.internal,localhost}"
DAYS="${4:-365}"

echo "[CERTS] Génération du certificat pour : $CERT_NAME"
echo "[CERTS] PKI_DIR: $PKI_DIR"

mkdir -p "$PKI_DIR"

# Vérifier que la CA existe
if [ ! -f "$PKI_DIR/ca-cert.pem" ] || [ ! -f "$PKI_DIR/ca-key.pem" ]; then
    echo "[CERTS] ✗ CA non trouvée à $PKI_DIR !"
    ls -la "$PKI_DIR/" 2>/dev/null || echo "  Dossier inexistant"
    exit 1
fi

CERT_KEY="$PKI_DIR/${CERT_NAME}-key.pem"
CERT_CSR="$PKI_DIR/${CERT_NAME}.csr"
CERT_FILE="$PKI_DIR/${CERT_NAME}-cert.pem"

# Vérifier si le certificat existe et est valide
if [ -f "$CERT_FILE" ]; then
    # Extraire la date d'expiration et la convertir correctement
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)
    
    # Convertir "Feb  4 09:27:38 2027 GMT" en timestamp
    # Utiliser -d avec guillemets pour laisser bash expand la variable
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || echo "0")
    
    if [ "$EXPIRY_EPOCH" = "0" ]; then
        echo "[CERTS] ⚠ Impossible de parser la date d'expiration, régénération..."
    else
        CURRENT_EPOCH=$(date +%s)
        DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))
        
        if [ $DAYS_LEFT -gt 30 ]; then
            echo "[CERTS] ✓ Certificat $CERT_NAME valide pour $DAYS_LEFT jours encore"
            exit 0
        fi
        echo "[CERTS] ⚠ Certificat expire dans $DAYS_LEFT jours, renouvellement..."
    fi
fi

echo "[CERTS] Génération de la clé privée..."
openssl genrsa -out "$CERT_KEY" 4096 2>/dev/null

echo "[CERTS] Création de la demande de signature (CSR)..."

# Convertir les domaines en format DNS:domain,DNS:domain
SAN_LIST=$(echo "$DOMAINS" | sed 's/,/,DNS:/g' | sed 's/^/DNS:/')

openssl req -new -key "$CERT_KEY" -out "$CERT_CSR" \
  -subj "/CN=*.internal/O=Sauvetage/C=FR" \
  -addext "subjectAltName=$SAN_LIST" 2>/dev/null

echo "[CERTS] Signature du certificat par la CA..."

# Créer un fichier temporaire pour les extensions
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

# Nettoyer
rm -f "$EXT_FILE"
rm -f "$CERT_CSR"

# Sécuriser
chmod 400 "$CERT_KEY"
chmod 444 "$CERT_FILE"

echo "[CERTS] ✓ Certificat généré : $CERT_FILE"
echo "[CERTS] ✓ Clé privée : $CERT_KEY"