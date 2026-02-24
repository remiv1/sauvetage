/**
 * Point d'entrée JS pour la page de visualisation client (fiche client).
 * Importe et initialise les sous-modules : onglets, adresses, emails, téléphones.
 */

import { setupAddresses } from './addresses.js';
import { setupEmails } from './emails.js';
import { setupPhones } from './phones.js';
import { postJson, showNotification } from './functions.js';

/**
 * Configure la navigation par onglets.
 */
function setupTabs() {
    const tabs = document.querySelectorAll('.customer-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const target = tab.dataset.target;
            document.querySelectorAll('.customer-panel').forEach(p => p.classList.add('hidden'));
            const panel = document.getElementById(target);
            if (panel) panel.classList.remove('hidden');
        });
    });
}

/**
 * Configure le bouton d'activation / désactivation du client.
 */
function setupToggleStatus() {
    const btn = document.getElementById('btn-toggle-status');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const isActive = btn.dataset.active === 'true';
        const action = isActive ? 'deactivate' : 'activate';
        const label = isActive ? 'désactiver' : 'activer';

        if (!confirm(`Voulez-vous ${label} ce client ?`)) return;

        const result = await postJson(
            `/customer/data/${window.CUSTOMER_ID}/${action}`,
            {}
        );

        if (result.ok && result.data) {
            const newActive = result.data.is_active;
            btn.dataset.active = newActive.toString();
            btn.textContent = newActive ? 'Désactiver' : 'Activer';

            // Met à jour le badge de statut
            const badge = document.querySelector('.status-badge');
            if (badge) {
                badge.className = `status-badge ${newActive ? 'status-active' : 'status-inactive'}`;
                badge.textContent = newActive ? 'Actif' : 'Inactif';
            }

            showNotification(
                newActive ? 'Client activé.' : 'Client désactivé.',
                'success'
            );
        } else {
            showNotification('Erreur lors du changement de statut.', 'danger');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupToggleStatus();
    setupAddresses();
    setupEmails();
    setupPhones();
});
