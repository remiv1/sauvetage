/**
 * Module principal de la page « Conciliation prix zéro ».
 *
 * Workflow par ligne :
 *  1. L'utilisateur saisit un montant dans le champ prix.
 *  2. Il clique sur « Valider ».
 *  3. Un POST est envoyé au serveur.
 *  4. Si la réponse est 200, le champ devient du texte simple
 *     et le bouton disparaît.
 */

import { updatePrice } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    const table = document.getElementById('council-table');
    if (!table) return;

    // Délégation d'événement sur le tableau
    table.addEventListener('click', async (e) => {
        const btn = e.target.closest('.btn-validate');
        if (!btn) return;

        const row        = btn.closest('tr');
        const input      = row.querySelector('.price-input');
        const movementId = Number(row.dataset.movementId);
        const price      = Number.parseFloat(input.value);

        // Validation côté client
        if (Number.isNaN(price) || price < 0) {
            input.focus();
            input.classList.add('is-invalid');
            return;
        }
        input.classList.remove('is-invalid');

        // Désactiver le bouton pendant l'appel
        btn.disabled = true;
        btn.textContent = '…';

        const { ok } = await updatePrice(movementId, price);

        if (ok) {
            // Remplacer le champ par du texte simple
            const cellPrice = row.querySelector('.cell-price');
            cellPrice.textContent = price.toFixed(2);

            // Supprimer le bouton
            const cellAction = row.querySelector('.cell-action');
            cellAction.textContent = '✓';
            cellAction.classList.add('text-success');
        } else {
            btn.disabled = false;
            btn.textContent = 'Valider';
            alert('Erreur lors de la mise à jour du prix.');
        }
    });
});
