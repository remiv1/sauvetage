/**
 * Point d'entrée JS pour la page de création client.
 * Importe et initialise le module de gestion du formulaire.
 */

import { setupCreateForm } from './form.js';

document.addEventListener('DOMContentLoaded', () => {
    setupCreateForm();
});
