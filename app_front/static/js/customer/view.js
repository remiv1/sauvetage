/**
 * Point d'entrée JS pour la page de visualisation client (fiche client).
 * Importe et initialise les sous-modules : onglets, adresses, emails, téléphones.
 */

import { setupAddresses } from './addresses.js';
import { setupEmails } from './emails.js';
import { setupPhones } from './phones.js';
import { postJson, patchJson, showNotification, serializeForm } from './functions.js';

/**
 * Mapping des civilités pour l'affichage.
 */
const CIVIL_TITLES = { m: 'M.', mme: 'Mme', mlle: 'Mlle', ab: 'Abbé', sr: 'Sr', dr: 'Dr' };

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
 * Met à jour l'affichage de la carte info après une modification réussie.
 */
function refreshInfoDisplay(data) {
    const display = document.getElementById('info-display');
    if (!display) return;

    // Mise à jour du titre
    const title = display.querySelector('.customer-container__title');
    if (title) {
        if (data.customer_type === 'part' && data.part) {
            const ct = data.part.civil_title || '';
            const cap = ct.charAt(0).toUpperCase() + ct.slice(1);
            title.textContent = `${cap} ${data.part.first_name} ${data.part.last_name}`;
        } else if (data.customer_type === 'pro' && data.pro) {
            title.textContent = data.pro.company_name;
        }
    }

    // Mise à jour du détail
    const detailRow = display.querySelector('.customer-detail-row');
    if (detailRow && data.customer_type === 'part' && data.part) {
        const ct = data.part.civil_title || '—';
        const capCt = ct.charAt(0).toUpperCase() + ct.slice(1);
        const dob = data.part.date_of_birth ? data.part.date_of_birth.substring(0, 10) : '—';
        detailRow.innerHTML =
            `<span><strong>Civilité :</strong> ${capCt}</span>` +
            `<span><strong>Prénom :</strong> ${data.part.first_name}</span>` +
            `<span><strong>Nom :</strong> ${data.part.last_name}</span>` +
            `<span><strong>Date de naissance :</strong> ${dob}</span>`;
    } else if (detailRow && data.customer_type === 'pro' && data.pro) {
        detailRow.innerHTML =
            `<span><strong>Raison sociale :</strong> ${data.pro.company_name}</span>` +
            `<span><strong>SIRET :</strong> ${data.pro.siret_number || '—'}</span>` +
            `<span><strong>TVA :</strong> ${data.pro.vat_number || '—'}</span>`;
    }

    // Mise à jour de la date de modification
    const metaItems = display.querySelectorAll('.meta-item');
    if (metaItems.length >= 3 && data.updated_at) {
        metaItems[2].innerHTML = `<strong>Mis à jour le :</strong> ${data.updated_at.substring(0, 10)}`;
    }
}

/**
 * Configure l'édition inline des informations client.
 */
function setupInfoEdit() {
    const btnEdit = document.getElementById('btn-edit-info');
    const btnSave = document.getElementById('btn-save-info');
    const btnCancel = document.getElementById('btn-cancel-info');
    const infoDisplay = document.getElementById('info-display');
    const infoEdit = document.getElementById('info-edit');
    const editForm = document.getElementById('info-edit-form');

    if (!btnEdit || !infoDisplay || !infoEdit || !editForm) return;

    // Ouvrir l'édition
    btnEdit.addEventListener('click', () => {
        infoDisplay.classList.add('hidden');
        infoEdit.classList.remove('hidden');
    });

    // Annuler l'édition
    btnCancel.addEventListener('click', () => {
        infoEdit.classList.add('hidden');
        infoDisplay.classList.remove('hidden');
    });

    // Sauvegarder
    btnSave.addEventListener('click', async () => {
        const data = serializeForm(editForm);

        // Validation côté client
        if (globalThis.CUSTOMER_TYPE === 'part') {
            if (!data.first_name?.trim() || !data.last_name?.trim()) {
                showNotification('Le prénom et le nom sont obligatoires.', 'danger');
                return;
            }
        } else if (globalThis.CUSTOMER_TYPE === 'pro') {
            if (!data.company_name?.trim()) {
                showNotification('La raison sociale est obligatoire.', 'danger');
                return;
            }
        }

        const result = await patchJson(
            `/customer/data/${globalThis.CUSTOMER_ID}/info`,
            data
        );

        if (result.ok && result.data) {
            refreshInfoDisplay(result.data);

            // Mettre à jour les champs du formulaire avec les nouvelles valeurs
            if (result.data.customer_type === 'part' && result.data.part) {
                const p = result.data.part;
                const selCivil = editForm.querySelector('[name="civil_title"]');
                if (selCivil) selCivil.value = p.civil_title || 'm';
                const inpFirst = editForm.querySelector('[name="first_name"]');
                if (inpFirst) inpFirst.value = p.first_name || '';
                const inpLast = editForm.querySelector('[name="last_name"]');
                if (inpLast) inpLast.value = p.last_name || '';
                const inpDob = editForm.querySelector('[name="date_of_birth"]');
                if (inpDob) inpDob.value = p.date_of_birth ? p.date_of_birth.substring(0, 10) : '';
            } else if (result.data.customer_type === 'pro' && result.data.pro) {
                const pr = result.data.pro;
                const inpComp = editForm.querySelector('[name="company_name"]');
                if (inpComp) inpComp.value = pr.company_name || '';
                const inpSiret = editForm.querySelector('[name="siret_number"]');
                if (inpSiret) inpSiret.value = pr.siret_number || '';
                const inpVat = editForm.querySelector('[name="vat_number"]');
                if (inpVat) inpVat.value = pr.vat_number || '';
            }

            infoEdit.classList.add('hidden');
            infoDisplay.classList.remove('hidden');
            showNotification('Informations mises à jour avec succès.', 'success');
        } else {
            const msg = result.data?.error || 'Erreur lors de la mise à jour.';
            showNotification(msg, 'danger');
        }
    });
}

/**
 * Met à jour l'UI après le changement de statut.
 */
function updateStatusUI(btn, newActive) {
    btn.dataset.active = newActive.toString();
    btn.textContent = newActive ? 'Désactiver' : 'Activer';

    const badge = document.querySelector('.status-badge');
    if (badge) {
        badge.className = `status-badge ${newActive ? 'status-active' : 'status-inactive'}`;
        badge.textContent = newActive ? 'Actif' : 'Inactif';
    }

    const message = newActive ? 'Client activé.' : 'Client désactivé.';
    showNotification(message, 'success');
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
            `/customer/data/${globalThis.CUSTOMER_ID}/${action}`,
            {}
        );

        if (result.ok && result.data) {
            updateStatusUI(btn, result.data.is_active);
        } else {
            showNotification('Erreur lors du changement de statut.', 'danger');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupInfoEdit();
    setupToggleStatus();
    setupAddresses();
    setupEmails();
    setupPhones();
});
