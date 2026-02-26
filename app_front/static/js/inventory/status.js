/**
 * Gestion de l'étape « Statut de la tâche » (étape 8) — commit + polling.
 */

import { showStep } from './functions.js';
import * as api from './api.js';

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
 * Lance le commit puis démarre le polling.
 * @param {Array} planned — mouvements planifiés.
 */
export async function startCommit(planned) {
    showStep('step-status');
    _setStatusUI('running', 0, 'Lancement du commit…');

    const { ok } = await api.commitInventory(planned);
    if (!ok) {
        _setStatusUI('error', 0, 'Impossible de lancer le commit.');
        return;
    }
    _startPolling();
}

// ----- Polling ----------------------------------------------------------- //

function _startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(_poll, POLL_INTERVAL);
}

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

    if (data.status === 'error') {
        clearInterval(pollTimer);
        pollTimer = null;
        _setStatusUI('error', 0, data.message || 'Erreur lors de la mise à jour');
        return;
    }

    _setStatusUI('running', data.progress || 0, data.message || 'Mise à jour du stock en cours…');
}

// ----- UI ---------------------------------------------------------------- //

function _setStatusUI(status, progress, message) {
    const spinner    = document.getElementById('status-spinner');
    const text       = document.getElementById('status-text');
    const container  = document.getElementById('progress-container');
    const bar        = document.getElementById('progress-bar');
    const btnNew     = document.getElementById('btn-new-inventory');

    text.textContent = message;
    bar.style.width  = `${progress}%`;

    if (status === 'running') {
        spinner.classList.remove('hidden');
        container.classList.remove('hidden');
        btnNew.classList.add('hidden');
    } else if (status === 'success') {
        spinner.classList.add('hidden');
        container.classList.add('hidden');
        btnNew.classList.remove('hidden');
        text.classList.add('status-success');
        text.classList.remove('status-error');
        setTimeout(() => {
            text.textContent = 'Stock à jour, veuillez patienter...';
        }, 3000);
    } else if (status === 'error') {
        spinner.classList.add('hidden');
        container.classList.add('hidden');
        btnNew.classList.remove('hidden');
        text.classList.add('status-error');
        text.classList.remove('status-success');
        setTimeout(() => {
            text.textContent = 'Une erreur est survenue lors de la mise à jour du stock.';
        }, 3000);
    }
}
