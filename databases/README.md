# Base de données NoSQL de logs

## Commandes utiles

### Connection à la base de données

```bash
podman compose exec db-logs mongosh "mongodb://<user>:<password>@<host>:<port>/<database>?authSource=<auth_db>"
```

### Recherche manuelle

```bash
db[<collection>].find({ <k>: <v> }).sort({ <k>: -1 }).limit(<nb>)
```
