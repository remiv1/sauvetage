/**
 * Module de recherche rapide (autocomplete) pour la page d'accueil client.
 * Effectue un fetch vers /customer/data/search/fast?q=... et affiche
 * les résultats dans une dropdown sous le champ de saisie.
 */

import { fetchJson } from './functions.js';

const FAST_SEARCH_URL = '/customer/data/search/fast';
const MIN_CHARS = 2;
const DEBOUNCE_MS = 300;

/** Labels lisibles pour le type de client. */
const TYPE_LABELS = { part: 'Particulier', pro: 'Professionnel' };

let debounceTimer = null;

/**
 * Initialise la recherche rapide sur la page d'accueil.
 */
export function setupFastSearch() {
    const input = document.getElementById('fast-search-input');
    const dropdown = document.getElementById('fast-search-results');
    if (!input || !dropdown) return;

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const q = input.value.trim();

        if (q.length < MIN_CHARS) {
            hideDropdown(dropdown);
            return;
        }

        debounceTimer = setTimeout(() => performSearch(q, dropdown), DEBOUNCE_MS);
    });

    // Fermer la dropdown au clic extérieur
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.fast-search-wrapper')) {
            hideDropdown(dropdown);
        }
    });

    // Navigation clavier dans la dropdown
    input.addEventListener('keydown', (e) => {
        handleKeyboard(e, dropdown);
    });
}

/**
 * Lance la requête de recherche et affiche les résultats.
 */
async function performSearch(query, dropdown) {
    const data = await fetchJson(`${FAST_SEARCH_URL}?q=${encodeURIComponent(query)}`);

    if (!data || data.length === 0) {
        dropdown.innerHTML = '<li class="fast-search-empty">Aucun résultat</li>';
        showDropdown(dropdown);
        return;
    }

    dropdown.innerHTML = data.map(c => `
        <li class="fast-search-item" data-id="${c.id}">
            <div class="fast-search-item__name">${escapeHtml(c.display_name)}</div>
            <div class="fast-search-item__meta">
                <span class="fast-search-item__location">${escapeHtml(c.location)}</span>
                <span class="badge badge-${c.customer_type === 'pro' ? 'billing' : 'shipping'}">
                    ${TYPE_LABELS[c.customer_type] || c.customer_type}
                </span>
            </div>
        </li>
    `).join('');

    // Clic sur un résultat → ouvrir la fiche
    dropdown.querySelectorAll('.fast-search-item').forEach(item => {
        item.addEventListener('click', () => {
            globalThis.location.href = `/customer/${item.dataset.id}`;
        });
    });

    showDropdown(dropdown);
}

/**
 * Gère la navigation clavier (flèches haut/bas, Entrée, Échap).
 */
function handleKeyboard(e, dropdown) {
    const items = dropdown.querySelectorAll('.fast-search-item');
    if (!items.length) return;

    const current = dropdown.querySelector('.fast-search-item--active');
    let idx = Array.from(items).indexOf(current);

    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            idx = idx < items.length - 1 ? idx + 1 : 0;
            setActive(items, idx);
            break;
        case 'ArrowUp':
            e.preventDefault();
            idx = idx > 0 ? idx - 1 : items.length - 1;
            setActive(items, idx);
            break;
        case 'Enter':
            e.preventDefault();
            if (current) current.click();
            break;
        case 'Escape':
            hideDropdown(dropdown);
            break;
    }
}

function setActive(items, idx) {
    items.forEach(i => i.classList.remove('fast-search-item--active'));
    items[idx]?.classList.add('fast-search-item--active');
    items[idx]?.scrollIntoView({ block: 'nearest' });
}

function showDropdown(el) { el.classList.remove('hidden'); }
function hideDropdown(el) { el.classList.add('hidden'); }

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
