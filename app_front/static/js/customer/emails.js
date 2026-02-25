/**
 * Module de gestion des emails client.
 * Charge, ajoute, modifie et désactive (soft-delete) les emails.
 * Affiche les éléments actifs et inactifs dans des sections séparées.
 */

import { fetchJson, patchJson, postJson, serializeForm, showNotification } from './functions.js';

/* ── Icônes SVG (inline, 16×16) ──────────────────────────────────────────── */
const ICON = {
    edit: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>`,
    deactivate: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>`,
    restore: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>`,
    save: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>`,
    cancel: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
};

/**
 * Initialise la section Emails.
 */
export function setupEmails() {
    loadEmails();
    setupEmailForm();
}

// ── Chargement ──────────────────────────────────────────────────────────────
async function loadEmails() {
    const customerId = globalThis.CUSTOMER_ID;
    const container = document.getElementById('emails-list');
    if (!container) return;

    const emails = await fetchJson(`/customer/data/${customerId}/emails`);
    if (!emails || emails.length === 0) {
        container.innerHTML = '<p class="empty-text">Aucun email enregistré.</p>';
        return;
    }

    renderEmailList(emails, container);
}

function renderEmailList(emails, container) {
    container.innerHTML = '';

    const active = emails.filter(e => e.is_active !== false);
    const inactive = emails.filter(e => e.is_active === false);

    if (active.length === 0 && inactive.length === 0) {
        container.innerHTML = '<p class="empty-text">Aucun email enregistré.</p>';
        return;
    }

    if (active.length > 0) {
        active.forEach(em => container.appendChild(createEmailCard(em)));
    } else {
        container.innerHTML = '<p class="empty-text">Aucun email actif.</p>';
    }

    if (inactive.length > 0) {
        const section = document.createElement('div');
        section.className = 'inactive-section';
        section.innerHTML = `
            <button class="inactive-section__toggle" type="button">
                Emails supprimés (${inactive.length})
            </button>
            <div class="inactive-section__list hidden"></div>
        `;
        const toggle = section.querySelector('.inactive-section__toggle');
        const list = section.querySelector('.inactive-section__list');
        toggle.addEventListener('click', () => {
            list.classList.toggle('hidden');
            toggle.classList.toggle('open');
        });
        inactive.forEach(em => list.appendChild(createEmailCard(em)));
        container.appendChild(section);
    }
}

// ── Carte email ─────────────────────────────────────────────────────────────
function createEmailCard(email) {
    const isActive = email.is_active !== false;
    const card = document.createElement('div');
    card.className = `item-card${isActive ? '' : ' item-card--inactive'}`;
    card.dataset.id = email.id;

    card.innerHTML = `
        <div class="item-card__header">
            <strong class="item-card__title">${email.email_name || 'Email'}</strong>
        </div>
        <div class="item-card__body">
            <p><a href="mailto:${email.email}">${email.email}</a></p>
        </div>
        <div class="item-card__actions">
            ${isActive ? `
                <button class="icon-btn icon-btn--edit" title="Modifier" data-action="edit">
                    ${ICON.edit}
                </button>
                <button class="icon-btn icon-btn--deactivate" title="Supprimer" data-action="deactivate">
                    ${ICON.deactivate}
                </button>
            ` : `
                <button class="icon-btn icon-btn--restore" title="Réactiver" data-action="restore">
                    ${ICON.restore}
                </button>
            `}
        </div>
    `;

    card.querySelector('[data-action="edit"]')?.addEventListener('click', () => enterEditMode(card, email));

    card.querySelector('[data-action="deactivate"]')?.addEventListener('click', async () => {
        if (!confirm(`Supprimer l'email « ${email.email} » ?`)) return;
        const result = await patchJson(
            `/customer/data/${globalThis.CUSTOMER_ID}/email/${email.id}`,
            { is_active: false }
        );
        if (result.ok) {
            email.is_active = false;
            showNotification('Email supprimé.', 'success');
            await loadEmails();
        } else {
            showNotification('Erreur lors de la suppression.', 'danger');
        }
    });

    card.querySelector('[data-action="restore"]')?.addEventListener('click', async () => {
        const result = await patchJson(
            `/customer/data/${globalThis.CUSTOMER_ID}/email/${email.id}`,
            { is_active: true }
        );
        if (result.ok) {
            email.is_active = true;
            showNotification('Email réactivé.', 'success');
            await loadEmails();
        } else {
            showNotification('Erreur lors de la réactivation.', 'danger');
        }
    });

    return card;
}

// ── Mode édition inline ─────────────────────────────────────────────────────
function enterEditMode(card, email) {
    card.classList.add('item-card--editing');
    card.innerHTML = `
        <form class="item-edit-form">
            <div class="form-row two-cols">
                <div class="form-group mb-2">
                    <label class="form-label">Nom</label>
                    <input type="text" name="email_name" class="form-control"
                           value="${escapeAttr(email.email_name)}" required>
                </div>
                <div class="form-group mb-2">
                    <label class="form-label">Adresse email</label>
                    <input type="email" name="email" class="form-control"
                           value="${escapeAttr(email.email)}" required>
                </div>
            </div>
            <div class="item-card__actions">
                <button type="submit" class="icon-btn icon-btn--save" title="Enregistrer">
                    ${ICON.save}
                </button>
                <button type="button" class="icon-btn icon-btn--cancel" title="Annuler" data-action="cancel">
                    ${ICON.cancel}
                </button>
            </div>
        </form>
    `;

    const form = card.querySelector('.item-edit-form');

    form.querySelector('[data-action="cancel"]').addEventListener('click', () => {
        const newCard = createEmailCard(email);
        card.replaceWith(newCard);
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = serializeForm(form);

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(data.email || '')) {
            showNotification('Adresse email invalide.', 'warning');
            return;
        }

        data.is_active = true;
        const result = await patchJson(
            `/customer/data/${globalThis.CUSTOMER_ID}/email/${email.id}`,
            data
        );
        if (result.ok && result.data) {
            showNotification('Email mis à jour.', 'success');
            Object.assign(email, result.data);
            const newCard = createEmailCard(result.data);
            card.replaceWith(newCard);
        } else {
            showNotification('Erreur lors de la mise à jour.', 'danger');
        }
    });
}

// ── Formulaire d'ajout ──────────────────────────────────────────────────────
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

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(data.email || '')) {
                showNotification('Adresse email invalide.', 'warning');
                return;
            }

            const result = await postJson(`/customer/data/${globalThis.CUSTOMER_ID}/email`, data);

            if (result.ok && result.data) {
                showNotification('Email ajouté avec succès.', 'success');
                form.reset();
                formContainer?.classList.add('hidden');
                if (btnAdd) btnAdd.textContent = '+ Ajouter un email';
                await loadEmails();
            } else {
                showNotification("Erreur lors de l'ajout de l'email.", 'danger');
            }
        });
    }
}

// ── Utilitaires ─────────────────────────────────────────────────────────────
function escapeAttr(str) {
    return (str || '').replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
}
