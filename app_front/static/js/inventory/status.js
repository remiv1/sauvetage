/**
 * Gestion de l'étape « Statut de la tâche » (étape 8) — commit + polling.
 */

import * as api from './api.js';
import { showStep } from './functions.js';
import { getType } from './input.js';

const POLL_INTERVAL = 3000; // ms

/** @type {number|null} */
let pollTimer = null;

/**
 * Initialise le bouton « Nouvel inventaire ».
 */
export function setupStatus() {
    document.getElementById('btn-new-inventory').addEventListener('click', () => {
        globalThis.location.reload();
    });
}

/**
 * Initialise le bouton « Accueil ».
 */
export function returnHome() {
    document.getElementById('btn-home').addEventListener('click', () => {
        globalThis.location.href = '/';
    });
}

/**
 * Lance le commit puis démarre le polling.
 * @param {Array} planned — mouvements planifiés.
 */
export async function startCommit(planned) {
    showStep('step-status');
    _setStatusUI('running', 0, 'Lancement du commit…');

    const inventoryType = getType();
    console.debug('Starting commit with planned movements:', planned, 'inventory_type:', inventoryType);

    const { ok } = await api.commitInventory(planned, inventoryType);
    if (!ok) {
        _setStatusUI('error', 0, 'Impossible de lancer le commit.');
        return;
    }
    _startPolling();
}

// ----- Polling ----------------------------------------------------------- //

/**
 * Démarre le polling pour vérifier l'état de la tâche de commit.
 */
function _startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(_poll, POLL_INTERVAL);
}

/**
 * Effectue le polling pour vérifier l'état de la tâche.
 * @returns {Promise<void>}
 */
async function _poll() {
    const data = await api.getInventoryStatus();
    if (!data) return;

    // Tâche terminée (fichier supprimé)
    if (data.running === false && !data.status) {
        clearInterval(pollTimer);
        pollTimer = null;
        _setStatusUI('success', 100, 'Stock à jour');
        return;
    }

    // Erreur signalée par le backend
    if (data.status === 'error') {
        clearInterval(pollTimer);
        pollTimer = null;
        _setStatusUI('error', 0, data.message || 'Erreur lors de la mise à jour');
        return;
    }

    _setStatusUI('running', data.progress || 0, data.message || 'Mise à jour du stock en cours…');
}

// ----- UI ---------------------------------------------------------------- //

/**
 * Met à jour l'affichage du statut de la tâche.
 * @param {string} status - Le statut actuel ('running', 'success', 'error').
 * @param {number} progress - Le pourcentage de progression (0-100).
 * @param {string} message - Le message à afficher.
 */
function _setStatusUI(status, progress, message) {
    const spinner    = document.getElementById('status-spinner');
    const text       = document.getElementById('status-text');
    const container  = document.getElementById('progress-container');
    const bar        = document.getElementById('progress-bar');
    const btnNew     = document.getElementById('btn-new-inventory');
    const btnHome    = document.getElementById('btn-home');

    text.textContent = message;
    bar.style.width  = `${progress}%`;

    if (status === 'running') {
        spinner.classList.remove('hidden');
        container.classList.remove('hidden');
        btnNew.classList.add('hidden');
        btnHome.classList.add('hidden');
    } else if (status === 'success') {
        spinner.classList.add('hidden');
        container.classList.add('hidden');
        btnNew.classList.remove('hidden');
        btnHome.classList.remove('hidden');
        text.classList.add('status-success');
        text.classList.remove('status-error');
        setTimeout(() => {
            text.textContent = 'Stock à jour, veuillez patienter...';
        }, 5000);
        globalThis.location.replace('/');
    } else if (status === 'error') {
        spinner.classList.add('hidden');
        container.classList.add('hidden');
        btnNew.classList.remove('hidden');
        btnHome.classList.remove('hidden');
        text.classList.add('status-error');
        text.classList.remove('status-success');
        setTimeout(() => {
            text.textContent = 'Une erreur est survenue lors de la mise à jour du stock.';
        }, 3000);
    }
}
