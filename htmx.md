# Notes à propos de l'HTMX

## Attributs de base

hx-get : Permet de faire une requête GET et de remplacer une partie de la page par le résultat.
hx-post : Permet de faire une requête POST et de remplacer une partie de la page par le résultat.
hx-put : Permet de faire une requête PUT et de remplacer une partie de la page par le résultat.
hx-delete : Permet de faire une requête DELETE et de remplacer une partie de la page par le résultat.
hx-target : Permet de cibler un élément de la page pour y injecter le résultat d'une requête.
hx-swap : Permet de définir comment le résultat d'une requête doit être injecté dans la page (innerHTML, outerHTML, etc.).
hx-trigger : Permet de déclencher une requête en fonction d'un événement (click, change, etc.).
hx-set : Permet de définir des attributs sur un élément après une requête (par exemple, pour mettre à jour un compteur).

## Autres attributs utiles

hx-vals : Permet de passer des données supplémentaires dans une requête.
hx-include : Permet d'inclure des éléments de la page dans une requête (par exemple, pour envoyer les données d'un formulaire).
hx-confirm : Permet d'afficher une confirmation avant de déclencher une requête.
hx-indicator : Permet d'afficher un indicateur de chargement pendant une requête.
hx-push-url : Permet de mettre à jour l'URL du navigateur après une requête.
hx-params : Permet de définir les paramètres d'une requête (par exemple, pour envoyer des données JSON).
hx-headers : Permet de définir les en-têtes d'une requête.
hx-on : Permet de définir des événements personnalisés à déclencher après une requête.
