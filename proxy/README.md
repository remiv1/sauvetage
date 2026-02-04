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

## 📘 Webhooks – Intégration WooCommerce → Service Interne

Ce module gère la réception, la validation et le traitement des webhooks envoyés par WooCommerce lors d’événements e‑commerce (création de commande, mise à jour, etc.). Il constitue le point d’entrée permettant à l’ERP interne de rester source unique de vérité pour les stocks, les commandes et les opérations métier.

### 🎯 Objectifs

- Recevoir les événements WooCommerce en temps réel.
- Valider l’authenticité et l’intégrité des appels entrants.
- Déclencher les opérations métier internes (création de commande, décrémentation de stock, génération de documents…).
- Garantir que WooCommerce ne modifie jamais le stock : l’ERP reste maître.
- Synchroniser ensuite l’état interne vers WooCommerce via l’API sortante.

### 🧩 Architecture générale

Flux recommandé :

```txt
WooCommerce → Webhook → Service interne → Mise à jour base interne → Sync API → WooCommerce
```

WooCommerce notifie, mais ne décide jamais.
Le service interne calcule, met à jour, pousse.

### 🔔 Événements gérés

Actuellement, le service écoute :

- order.created : commande créée
- order.updated : commande modifiée

Chaque événement déclenche un handler dédié.

### 🔐 Sécurité

L’accès au webhook est strictement contrôlé.

1. Filtrage réseau
   - Le serveur n’accepte que les requêtes provenant de l’adresse IP du serveur WooCommerce (ou du reverse proxy si utilisé).
2. Signature HMAC
   - WooCommerce peut signer les webhooks via un secret partagé.
   - Le service interne vérifie :
     - la présence de l’en-tête de signature,
     - la validité du hash,
     - la correspondance avec le secret configuré.
3. HTTPS obligatoire
4. Le webhook doit être exposé en HTTPS, même en IPv6.
   - Le webhook doit être exposé en HTTPS, même en IPv6.
   - Certificat auto-signé accepté si WooCommerce est configuré pour l’accepter.
5. Route dédiée et minimaliste
   - Une seule route publique est exposée :

      ```txt
      POST /webhooks/woocommerce/order-created
      ```

   - Tout le reste du service interne reste inaccessible depuis l’extérieur.

### 📦 Payload attendu

WooCommerce envoie un JSON complet contenant :

- l’ID de commande,
- le statut,
- les lignes de commande (line_items),
- les quantités,
- les informations client,
- les totaux.

Exemple simplifié :

```json
{
  "id": 1234,
  "status": "processing",
  "line_items": [
    { "product_id": 42, "quantity": 3 },
    { "product_id": 51, "quantity": 1 }
  ]
}
```

Le service interne ne dépend pas d’un fetch ultérieur : le webhook contient tout ce qui est nécessaire.

### ⚙️ Traitement interne

Lorsqu’un webhook est reçu :

- Vérification IP source.
- Vérification de signature HMAC.
- Parsing et validation du JSON.
- Déclenchement de l’opération métier :
  - création de commande interne,
  - décrémentation du stock interne,
  - génération de documents (si applicable),
  - enregistrement dans la base interne.
  - Mise à jour du stock WooCommerce via l’API sortante.

Le service interne reste maître du stock et des règles métier.

### 🔄 Synchronisation sortante

Après traitement interne :

- le service met à jour WooCommerce via son API REST,
- uniquement pour refléter l’état interne (stock, statut, etc.), jamais l’inverse.

Cela garantit la cohérence globale.

### 🧪 Tests

#### Test local

- Simuler un webhook avec curl ou Postman.
- Désactiver temporairement la vérification IP.
- Conserver la vérification HMAC.

#### Test en environnement réel

- Utiliser l’outil de test de webhooks WooCommerce.
- Vérifier les logs du service interne.
- Vérifier la mise à jour du stock côté WooCommerce.

### 📝 Configuration

Variables d’environnement :

| Variable | Description |
| -------- | ----------- |
| WEBHOOK_SECRET | Secret HMAC partagé avec WooCommerce |
| WEBHOOK_ALLOWED_IP | IP source autorisée |
| ERP_API_URL | URL interne pour les opérations métier |
| WC_API_URL | URL de l’API WooCommerce |
| WC_API_KEY | Clé API WooCommerce |
| WC_API_SECRET | Secret API WooCommerce |

### 🛡️ Bonnes pratiques

- Ne jamais laisser WooCommerce gérer automatiquement le stock.
- Toujours vérifier la signature HMAC.
- Toujours journaliser les webhooks reçus.
- Toujours renvoyer un 200 OK si le traitement interne a été déclenché.
- Ne jamais renvoyer d’informations sensibles dans la réponse.

### 📚 Conclusion

Ce module assure une intégration propre, sécurisée et cohérente entre WooCommerce et l’ERP interne.
WooCommerce annonce, l’ERP décide, et l’ERP synchronise.
C’est la seule manière de garantir une source unique de vérité fiable et robuste.

**_Document mis à jour le 2026-02-04 par Rémi Verschuur._**
