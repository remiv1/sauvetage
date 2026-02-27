/**
 * Gestion de l'étape « Conciliation » (étape 5)
 * et validation (étape 6).
 */

import { showStep, MOTIFS } from './functions.js';
import * as api from './api.js';

/** @type {Array} Lignes de conciliation courantes. */
let reconcileRows = [];

/**
 * Initialise la conciliation.
 * @param {Function} onValidated — callback(planned) après validation réussie.
 */
export function setupReconcile(onValidated) {
    const btnValidate   = document.getElementById('btn-validate');
    const btnBackUnknown = document.getElementById('btn-back-unknown');

    btnBackUnknown.addEventListener('click', () => {
        showStep('step-unknown');
    });

    // Écouter les modifications du stock réel (content-editable)
    document.querySelector('#reconcile-table tbody')
        .addEventListener('input', _onStockRealEdit);

    btnValidate.addEventListener('click', async () => {
        btnValidate.disabled = true;
        btnValidate.textContent = 'Validation…';

        const lines = _collectLines();
        const { ok, data } = await api.validateInventory(lines);

        btnValidate.disabled = false;
        btnValidate.textContent = 'Valider les écarts';

        if (!ok || !data) {
            alert('Erreur lors de la validation.');
            return;
        }
        onValidated(data.planned || []);
    });
}

/**
 * Charge et affiche la conciliation pour les EAN13 donnés.
 * @param {string[]} ean13List
 */
export async function showReconcileStep(ean13List) {
    const { ok, data } = await api.prepareInventory(ean13List);
    if (!ok || !data) {
        alert('Erreur lors de la préparation de la conciliation.');
        return;
    }
    reconcileRows = Array.isArray(data) ? data : [];
    _render();
    showStep('step-reconcile');
}

// ----- Rendu ------------------------------------------------------------- //

function _render() {
    const tbody = document.querySelector('#reconcile-table tbody');
    tbody.innerHTML = '';

    reconcileRows.forEach((row, idx) => {
        const tr = document.createElement('tr');
        tr.dataset.idx = idx;
        const diffClass = row.difference === 0 ? '' : 'cell-diff';

        // Cases à cocher pour les motifs
        const motifsHtml = MOTIFS.map(m =>
            `<label class="motif-label">
                <input type="checkbox" name="motif-${idx}" value="${m}" /> ${m}
             </label>`
        ).join('');
        tr.innerHTML = `
            <td>${row.ean13}</td>
            <td>${row.title}</td>
            <td class="text-center">${row.stock_theorique}</td>
            <td class="text-center stock-reel" contenteditable="true">${row.stock_reel}</td>
            <td class="text-center ${diffClass}" data-diff>${row.difference}</td>
            <td class="motifs-cell">${motifsHtml}</td>
            <td><input type="text" class="form-control form-control-sm commentaire-input"
                       placeholder="Commentaire…" /></td>`;
        tbody.appendChild(tr);
    });
}

// ----- Édition du stock réel --------------------------------------------- //

function _onStockRealEdit(ev) {
    const td = ev.target.closest('.stock-reel');
    if (!td) return;
    const tr    = td.closest('tr');
    const idx   = Number.parseInt(tr.dataset.idx, 10);
    const newVal = Number.parseInt(td.textContent, 10) || 0;
    const thVal  = reconcileRows[idx].stock_theorique;
    const diff   = newVal - thVal;

    reconcileRows[idx].stock_reel = newVal;
    reconcileRows[idx].difference = diff;

    const diffTd = tr.querySelector('[data-diff]');
    diffTd.textContent = diff;
    diffTd.classList.toggle('cell-diff', diff !== 0);
}

// ----- Collecte des lignes pour validation ------------------------------- //

function _collectLines() {
    const rows = document.querySelectorAll('#reconcile-table tbody tr');
    return Array.from(rows).map((tr, idx) => {
        const row    = reconcileRows[idx];
        const motifs = Array.from(tr.querySelectorAll(`input[name="motif-${idx}"]:checked`))
                            .map(cb => cb.value);
        const commentaire = tr.querySelector('.commentaire-input')?.value || '';
        return {
            ean13:            row.ean13,
            stock_theorique:  row.stock_theorique,
            stock_reel:       Number.parseInt(tr.querySelector('.stock-reel').textContent, 10) || 0,
            motifs,
            commentaire,
        };
    });
}
