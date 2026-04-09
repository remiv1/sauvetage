# Gestion de services avec systemd

## Autoriser l'utilisateur à lancer des services systemd sans connection SSH

```bash
sudo loginctl enable-linger <ton_nom_utilisateur>
```

## Copier le fichier de service dans le dossier systemd de l'utilisateur

```bash
# Copier le fichier de service dans le dossier systemd de l'utilisateur
mkdir -p ~/.config/systemd/user
cp ./systemd/sauvetage.service ~/.config/systemd/user/
```

## Installation de l'application métier en tant que service systemd

```bash
# Recharger systemd pour voir le nouveau service
systemctl --user daemon-reload

# Activer le service pour qu'il se lance au démarrage du serveur
systemctl --user enable sauvetage.service

# Lancer l'app immédiatement
systemctl --user start sauvetage.service
```

## Problèmes courants

### Vérifier que le service est bien lancé :

```bash
systemctl --user status sauvetage.service
```

### Problème de localisation de podman-compose :

```bash
# Vérifier que le chemin de podman-compose est correct
which podman-compose
```

- Si c'est /usr/bin/podman-compose, ton fichier est bon, mais il y a un souci de permission.
- Si c'est /usr/local/bin/podman-compose ou ~/.local/bin/podman-compose, il faut corriger le fichier service en décommentant les bonnes lignes et en commentant les mauvaises.

