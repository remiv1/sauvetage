/**
 * Fonctions utilitaires partagées pour le module stock.
 */

/**
 * Effectue une requête POST JSON.
 * @param {string} url  — URL de l'endpoint.
 * @param {any}    body — Corps de la requête.
 * @returns {Promise<{ok: boolean, status: number, data: any}>}
 */
export async function postJson(url, body) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json().catch(() => null);
        return { ok: res.ok, status: res.status, data };
    } catch (e) {
        console.warn('[stock] POST échoué pour', url, e);
        return { ok: false, status: 0, data: null };
    }
}
