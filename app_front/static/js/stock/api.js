/**
 * Module API pour le module stock.
 * Appelle le gateway Flask (/stock/data/…).
 */

import { postJson } from './functions.js';

const BASE = '/stock/data';

/**
 * Met à jour le prix de revient d'un mouvement d'inventaire.
 * @param {number} movementId — ID du mouvement à mettre à jour.
 * @param {number} price      — Nouveau prix de revient.
 * @returns {Promise<{ok: boolean, status: number, data: any}>}
 */
export async function updatePrice(movementId, price) {
    return postJson(`${BASE}/council`, { movement_id: movementId, price });
}
