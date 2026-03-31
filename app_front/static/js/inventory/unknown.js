/**
 * Gestion de l'étape « Produits inconnus » (étape 3).
 * L'ajout d'un article inconnu utilise le formulaire de création
 * du workflow stock (chargé via HTMX dans #object-modal-container).
 */

import { showStep } from './functions.js';

/** @type {string[]} Liste courante des EAN13 inconnus. */
let unknownList = [];

/** @type {Function|null} Callback lorsque tous les inconnus sont résolus. */
let onAllResolved = null;

/**
 * Initialise la gestion des produits inconnus.
 * @param {Function} onContinue — appelé quand l'utilisateur clique « Continuer ».
 */
export function setupUnknown(onContinue) {
    onAllResolved = onContinue;

    const btnContinue  = document.getElementById('btn-continue');
    const btnBackInput = document.getElementById('btn-back-input');

    btnContinue.addEventListener('click', () => {
        if (onAllResolved) onAllResolved();
    });

    btnBackInput.addEventListener('click', () => {
        showStep('step-input');
    });

    // Délégation d'événement pour le bouton « Ajouter »
    document.getElementById('unknown-table')
        .querySelector('tbody')
        .addEventListener('click', async (ev) => {
            const btn = ev.target.closest('.btn-add-product');
            if (!btn) return;
            await _loadStockForm(btn.dataset.ean);
        });

    // Fermeture de la modale stock (bouton × ou .btn-close-modal)
    document.addEventListener('click', (ev) => {
        if (ev.target.closest('.btn-close-modal')) {
            _closeStockForm();
        }
    });

    // Écouter l'événement déclenché par le serveur après création réussie
    document.body.addEventListener('inventoryObjectCreated', (ev) => {
        const ean13 = ev.detail?.ean13;
        if (ean13) {
            unknownList = unknownList.filter(e => e !== ean13);
            _render();
        }
        _closeStockForm();
    });
}

/**
 * Affiche l'étape « Produits inconnus » avec la liste donnée.
 * @param {string[]} eans
 */
export function showUnknownStep(eans) {
    unknownList = [...eans];
    _render();
    showStep('step-unknown');
}

function _render() {
    const tbody    = document.querySelector('#unknown-table tbody');
    const btnCont  = document.getElementById('btn-continue');
    tbody.innerHTML = '';

    unknownList.forEach(ean => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${ean}</td>
            <td><span class="badge badge-warning">Inconnu</span></td>
            <td><button class="btn btn-sm btn-primary btn-add-product"
                        data-ean="${ean}">Ajouter</button></td>`;
        tbody.appendChild(tr);
    });

    btnCont.disabled = unknownList.length > 0;
}

/**
 * Charge le formulaire de création d'article du stock dans le container
 * #object-modal-container, avec l'EAN pré-rempli.
 * @param {string} ean
 */
async function _loadStockForm(ean) {
    const container = document.getElementById('object-modal-container');
    if (!container) return;
    try {
        const resp = await fetch(
            `/stock/htmx/search/object/form?ean13=${encodeURIComponent(ean)}&from_inventory=1`
        );
        const html = await resp.text();
        container.innerHTML = html;
        // Activer HTMX sur les nouveaux éléments chargés dynamiquement
        if (window.htmx) {
            htmx.process(container);
        }
    } catch (err) {
        console.error('Erreur chargement formulaire article :', err);
    }
}

/**
 * Vide le container de la modale de création d'article.
 */
function _closeStockForm() {
    const container = document.getElementById('object-modal-container');
    if (container) {
        container.innerHTML = '';
    }
}
