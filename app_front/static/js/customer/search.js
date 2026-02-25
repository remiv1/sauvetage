/**
 * Point d'entrée JS pour la page de recherche avancée client.
 * Importe et initialise le module de recherche avancée.
 */

import { setupAdvancedSearch } from './advancedSearch.js';

document.addEventListener('DOMContentLoaded', () => {
    setupAdvancedSearch();
});
