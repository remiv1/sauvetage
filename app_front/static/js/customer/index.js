/**
 * Point d'entrée JS pour la page d'accueil du module client.
 * Importe et initialise la recherche rapide.
 */

import { setupFastSearch } from './fastSearch.js';

document.addEventListener('DOMContentLoaded', () => {
    setupFastSearch();
});
