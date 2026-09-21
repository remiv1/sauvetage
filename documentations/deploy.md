# Déploiement du projet Sauvetage

Ce document décrit les étapes nécessaires pour déployer le projet Sauvetage sur un environnement de production après avoir travaillé un temps en environnement de staging utilisateur.

## Etapes de déploiement

1. Nettoyer complètement le projet :
    ```bash
    podman compose down -v
    rm -rf documents/back/dilicom/in/*
    touch documents/back/dilicom/in/.gitkeep
    ```

2. Relancer le service ou le créer le cas échéant :
    ```bash
    mkdir -p ~/.config/systemd/user
    cp systemd/sauvetage.service ~/.config/systemd/user/sauvetage.service
    systemctl --user daemon-reload
    systemctl --user enable --now sauvetage.service
    systemctl --user start sauvetage.service
    systemctl --user status sauvetage.service
    ```
    Il peut être nécessaire d'autoriser l'accès aux ports privilégiés pour le service.
    ```bash
    sudo sysctl net.ipv4.ip_unprivileged_port_start=0
    ```
    Pour que le service soit lancé automatiquement au démarrage, même sans connection interactive :
    ```bash
    sudo loginctl enable-linger sauvetage
    ```

3. Vérifier que le service fonctionne correctement :
    ```bash
    systemctl --user status sauvetage.service
    podman ps
    ```

4. Aller sur l'outil web du projet pour créer le premier utilisateur (super-administrateur).
5. Créer les autres utilisateurs nécessaires avec les rôles appropriés via l'outil web.
6. Injecter les produits initiaux :
    ```bash
    ./datas/launcher.sh
    ```
