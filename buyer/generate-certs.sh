#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/ssl"

mkdir -p "$OUT_DIR"
cd "$OUT_DIR"

rm -f ca.key ca.crt ca.srl server.key server.csr server.crt cert.pem key.pem fullchain.pem server.csr.cnf server.ext

echo "Generating local CA (ca.key / ca.crt)..."
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt -subj "/CN=Local Dev CA"

echo "Generating server key and CSR..."
openssl genrsa -out server.key 2048

cat > server.csr.cnf <<'EOF'
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[ dn ]
CN = localhost

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = localhost
IP.1 = 127.0.0.1
EOF

openssl req -new -key server.key -out server.csr -config server.csr.cnf

cat > server.ext <<'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
EOF

echo "Signing server certificate with CA..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 825 -sha256 -extfile server.ext

# Put files under names expected by nginx.conf
mv -f server.crt cert.pem
mv -f server.key key.pem
cat cert.pem ca.crt > fullchain.pem

echo "Done. Files in $OUT_DIR:"
echo " - ca.crt"
echo " - cert.pem"
echo " - key.pem"
echo " - fullchain.pem"
