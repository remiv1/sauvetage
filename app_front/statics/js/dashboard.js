/**
 * dashboard.js – Tableau de bord moderne (Éditions Sauvetage)
 * Gestion des onglets et chargement des données par fetch.
 */

'use strict';

/* ── Constantes ──────────────────────────────────────────── */
const API_BASE = '/dashboard/api';

const TABS = ['general', 'stocks', 'commandes', 'clients', 'fournisseurs'];

/* ── État ────────────────────────────────────────────────── */
const loaded = new Set();

/* ── Utilitaires DOM ─────────────────────────────────────── */
const el = (id) => document.getElementById(id);

function html(strings, ...values) {
    return strings.reduce((acc, str, i) => acc + str + (i < values.length ? escHtml(values[i]) : ''), '');
}

function escHtml(v) {
    return String(v)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/* ── Spinner de chargement ───────────────────────────────── */
function loadingHTML() {
    return `<div class="db-loading"><div class="db-spinner"></div><p>Chargement…</p></div>`;
}

function errorHTML(msg) {
    return `<div class="db-error">⚠️ ${escHtml(msg)}</div>`;
}

/* ── Badge de statut ─────────────────────────────────────── */
function badge(statut) {
    const map = {
        'OK': 'ok', 'Actif': 'actif',
        'Livrée': 'livree', 'En cours': 'en-cours',
        'Annulée': 'annulee', 'Inactif': 'inactif',
        'Faible': 'faible', 'Critique': 'critique',
    };
    const cls = map[statut] || 'ok';
    return `<span class="db-badge db-badge--${escHtml(cls)}">${escHtml(statut)}</span>`;
}

/* ── Tendance (flèche) ───────────────────────────────────── */
function trend(val, up) {
    const dir = up ? 'up' : 'down';
    const arrow = up ? '▲' : '▼';
    return `<span class="db-kpi__trend db-kpi__trend--${dir}">${arrow} ${escHtml(val)}</span>`;
}

/* ── Rendu des KPI ───────────────────────────────────────── */
function renderKpis(kpis) {
    const cards = kpis.map((k) => `
        <div class="db-kpi">
            <span class="db-kpi__accent"></span>
            <span class="db-kpi__label">${escHtml(k.label)}</span>
            <span class="db-kpi__value">${escHtml(k.value)}</span>
            ${trend(k.trend, k.up)}
        </div>`).join('');
    return `<div class="db-kpis">${cards}</div>`;
}

/* ── Rendu : Vue générale ────────────────────────────────── */
function renderGeneral(data) {
    const rows = data.recent.map((r) => `
        <tr>
            <td>${escHtml(r.date)}</td>
            <td>${escHtml(r.type)}</td>
            <td><code>${escHtml(r.ref)}</code></td>
            <td>${escHtml(r.montant)}</td>
            <td>${badge(r.statut)}</td>
        </tr>`).join('');

    return renderKpis(data.kpis) + `
        <div class="db-section">
            <div class="db-section__header">
                <h2 class="db-section__title">Activité récente</h2>
                <span class="db-section__count">${data.recent.length} entrées</span>
            </div>
            <div class="db-table-wrap">
                <table class="db-table">
                    <thead><tr>
                        <th>Date</th><th>Type</th><th>Référence</th>
                        <th>Montant</th><th>Statut</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
}

/* ── Rendu : Stocks ──────────────────────────────────────── */
function renderStocks(data) {
    const rows = data.items.map((i) => `
        <tr>
            <td><code>${escHtml(i.ref)}</code></td>
            <td>${escHtml(i.titre)}</td>
            <td>${escHtml(String(i.stock))}</td>
            <td>${escHtml(String(i.min_stock))}</td>
            <td>${badge(i.statut)}</td>
        </tr>`).join('');

    return renderKpis(data.kpis) + `
        <div class="db-section">
            <div class="db-section__header">
                <h2 class="db-section__title">Articles à surveiller</h2>
                <span class="db-section__count">${data.items.length} articles</span>
            </div>
            <div class="db-table-wrap">
                <table class="db-table">
                    <thead><tr>
                        <th>Référence</th><th>Titre</th><th>En stock</th>
                        <th>Stock min.</th><th>Statut</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
}

/* ── Rendu : Commandes ───────────────────────────────────── */
function renderCommandes(data) {
    const rows = data.commandes.map((c) => `
        <tr>
            <td><code>${escHtml(c.ref)}</code></td>
            <td>${escHtml(c.client)}</td>
            <td>${escHtml(c.date)}</td>
            <td>${escHtml(c.total)}</td>
            <td>${badge(c.statut)}</td>
        </tr>`).join('');

    return renderKpis(data.kpis) + `
        <div class="db-section">
            <div class="db-section__header">
                <h2 class="db-section__title">Commandes récentes</h2>
                <span class="db-section__count">${data.commandes.length} commandes</span>
            </div>
            <div class="db-table-wrap">
                <table class="db-table">
                    <thead><tr>
                        <th>Référence</th><th>Client</th><th>Date</th>
                        <th>Total</th><th>Statut</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
}

/* ── Rendu : Clients ─────────────────────────────────────── */
function renderClients(data) {
    const rows = data.clients.map((c) => `
        <tr>
            <td>${escHtml(c.nom)}</td>
            <td>${escHtml(c.ville)}</td>
            <td>${escHtml(String(c.commandes))}</td>
            <td>${escHtml(c.ca)}</td>
            <td>${badge(c.statut)}</td>
        </tr>`).join('');

    return renderKpis(data.kpis) + `
        <div class="db-section">
            <div class="db-section__header">
                <h2 class="db-section__title">Principaux clients</h2>
                <span class="db-section__count">${data.clients.length} clients</span>
            </div>
            <div class="db-table-wrap">
                <table class="db-table">
                    <thead><tr>
                        <th>Nom</th><th>Ville</th><th>Commandes</th>
                        <th>CA</th><th>Statut</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
}

/* ── Rendu : Fournisseurs ────────────────────────────────── */
function renderFournisseurs(data) {
    const rows = data.fournisseurs.map((f) => `
        <tr>
            <td>${escHtml(f.nom)}</td>
            <td>${escHtml(f.pays)}</td>
            <td>${escHtml(String(f.commandes))}</td>
            <td>${escHtml(f.delai)}</td>
            <td>${badge(f.statut)}</td>
        </tr>`).join('');

    return renderKpis(data.kpis) + `
        <div class="db-section">
            <div class="db-section__header">
                <h2 class="db-section__title">Fournisseurs</h2>
                <span class="db-section__count">${data.fournisseurs.length} fournisseurs</span>
            </div>
            <div class="db-table-wrap">
                <table class="db-table">
                    <thead><tr>
                        <th>Nom</th><th>Pays</th><th>Cmd. en cours</th>
                        <th>Délai moy.</th><th>Statut</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
}

/* ── Carte de rendu par onglet ───────────────────────────── */
const RENDERERS = {
    general:      renderGeneral,
    stocks:       renderStocks,
    commandes:    renderCommandes,
    clients:      renderClients,
    fournisseurs: renderFournisseurs,
};

/* ── Chargement des données ──────────────────────────────── */
async function loadPanel(tab) {
    if (loaded.has(tab)) return;

    const panel = el(`panel-${tab}`);
    panel.innerHTML = loadingHTML();

    try {
        const resp = await fetch(`${API_BASE}/${tab}`);
        if (!resp.ok) throw new Error(`Erreur HTTP ${resp.status}`);
        const data = await resp.json();
        panel.innerHTML = RENDERERS[tab](data);
        loaded.add(tab);
    } catch (err) {
        panel.innerHTML = errorHTML(`Impossible de charger les données : ${err.message}`);
    }
}

/* ── Gestion des onglets ─────────────────────────────────── */
function activateTab(tab) {
    TABS.forEach((t) => {
        const btn = el(`tab-${t}`);
        const pnl = el(`panel-${t}`);
        const active = t === tab;

        btn.classList.toggle('active', active);
        btn.setAttribute('aria-selected', String(active));

        if (active) {
            pnl.classList.remove('db-panel--hidden');
        } else {
            pnl.classList.add('db-panel--hidden');
        }
    });

    loadPanel(tab);
}

/* ── Rafraîchissement ────────────────────────────────────── */
function refreshCurrent() {
    const activeTab = TABS.find((t) => el(`tab-${t}`).classList.contains('active'));
    if (!activeTab) return;

    const btn = el('db-refresh');
    btn.classList.add('spinning');
    btn.disabled = true;

    loaded.delete(activeTab);
    loadPanel(activeTab).finally(() => {
        btn.classList.remove('spinning');
        btn.disabled = false;
    });
}

/* ── Date courante ───────────────────────────────────────── */
function updateDate() {
    const dateEl = el('db-date');
    if (!dateEl) return;
    const now = new Date();
    dateEl.textContent = now.toLocaleDateString('fr-FR', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    });
}

/* ── Initialisation ──────────────────────────────────────── */
function init() {
    updateDate();

    /* Écouteurs sur les onglets */
    TABS.forEach((tab) => {
        const btn = el(`tab-${tab}`);
        if (btn) {
            btn.addEventListener('click', () => activateTab(tab));
        }
    });

    /* Bouton rafraîchir */
    const refreshBtn = el('db-refresh');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshCurrent);
    }

    /* Chargement initial du premier onglet */
    loadPanel('general');
}

document.addEventListener('DOMContentLoaded', init);
