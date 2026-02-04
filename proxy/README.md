# Proxy interne pour les services réseaux sur serveur local

Le réseau étant interne sans domaine publique, il n'y aura pas possibilité d'utiliser Let's Encrypt pour les certificats SSL. On procèdera donc à un CA interne avec OpenSSL.

## Process

### Créer une autorité de certification (CA) interne

```bash
# Créer un dossier pour la PKI
mkdir -p /home/remi-verschuur/Projets/sauvetage/proxy/pki
cd /home/remi-verschuur/Projets/sauvetage/proxy/pki

# Générer la clé privée de la CA (4096 bits, valide 10 ans)
openssl genrsa -out ca-key.pem 4096

# Générer le certificat de la CA
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/CN=Sauvetage-Internal-CA/O=Sauvetage/C=FR"
```

### Créer des certificats pour les services internes

```bash
cd /home/remi-verschuur/Projets/sauvetage/proxy/pki

# 1. Générer la clé privée du serveur
openssl genrsa -out server-key.pem 4096

# 2. Créer une demande de signature (CSR)
openssl req -new -key server-key.pem -out server.csr \
  -subj "/CN=*.internal/O=Sauvetage/C=FR" \
  -addext "subjectAltName=DNS:app.internal,DNS:api.internal,DNS:*.internal"

# 3. Signer avec la CA interne (valide 1 an, renouvelable)
openssl x509 -req -in server.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -days 365 \
  -extfile <(printf "subjectAltName=DNS:app.internal,DNS:api.internal,DNS:*.internal")

# Nettoyer
rm server.csr
```

### Configurer Traefik pour utiliser les certificats

Pour le Dockerfile :

```Dockerfile
FROM traefik:v2.10

# Copier les certificats dans l'image
COPY pki/server-cert.pem /etc/traefik/certs/
COPY pki/server-key.pem /etc/traefik/certs/

# Permissions
RUN chmod 400 /etc/traefik/certs/server-key.pem
```

Dans le fichier de configuration `traefik.yml` :

```yaml
global:
  checkNewVersion: false
  sendAnonymousUsage: false

api:
  dashboard: true
  insecure: false

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entrypoint:
          regex: "^http://(.*)$"
          replacement: "https://$1"
          permanent: true

  websecure:
    address: ":443"
    http:
      tls:
        certResolver: internal-ca
        domains:
          - main: "*.internal"
            sans:
              - "app.internal"
              - "api.internal"

certificatesResolvers:
  internal-ca:
    tlsChallenge: {}

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: sauvetage

  file:
    filename: /etc/traefik/dynamic/config.yml
    watch: true

log:
  level: INFO
  format: json
```

## Installation des services

```bash
sudo cp ~/Projets/sauvetage/proxy/systemd/sauv-traefik-renewer.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sauv-traefik-renewer.timer
sudo systemctl start sauv-traefik-renewer.timer
sudo systemctl status sauv-traefik-renewer.timer
```

## Mise en oeuvre globale

```bash
# 1. Rendre les scripts exécutables
chmod +x /home/remi-verschuur/Projets/sauvetage/proxy/scripts/*.sh

# 2. Lancer les containers
cd /home/remi-verschuur/Projets/sauvetage
docker-compose up -d traefik

# 3. Vérifier que la PKI a été générée
docker exec traefik ls -la /app/pki/

# 4. Vérifier les certificats
docker exec traefik openssl x509 -in /app/pki/server-cert.pem -noout -text

# 5. Installer le timer systemd
sudo systemctl enable sauv-traefik-renewer.timer
```
