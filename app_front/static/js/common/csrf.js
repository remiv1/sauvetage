/**
 * Helpers CSRF partagés par tous les modules front.
 * Le jeton est injecté par le gabarit de base dans <meta name="csrf-token">.
 */

/**
 * Retourne le jeton CSRF injecté par le gabarit de base.
 * @returns {string} Le jeton CSRF, ou une chaîne vide s'il est absent.
 */
export function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

/**
 * Construit les en-têtes d'une requête JSON protégée par CSRF.
 * @param {Record<string, string>} [extra={}] - En-têtes supplémentaires à fusionner.
 * @returns {Record<string, string>} Les en-têtes à transmettre à fetch.
 */
export function jsonHeaders(extra = {}) {
    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
        ...extra,
    };
}
