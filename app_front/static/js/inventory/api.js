/**
 * Module API pour le workflow d'inventaire.
 * Chaque fonction appelle le gateway Flask (/inventory/data/…)
 * qui redirige vers le micro-service FastAPI.
 */

import { postJson, fetchJson } from './functions.js';

const BASE = '/inventory/data';

/** Étape 2 – Envoyer le texte brut pour parsing. */
export async function parseEan13(raw, inventoryType = 'complete', category = null) {
    return postJson(`${BASE}/parse`, { raw, inventory_type: inventoryType, category });
}

/** Étape 3 – Obtenir les EAN13 inconnus. */
export async function getUnknownProducts(ean13List) {
    return postJson(`${BASE}/unknown`, { ean13: ean13List });
}

/** Étape 4 – Créer un nouveau produit. */
export async function createProduct(productData) {
    return postJson(`${BASE}/products`, productData);
}

/** Étape 5 – Calculer la conciliation théorique vs réel. */
export async function prepareInventory(ean13List) {
    return postJson(`${BASE}/prepare`, { ean13: ean13List });
}

/** Étape 6 – Valider les écarts. */
export async function validateInventory(lines) {
    return postJson(`${BASE}/validate`, lines);
}

/** Étape 7 – Lancer le commit asynchrone. */
export async function commitInventory(planned) {
    return postJson(`${BASE}/commit`, { planned });
}

/** Étape 8 – Obtenir l'état de la tâche de commit. */
export async function getInventoryStatus() {
    return fetchJson(`${BASE}/status`);
}

/** Fournisseurs – Rechercher par nom (autocomplete). */
export async function searchSuppliers(query) {
    return fetchJson(`${BASE}/suppliers/search?q=${encodeURIComponent(query)}`);
}

/** Fournisseurs – Créer un fournisseur minimal. */
export async function createSupplier(name) {
    return postJson(`${BASE}/suppliers`, { name });
}
