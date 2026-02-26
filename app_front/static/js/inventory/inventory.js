/**
 * Point d'entrée du module inventaire.
 * Orchestre les étapes du workflow.
 */

import { setupInput, getParseResult } from './input.js';
import { setupUnknown, showUnknownStep } from './unknown.js';
import { setupReconcile, showReconcileStep } from './reconcile.js';
import { setupStatus, startCommit } from './status.js';

// Listener global pour orchestrer les étapes du workflow
document.addEventListener('DOMContentLoaded', () => {
    // --- Étape 2 : après parsing ---
    setupInput((parseResult) => {
        if (parseResult.unknown && parseResult.unknown.length > 0) {
            showUnknownStep(parseResult.unknown);
        } else {
            // Pas d'inconnus → directement à la conciliation
            showReconcileStep(parseResult.ean13);
        }
    });

    // --- Étape 3-4 : après résolution des inconnus ---
    setupUnknown(() => {
        const result = getParseResult();
        if (result) {
            showReconcileStep(result.ean13);
        }
    });

    // --- Étape 5-6 : après validation des écarts ---
    setupReconcile((planned) => {
        startCommit(planned);
    });

    // --- Étape 8 : statut ---
    setupStatus();
});
