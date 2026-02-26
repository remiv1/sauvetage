/**
 * Fonctions utilitaires partagées pour le module inventory.
 */

/**
 * Effectue une requête GET JSON.
 * @param {string} url
 * @returns {Promise<any|null>}
 */
export async function fetchJson(url) {
    try {
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn('[inventory] Fetch GET échoué pour', url, e);
        return null;
    }
}

/**
 * Effectue une requête POST JSON.
 * @param {string} url
 * @param {any} body
 * @returns {Promise<{ok: boolean, data: any}>}
 */
export async function postJson(url, body) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        return { ok: res.ok, data };
    } catch (e) {
        console.warn('[inventory] Fetch POST échoué pour', url, e);
        return { ok: false, data: null };
    }
}

/**
 * Affiche une section et masque les autres.
 * @param {string} activeId - ID de la section à afficher.
 */
export function showStep(activeId) {
    document.querySelectorAll('.inventory-step').forEach(el => {
        el.classList.toggle('hidden', el.id !== activeId);
    });
}

/** Liste des motifs de différence possibles. */
export const MOTIFS = ['perte', 'casse', 'vol', 'erreur_saisie', 'retour', 'don', 'autre'];
