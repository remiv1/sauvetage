/**
 * Module API pour le workflow d'inventaire.
 * Chaque fonction appelle le gateway Flask (/inventory/data/…)
 * qui redirige vers le micro-service FastAPI.
 */

import { postJson, fetchJson } from './functions.js';

// Base URL pour les appels API du module inventaire
const BASE = '/inventory/data';
const BASE_SUPPLIERS = '/supplier/data';

/** Étape 2 – Envoyer le texte brut pour parsing. */
export async function parseEan13(raw, inventoryType = 'complete', category = null) {
    return postJson(`${BASE}/parse`, { raw, inventory_type: inventoryType, category });
}

/** Étape 4 – Créer un nouveau produit. */
export async function createProduct(productData) {
    return postJson(`${BASE}/products`, productData);
}

/** Etape 4bis - Création d'un fournisseur. */
export async function createSupplier(data) {
    return postJson(`${BASE_SUPPLIERS}/suppliers`, { data });
}

/** Étape 5 – Calculer la conciliation théorique vs réel. */
export async function prepareInventory(ean13List, inventoryType = null) {
    return postJson(`${BASE}/prepare`, { ean13: ean13List, inventory_type: inventoryType });
}

/** Étape 6 – Valider les écarts. */
export async function validateInventory(lines, inventoryType = null) {
    return postJson(`${BASE}/validate`, { lines: lines, inventory_type: inventoryType });
}

/** Étape 7 – Lancer le commit asynchrone. */
export async function commitInventory(planned, inventoryType = null) {
    return postJson(`${BASE}/commit`, { planned: planned, inventory_type: inventoryType });
}

/** Étape 8 – Obtenir l'état de la tâche de commit. */
export async function getInventoryStatus() {
    return fetchJson(`${BASE}/status`);
}

/** Fournisseurs – Rechercher par nom (autocomplete). */
export async function searchSuppliers(query) {
    const typeOfData = "id_and_name";
    return fetchJson(`${BASE_SUPPLIERS}/search?q=${encodeURIComponent(query)}&type_of_data=${typeOfData}`);
}
