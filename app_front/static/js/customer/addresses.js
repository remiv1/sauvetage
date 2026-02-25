/**
 * Module de gestion des adresses client.
 * Charge, ajoute, modifie et désactive (soft-delete) les adresses.
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
 * Initialise la section Adresses.
 */
export function setupAddresses() {
    loadAddresses();
    setupAddressForm();
}

// ── Chargement ──────────────────────────────────────────────────────────────
async function loadAddresses() {
    const customerId = globalThis.CUSTOMER_ID;
    const container = document.getElementById('addresses-list');
    if (!container) return;

    const addresses = await fetchJson(`/customer/data/${customerId}/addresses`);
    if (!addresses || addresses.length === 0) {
        container.innerHTML = '<p class="empty-text">Aucune adresse enregistrée.</p>';
        return;
    }

    renderAddressList(addresses, container);
}

function renderAddressList(addresses, container) {
    container.innerHTML = '';

    const active = addresses.filter(a => a.is_active !== false);
    const inactive = addresses.filter(a => a.is_active === false);

    if (active.length === 0 && inactive.length === 0) {
        container.innerHTML = '<p class="empty-text">Aucune adresse enregistrée.</p>';
        return;
    }

    if (active.length > 0) {
        active.forEach(addr => container.appendChild(createAddressCard(addr)));
    } else {
        container.innerHTML = '<p class="empty-text">Aucune adresse active.</p>';
    }

    if (inactive.length > 0) {
        const section = document.createElement('div');
        section.className = 'inactive-section';
        section.innerHTML = `
            <button class="inactive-section__toggle" type="button">
                Adresses supprimées (${inactive.length})
            </button>
            <div class="inactive-section__list hidden"></div>
        `;
        const toggle = section.querySelector('.inactive-section__toggle');
        const list = section.querySelector('.inactive-section__list');
        toggle.addEventListener('click', () => {
            list.classList.toggle('hidden');
            toggle.classList.toggle('open');
        });
        inactive.forEach(addr => list.appendChild(createAddressCard(addr)));
        container.appendChild(section);
    }
}

// ── Carte d'adresse ─────────────────────────────────────────────────────────
function createAddressCard(addr) {
    const isActive = addr.is_active !== false;
    const card = document.createElement('div');
    card.className = `item-card${isActive ? '' : ' item-card--inactive'}`;
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

    // Actions
    card.querySelector('[data-action="edit"]')?.addEventListener('click', () => enterEditMode(card, addr));

    card.querySelector('[data-action="deactivate"]')?.addEventListener('click', async () => {
        if (!confirm(`Supprimer l'adresse « ${addr.address_name} » ?`)) return;
        const result = await patchJson(
            `/customer/data/${globalThis.CUSTOMER_ID}/address/${addr.id}`,
            { is_active: false }
        );
        if (result.ok) {
            addr.is_active = false;
            showNotification('Adresse supprimée.', 'success');
            await loadAddresses();
        } else {
            showNotification('Erreur lors de la suppression.', 'danger');
        }
    });

    card.querySelector('[data-action="restore"]')?.addEventListener('click', async () => {
        const result = await patchJson(
            `/customer/data/${globalThis.CUSTOMER_ID}/address/${addr.id}`,
            { is_active: true }
        );
        if (result.ok) {
            addr.is_active = true;
            showNotification('Adresse réactivée.', 'success');
            await loadAddresses();
        } else {
            showNotification('Erreur lors de la réactivation.', 'danger');
        }
    });

    return card;
}

// ── Mode édition inline ─────────────────────────────────────────────────────
function enterEditMode(card, addr) {
    card.classList.add('item-card--editing');
    card.innerHTML = `
        <form class="item-edit-form">
            <div class="form-group mb-2">
                <label class="form-label">Nom de l'adresse</label>
                <input type="text" name="address_name" class="form-control"
                       value="${escapeAttr(addr.address_name)}" required>
            </div>
            <div class="form-group mb-2">
                <label class="form-label">Adresse</label>
                <input type="text" name="address_line1" class="form-control"
                       value="${escapeAttr(addr.address_line1)}" required>
            </div>
            <div class="form-group mb-2">
                <label class="form-label">Complément</label>
                <input type="text" name="address_line2" class="form-control"
                       value="${escapeAttr(addr.address_line2 || '')}">
            </div>
            <div class="form-row three-cols">
                <div class="form-group mb-2">
                    <label class="form-label">Ville</label>
                    <input type="text" name="city" class="form-control"
                           value="${escapeAttr(addr.city)}" required>
                </div>
                <div class="form-group mb-2">
                    <label class="form-label">Code postal</label>
                    <input type="text" name="postal_code" class="form-control"
                           value="${escapeAttr(addr.postal_code)}" required>
                </div>
                <div class="form-group mb-2">
                    <label class="form-label">Région</label>
                    <input type="text" name="state" class="form-control"
                           value="${escapeAttr(addr.state)}" required>
                </div>
            </div>
            <div class="form-group mb-2">
                <label class="form-label">Pays</label>
                <input type="text" name="country" class="form-control"
                       value="${escapeAttr(addr.country)}" required>
            </div>
            <div class="form-row two-cols">
                <div class="form-group mb-2">
                    <label class="toggle-label">
                        <input type="checkbox" name="is_billing" ${addr.is_billing ? 'checked' : ''}>
                        Adresse de facturation
                    </label>
                </div>
                <div class="form-group mb-2">
                    <label class="toggle-label">
                        <input type="checkbox" name="is_shipping" ${addr.is_shipping ? 'checked' : ''}>
                        Adresse de livraison
                    </label>
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
        const newCard = createAddressCard(addr);
        card.replaceWith(newCard);
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = serializeForm(form);
        data.is_billing = form.querySelector('[name="is_billing"]').checked;
        data.is_shipping = form.querySelector('[name="is_shipping"]').checked;
        data.is_active = true;

        const result = await patchJson(
            `/customer/data/${globalThis.CUSTOMER_ID}/address/${addr.id}`,
            data
        );
        if (result.ok && result.data) {
            showNotification('Adresse mise à jour.', 'success');
            Object.assign(addr, result.data);
            const newCard = createAddressCard(result.data);
            card.replaceWith(newCard);
        } else {
            showNotification('Erreur lors de la mise à jour.', 'danger');
        }
    });
}

// ── Formulaire d'ajout ──────────────────────────────────────────────────────
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
            data.is_billing = form.querySelector('[name="is_billing"]')?.checked || false;
            data.is_shipping = form.querySelector('[name="is_shipping"]')?.checked || false;

            const result = await postJson(`/customer/data/${globalThis.CUSTOMER_ID}/address`, data);

            if (result.ok && result.data) {
                showNotification('Adresse ajoutée avec succès.', 'success');
                form.reset();
                formContainer?.classList.add('hidden');
                if (btnAdd) btnAdd.textContent = '+ Ajouter une adresse';
                await loadAddresses();
            } else {
                showNotification("Erreur lors de l'ajout de l'adresse.", 'danger');
            }
        });
    }
}

// ── Utilitaires ─────────────────────────────────────────────────────────────
function escapeAttr(str) {
    return (str || '').replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
}
