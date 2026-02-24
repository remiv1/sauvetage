/**
 * Module de gestion des téléphones client.
 * Charge, ajoute et supprime les téléphones via l'API customer/data.
 */

import { fetchJson, postJson, deleteJson, showNotification, serializeForm } from './functions.js';

/**
 * Initialise la section Téléphones : chargement, formulaire d'ajout, suppression.
 */
export function setupPhones() {
    loadPhones();
    setupPhoneForm();
}

/**
 * Charge et affiche la liste des téléphones du client.
 */
async function loadPhones() {
    const customerId = globalThis.CUSTOMER_ID;
    const container = document.getElementById('phones-list');
    if (!container) return;

    const phones = await fetchJson(`/customer/data/${customerId}/phones`);
    if (!phones || phones.length === 0) {
        container.innerHTML = '<p class="empty-text">Aucun téléphone enregistré.</p>';
        return;
    }

    container.innerHTML = '';
    phones.forEach(phone => {
        const card = createPhoneCard(phone);
        container.appendChild(card);
    });
}

/**
 * Crée un élément DOM pour une carte téléphone.
 * @param {object} phone - Les données du téléphone.
 * @returns {HTMLElement}
 */
function createPhoneCard(phone) {
    const card = document.createElement('div');
    card.className = 'item-card';
    card.dataset.id = phone.id;

    const statusClass = phone.is_active ? 'badge-active' : 'badge-inactive';
    const statusText = phone.is_active ? 'Actif' : 'Inactif';

    card.innerHTML = `
        <div class="item-card__header">
            <strong class="item-card__title">${phone.phone_name || 'Téléphone'}</strong>
            <span class="badge ${statusClass}">${statusText}</span>
        </div>
        <div class="item-card__body">
            <p><a href="tel:${phone.phone_number.replaceAll(/\s/g, '')}">${phone.phone_number}</a></p>
        </div>
        <div class="item-card__actions">
            <button class="btn btn-delete btn-sm" data-delete-phone="${phone.id}">Supprimer</button>
        </div>
    `;

    card.querySelector('[data-delete-phone]').addEventListener('click', async () => {
        if (!confirm(`Supprimer le téléphone "${phone.phone_number}" ?`)) return;
        const result = await deleteJson(`/customer/data/${globalThis.CUSTOMER_ID}/phone/${phone.id}`);
        if (result.ok) {
            card.remove();
            showNotification('Téléphone supprimé.', 'success');
            const list = document.getElementById('phones-list');
            if (list?.children.length === 0) {
                list.innerHTML = '<p class="empty-text">Aucun téléphone enregistré.</p>';
            }
        } else {
            showNotification('Erreur lors de la suppression.', 'danger');
        }
    });

    return card;
}

/**
 * Configure le formulaire d'ajout de téléphone.
 */
function setupPhoneForm() {
    const btnAdd = document.getElementById('btn-add-phone');
    const btnCancel = document.getElementById('btn-cancel-phone');
    const formContainer = document.getElementById('phone-form-container');
    const form = document.getElementById('phone-form');

    if (btnAdd && formContainer) {
        btnAdd.addEventListener('click', () => {
            formContainer.classList.toggle('hidden');
            btnAdd.textContent = formContainer.classList.contains('hidden')
                ? '+ Ajouter un téléphone' : '− Fermer';
        });
    }

    if (btnCancel && formContainer && btnAdd) {
        btnCancel.addEventListener('click', () => {
            formContainer.classList.add('hidden');
            btnAdd.textContent = '+ Ajouter un téléphone';
            if (form) form.reset();
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = serializeForm(form);

            // Validation basique du numéro
            const cleaned = (data.phone_number || '').replaceAll(/[\s\-.]/g, '');
            if (cleaned.length < 8) {
                showNotification('Numéro de téléphone trop court.', 'warning');
                return;
            }

            const result = await postJson(`/customer/data/${globalThis.CUSTOMER_ID}/phone`, data);

            if (result.ok && result.data) {
                const list = document.getElementById('phones-list');
                const emptyText = list?.querySelector('.empty-text');
                if (emptyText) emptyText.remove();

                if (list) list.appendChild(createPhoneCard(result.data));
                showNotification('Téléphone ajouté avec succès.', 'success');
                form.reset();
                formContainer?.classList.add('hidden');
                if (btnAdd) btnAdd.textContent = '+ Ajouter un téléphone';
            } else {
                showNotification('Erreur lors de l\'ajout du téléphone.', 'danger');
            }
        });
    }
}
