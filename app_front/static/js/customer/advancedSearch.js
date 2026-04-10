/**
 * Module de recherche avancée pour la page /customer/search.
 * Soumet les critères du formulaire à /customer/data/search/long
 * et affiche les résultats dans un tableau.
 */

import { fetchJson, isPresent } from './functions.js';

const SEARCH_URL = '/customer/data/search/long';

/** Labels lisibles pour le type de client. */
const TYPE_LABELS = { part: 'Particulier', pro: 'Professionnel' };

/**
 * Initialise le formulaire de recherche avancée.
 */
export function setupAdvancedSearch() {
    const form = document.getElementById('advanced-search-form');
    const resultsSection = document.getElementById('search-results-section');
    const resetBtn = document.getElementById('search-reset-btn');

    if (!form || !resultsSection) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await performSearch(form, resultsSection);
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            resultsSection.classList.add('hidden');
        });
    }
}

/**
 * Collecte les critères du formulaire et lance la recherche.
 */
async function performSearch(form, section) {
    const formData = new FormData(form);
    const params = new URLSearchParams();

    for (const [key, value] of formData.entries()) {
        if (value.trim()) {
            params.append(key, value.trim());
        }
    }

    const url = `${SEARCH_URL}?${params.toString()}`;
    const data = await fetchJson(url);

    renderResults(data, section);
}

/**
 * Affiche les résultats dans le tableau.
 */
function renderResults(data, section) {
    const tbody = document.getElementById('search-results-body');
    const noResults = document.getElementById('search-no-results');
    const countEl = document.getElementById('search-results-count');
    const table = document.getElementById('search-results-table');

    section.classList.remove('hidden');

    if (!data || data.length === 0) {
        tbody.innerHTML = '';
        table.classList.add('hidden');
        noResults.classList.remove('hidden');
        countEl.textContent = '';
        return;
    }

    noResults.classList.add('hidden');
    table.classList.remove('hidden');
    countEl.textContent = `${data.length} résultat${data.length > 1 ? 's' : ''}`;

    tbody.innerHTML = data.map(c => `
        <tr class="search-results-row" data-id="${c.id}">
            <td>${escapeHtml(c.display_name)}</td>
            <td>
                <span class="badge badge-${c.customer_type === 'pro' ? 'billing' : 'shipping'}">
                    ${TYPE_LABELS[c.customer_type] || c.customer_type}
                </span>
            </td>
            <td>${escapeHtml(c.location || '—')}</td>
            <td class="email-col">
                <span class="status-dot ${isPresent(c.email) ? 'present' : 'absent'}" title="${escapeHtml(c.email || 'Aucun e-mail')}"></span>
            </td>
            <td class="phone-col">
                <span class="status-dot ${isPresent(c.phone) ? 'present' : 'absent'}" title="${escapeHtml(c.phone || 'Aucun téléphone')}"></span>
            </td>
            <td>
                <span class="badge ${c.is_active ? 'badge-active' : 'badge-inactive'}">
                    ${c.is_active ? 'Actif' : 'Inactif'}
                </span>
            </td>
            <td>
                <a href="/customer/${c.id}" class="btn-add btn-sm">Voir</a>
            </td>
        </tr>
    `).join('');

    // Clic sur une ligne → ouvrir la fiche
    tbody.querySelectorAll('.search-results-row').forEach(row => {
        row.addEventListener('click', (e) => {
            // Ne pas intercepter le clic sur le bouton "Voir"
            if (e.target.closest('a')) return;
            globalThis.location.href = `/customer/${row.dataset.id}`;
        });
    });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
