/**
 * Gestion de l'étape « Saisie des EAN13 » (étape 2).
 */

import { showStep } from './functions.js';
import * as api from './api.js';

// Création des variables globales
/** @type {string|null} Type d'inventaire sélectionné. */
let currentType = null;
/** @type {object|null} Dernière réponse de parsing. */
let lastParseResult = null;

/** Retourne le type d'inventaire courant. */
export function getType() {
    return currentType;
}

/** Retourne le résultat du dernier parsing. */
export function getParseResult() {
    return lastParseResult;
}

/**
 * Initialise les événements de l'étape choix + saisie.
 * @param {Function} onParsed — callback(parseResult) pour passer à l'étape suivante.
 */
export function setupInput(onParsed) {
    const cards         = document.querySelectorAll('.inventory-card');
    const textareaRow   = document.getElementById('textarea-row');
    const singleRow     = document.getElementById('single-row');
    const categoryRow   = document.getElementById('category-row');
    const btnParse      = document.getElementById('btn-parse');
    const btnBackChoice = document.getElementById('btn-back-choice');
    const inputTitle    = document.getElementById('input-title');

    // Choix du type
    cards.forEach(card => {
        card.addEventListener('click', () => {
            currentType = card.dataset.type;
            inputTitle.textContent = {
                complete: 'Inventaire Complet — Saisie des EAN13',
                partial:  'Inventaire Partiel — Saisie des EAN13',
                single:   'Article Unique — Saisie de l\'EAN13',
            }[currentType] || 'Saisie des EAN13';

            textareaRow.classList.toggle('hidden', currentType === 'single');
            singleRow.classList.toggle('hidden',   currentType !== 'single');
            categoryRow.classList.toggle('hidden',  currentType !== 'partial');
            showStep('step-input');
        });
    });

    // Retour au choix
    btnBackChoice.addEventListener('click', () => {
        showStep('step-choice');
    });

    // Bouton « Analyser »
    btnParse.addEventListener('click', async () => {
        let raw = '';
        if (currentType === 'single') {
            raw = document.getElementById('ean-single').value.trim();
        } else {
            raw = document.getElementById('ean-textarea').value.trim();
        }
        if (!raw) return;

        btnParse.disabled = true;
        btnParse.textContent = 'Analyse en cours…';

        const category = currentType === 'partial'
            ? document.getElementById('category-input').value.trim() || null
            : null;

        const { ok, data } = await api.parseEan13(raw, currentType, category);

        btnParse.disabled = false;
        btnParse.textContent = 'Analyser';

        if (!ok || !data) {
            alert('Erreur lors de l\'analyse des EAN13.');
            return;
        }
        lastParseResult = data;
        onParsed(data);
    });
}
