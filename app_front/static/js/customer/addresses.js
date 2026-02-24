/**
 * Module de gestion des adresses client.
 * Charge, ajoute et supprime les adresses via l'API customer/data.
 */

import { fetchJson, postJson, deleteJson, showNotification, serializeForm } from './functions.js';

/**
 * Initialise la section Adresses : chargement, formulaire d'ajout, suppression.
 */
export function setupAddresses() {
    loadAddresses();
    setupAddressForm();
}

/**
 * Charge et affiche la liste des adresses du client.
 */
async function loadAddresses() {
    const customerId = globalThis.CUSTOMER_ID;
    const container = document.getElementById('addresses-list');
    if (!container) return;

    const addresses = await fetchJson(`/customer/data/${customerId}/addresses`);
    if (!addresses || addresses.length === 0) {
        container.innerHTML = '<p class="empty-text">Aucune adresse enregistrée.</p>';
        return;
    }

    container.innerHTML = '';
    addresses.forEach(addr => {
        const card = createAddressCard(addr);
        container.appendChild(card);
    });
}

/**
 * Crée un élément DOM pour une carte d'adresse.
 * @param {object} addr - Les données de l'adresse.
 * @returns {HTMLElement}
 */
function createAddressCard(addr) {
    const card = document.createElement('div');
    card.className = 'item-card';
    card.dataset.id = addr.id;

    const line2 = addr.address_line2 ? `<br>${addr.address_line2}` : '';
    const badges = [];
    if (addr.is_billing) badges.push('<span class="badge badge-billing">Facturation</span>');
    if (addr.is_shipping) badges.push('<span class="badge badge-shipping">Livraison</span>');

    card.innerHTML = `
        <div class="item-card__header">
            <strong class="item-card__title">${addr.address_name || 'Adresse'}</strong>
            <div class="item-card__badges">${badges.join(' ')}</div>
        </div>
        <div class="item-card__body">
            <p>${addr.address_line1}${line2}</p>
            <p>${addr.postal_code} ${addr.city}, ${addr.state}</p>
            <p>${addr.country}</p>
        </div>
        <div class="item-card__actions">
            <button class="btn btn-delete btn-sm" data-delete-address="${addr.id}">Supprimer</button>
        </div>
    `;

    // Bouton supprimer
    card.querySelector('[data-delete-address]').addEventListener('click', async () => {
        if (!confirm(`Supprimer l'adresse "${addr.address_name}" ?`)) return;
        const result = await deleteJson(`/customer/data/${globalThis.CUSTOMER_ID}/address/${addr.id}`);
        if (result.ok) {
            card.remove();
            showNotification('Adresse supprimée.', 'success');
            // Vérifier si la liste est vide
            const list = document.getElementById('addresses-list');
            if (list?.children.length === 0) {
                list.innerHTML = '<p class="empty-text">Aucune adresse enregistrée.</p>';
            }
        } else {
            showNotification('Erreur lors de la suppression.', 'danger');
        }
    });

    return card;
}

/**
 * Configure le formulaire d'ajout d'adresse (affichage/masquage + soumission).
 */
function setupAddressForm() {
    const btnAdd = document.getElementById('btn-add-address');
    const btnCancel = document.getElementById('btn-cancel-address');
    const formContainer = document.getElementById('address-form-container');
    const form = document.getElementById('address-form');

    if (btnAdd && formContainer) {
        btnAdd.addEventListener('click', () => {
            formContainer.classList.toggle('hidden');
            btnAdd.textContent = formContainer.classList.contains('hidden')
                ? '+ Ajouter une adresse' : '− Fermer';
        });
    }

    if (btnCancel && formContainer && btnAdd) {
        btnCancel.addEventListener('click', () => {
            formContainer.classList.add('hidden');
            btnAdd.textContent = '+ Ajouter une adresse';
            if (form) form.reset();
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = serializeForm(form);
            const result = await postJson(`/customer/data/${globalThis.CUSTOMER_ID}/address`, data);

            if (result.ok && result.data) {
                const list = document.getElementById('addresses-list');
                // Retirer le message "aucune adresse" s'il existe
                const emptyText = list?.querySelector('.empty-text');
                if (emptyText) emptyText.remove();

                if (list) list.appendChild(createAddressCard(result.data));
                showNotification('Adresse ajoutée avec succès.', 'success');
                form.reset();
                formContainer?.classList.add('hidden');
                if (btnAdd) btnAdd.textContent = '+ Ajouter une adresse';
            } else {
                showNotification('Erreur lors de l\'ajout de l\'adresse.', 'danger');
            }
        });
    }
}
