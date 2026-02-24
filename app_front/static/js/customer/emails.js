/**
 * Module de gestion des emails client.
 * Charge, ajoute et supprime les emails via l'API customer/data.
 */

import { fetchJson, postJson, deleteJson, showNotification, serializeForm } from './functions.js';

/**
 * Initialise la section Emails : chargement, formulaire d'ajout, suppression.
 */
export function setupEmails() {
    loadEmails();
    setupEmailForm();
}

/**
 * Charge et affiche la liste des emails du client.
 */
async function loadEmails() {
    const customerId = globalThis.CUSTOMER_ID;
    const container = document.getElementById('emails-list');
    if (!container) return;

    const emails = await fetchJson(`/customer/data/${customerId}/emails`);
    if (!emails || emails.length === 0) {
        container.innerHTML = '<p class="empty-text">Aucun email enregistré.</p>';
        return;
    }

    container.innerHTML = '';
    emails.forEach(email => {
        const card = createEmailCard(email);
        container.appendChild(card);
    });
}

/**
 * Crée un élément DOM pour une carte email.
 * @param {object} email - Les données de l'email.
 * @returns {HTMLElement}
 */
function createEmailCard(email) {
    const card = document.createElement('div');
    card.className = 'item-card';
    card.dataset.id = email.id;

    const statusClass = email.is_active ? 'badge-active' : 'badge-inactive';
    const statusText = email.is_active ? 'Actif' : 'Inactif';

    card.innerHTML = `
        <div class="item-card__header">
            <strong class="item-card__title">${email.email_name || 'Email'}</strong>
            <span class="badge ${statusClass}">${statusText}</span>
        </div>
        <div class="item-card__body">
            <p><a href="mailto:${email.email}">${email.email}</a></p>
        </div>
        <div class="item-card__actions">
            <button class="btn btn-delete btn-sm" data-delete-email="${email.id}">Supprimer</button>
        </div>
    `;

    card.querySelector('[data-delete-email]').addEventListener('click', async () => {
        if (!confirm(`Supprimer l'email "${email.email}" ?`)) return;
        const result = await deleteJson(`/customer/data/${globalThis.CUSTOMER_ID}/email/${email.id}`);
        if (result.ok) {
            card.remove();
            showNotification('Email supprimé.', 'success');
            const list = document.getElementById('emails-list');
            if (list?.children.length === 0) {
                list.innerHTML = '<p class="empty-text">Aucun email enregistré.</p>';
            }
        } else {
            showNotification('Erreur lors de la suppression.', 'danger');
        }
    });

    return card;
}

/**
 * Configure le formulaire d'ajout d'email.
 */
function setupEmailForm() {
    const btnAdd = document.getElementById('btn-add-email');
    const btnCancel = document.getElementById('btn-cancel-email');
    const formContainer = document.getElementById('email-form-container');
    const form = document.getElementById('email-form');

    if (btnAdd && formContainer) {
        btnAdd.addEventListener('click', () => {
            formContainer.classList.toggle('hidden');
            btnAdd.textContent = formContainer.classList.contains('hidden')
                ? '+ Ajouter un email' : '− Fermer';
        });
    }

    if (btnCancel && formContainer && btnAdd) {
        btnCancel.addEventListener('click', () => {
            formContainer.classList.add('hidden');
            btnAdd.textContent = '+ Ajouter un email';
            if (form) form.reset();
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = serializeForm(form);

            // Validation basique de l'email
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(data.email || '')) {
                showNotification('Adresse email invalide.', 'warning');
                return;
            }

            const result = await postJson(`/customer/data/${globalThis.CUSTOMER_ID}/email`, data);

            if (result.ok && result.data) {
                const list = document.getElementById('emails-list');
                const emptyText = list?.querySelector('.empty-text');
                if (emptyText) emptyText.remove();

                if (list) list.appendChild(createEmailCard(result.data));
                showNotification('Email ajouté avec succès.', 'success');
                form.reset();
                formContainer?.classList.add('hidden');
                if (btnAdd) btnAdd.textContent = '+ Ajouter un email';
            } else {
                showNotification('Erreur lors de l\'ajout de l\'email.', 'danger');
            }
        });
    }
}
