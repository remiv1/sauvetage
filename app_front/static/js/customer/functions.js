/**
 * Fonctions utilitaires partagées pour le module customer.
 */

/**
 * Effectue une requête GET et retourne la réponse JSON.
 * @param {string} url - L'URL à interroger.
 * @returns {Promise<any|null>} Les données JSON ou null en cas d'erreur.
 */
export async function fetchJson(url) {
    try {
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn('[customer] Fetch GET échoué pour', url, e);
        return null;
    }
}

/**
 * Effectue une requête POST JSON et retourne la réponse.
 * @param {string} url - L'URL cible.
 * @param {object} body - Le corps de la requête.
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
        console.warn('[customer] Fetch POST échoué pour', url, e);
        return { ok: false, data: null };
    }
}

/**
 * Effectue une requête DELETE et retourne la réponse.
 * @param {string} url - L'URL cible.
 * @returns {Promise<{ok: boolean, data: any}>}
 */
export async function deleteJson(url) {
    try {
        const res = await fetch(url, { method: 'DELETE' });
        const data = await res.json();
        return { ok: res.ok, data };
    } catch (e) {
        console.warn('[customer] Fetch DELETE échoué pour', url, e);
        return { ok: false, data: null };
    }
}

/**
 * Affiche une notification temporaire dans le conteneur principal.
 * @param {string} message - Le message à afficher.
 * @param {'success'|'danger'|'warning'} type - Le type d'alerte.
 */
export function showNotification(message, type = 'success') {
    const container = document.querySelector('.customer-container');
    if (!container) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} mb-3 fade-alert`;
    alert.textContent = message;
    container.insertBefore(alert, container.firstChild);

    setTimeout(() => {
        alert.classList.add('fade-out');
        setTimeout(() => alert.remove(), 400);
    }, 3000);
}

/**
 * Collecte les données d'un formulaire dans un objet JS.
 * @param {HTMLFormElement} form - Le formulaire à sérialiser.
 * @returns {object} Un objet avec les paires nom/valeur.
 */
export function serializeForm(form) {
    const data = {};
    const formData = new FormData(form);
    for (const [key, value] of formData.entries()) {
        data[key] = value;
    }
    return data;
}
