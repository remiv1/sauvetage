# Build SCSS → CSS

Pour compiler tous les SCSS du projet en CSS, utiliser:

```bash
# Compiler un seul fichier
sass app_front/static/css/supplier/list.scss app_front/static/css/supplier/list.css

# Ou compiler toute la structure supplier
sass app_front/static/css/supplier/ app_front/static/css/supplier/

# Ou compiler tout CSS (avec watch mode)
sass --watch app_front/static/css/:app_front/static/css/
```

## Structure SCSS

Le projet utilise une architecture SCSS modulaire avec `@use` et `@forward`:

- **core/_variables.scss** - Couleurs, typographie, espacement, radius, ombres
- **core/_mixins.scss** - Utilitaires de layout (flex-center, card, input-base, etc.)
- **supplier/list.scss** - Styles spécifiques au module supplier

## Notes de compilation

- Les fichiers `@import` du core sont fusionnés automatiquement
- Les variables et mixins sont namespaced (`@use ... as v`, `@use ... as m`)
- Le CSS résultant est optimisé avec minification possible via `--style=compressed`
