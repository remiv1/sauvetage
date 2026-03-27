# Rapport : Templates dropdown fournisseurs

## Situation avant nettoyage

Il existait **5 templates** dans ce dossier avec un usage incohérent :

- `suppliers_dropdown.html` — orphelin, plus rendu par aucune route
- `dilicom_suppliers_dropdown.html` — utilisé dans des contextes non-Dilicom (mauvais nommage)
- `select_supplier.html` — orphelin par conséquent
- `select_dilicom_supplier.html` — fonctionnel mais utilisé hors contexte Dilicom
- `filter_suppliers_dropdown.html` — propre, piloté par JS ✅

Problèmes principaux :

- Pas de bouton « Créer un fournisseur » dans les formulaires stock/commande alors que l'infra existait
- Nommage confus (« dilicom » pour des templates utilisés partout)
- Templates orphelins accumulés

---

## Architecture après nettoyage

### Templates restants (3 fichiers)

| Template | Rôle | Paramètres |
| --- | --- | --- |
| `suppliers_dropdown.html` | Dropdown unifié (HTMX) | `suppliers`, `query`, `allow_create`, `context` |
| `select_supplier.html` | Fragment OOB après sélection | `supplier_id`, `supplier_name`, `gln13`, `context`, `allow_create` |
| `filter_suppliers_dropdown.html` | Dropdown filtres (JS) | `suppliers` — inchangé |

### Templates supprimés

- `dilicom_suppliers_dropdown.html` — fusionné dans `suppliers_dropdown.html`
- `select_dilicom_supplier.html` — fusionné dans `select_supplier.html`

### Route unifiée

La route `get_suppliers(type_of_data)` accepte maintenant :

- `type_of_data='id_name_gln'` → `suppliers_dropdown.html` (avec `allow_create` et `context`)
- `type_of_data='filter'` → `filter_suppliers_dropdown.html` (inchangé)

La route `select_supplier` est unifiée (la route `select_dilicom_supplier` est supprimée).
Le paramètre `context` (`"stock"` ou `"dilicom"`) détermine les IDs DOM pour les swaps OOB.

---

## Flux par contexte

```txt
Route get_suppliers(type_of_data='id_name_gln')
 ├── context='stock', allow_create=true   → suppliers_dropdown.html (avec ➕ Créer)
 │    └── clic item → select_supplier(context='stock') → select_supplier.html (#supplier_id)
 │    └── liste vide → add_new_supplier → add_supplier_form.html
 │
 ├── context='dilicom', allow_create=false → suppliers_dropdown.html (sans ➕ Créer)
 │    └── clic item → select_supplier(context='dilicom') → select_supplier.html (#dilicom-gln13)
 │
 └── type_of_data='filter' → filter_suppliers_dropdown.html (JS uniquement)
```

---

## État des templates par contexte d'utilisation

| Contexte | `allow_create` | `context` | Création possible ? | Correct ? |
| --- | --- | --- | --- | --- |
| Formulaire objet stock (`single_object_form.html`) | `true` | `stock` | ✅ Oui | ✅ |
| Formulaire nouvelle commande (`new.html`) | `true` | `stock` | ✅ Oui | ✅ |
| Modale Dilicom (`dilicom_modal.html`) | `false` | `dilicom` | Non (voulu) | ✅ |
| Filtres stock (`search.html`) | — | — | Non (JS) | ✅ |
