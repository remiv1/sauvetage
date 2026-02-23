// Tabs functionality
function setupTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(t => t.addEventListener('click', () => {
        tabs.forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        const target = t.dataset.target;
        document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
        const panel = document.getElementById(target);
        if (panel) panel.classList.remove('hidden');
    }));
}

// Data fetching with fallback sample data
async function fetchJson(url) {
    try {
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) throw new Error('Network error');
        return await res.json();
    } catch (e) {
        console.warn('Fetch failed for', url, e);
        return null;
    }
}

async function loadOrders() {
    const sampleOrders = [
        { name: 'M Rémi Verschuur', date: '01/01/2026', amount: 1253, availability: 'Disponible', status: 'En cours' },
        { name: 'M Christian de la Pellequirole', date: '03/01/2026', amount: 126.32, availability: 'Disponible', status: 'Annulée' }
    ];
    const data = await fetchJson('/dashboard/data/commandes') || sampleOrders;
    const wrap = document.getElementById('orders-table');
    if (!wrap) return;
    const table = document.createElement('table');
    table.className = 'dashboard-table';
    table.innerHTML = `<thead><tr><th>Nom du client</th><th>Date commande</th><th>Montant</th><th>Disponibilité</th><th>Status</th></tr></thead>`;
    const tbody = document.createElement('tbody');
    data.forEach(o => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${o.name}</td><td>${o.date}</td><td style="font-weight:700">${formatCurrency(o.amount)}</td><td>${o.availability || ''}</td><td>${o.status || ''}</td>`;
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.innerHTML = '';
    wrap.appendChild(table);
}

function formatCurrency(n) {
    if (typeof n !== 'number') return n;
    return n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
}

async function loadStocks() {
    const sampleStocks = {
        labels: ['Livres Ados', 'Petite enfance', 'Jeunesse', 'Spiritualité', 'Foyer', 'Objets'],
        values: [503, 652, 498, 395, 198, 760],
        value_total: 55300,
        items_total: 3006
    };
    const data = await fetchJson('/dashboard/data/stock') || sampleStocks;
    const ctx = document.getElementById('stocks-donut');
    if (!ctx) return;
    const colors = ['#ff6fcf', '#2ecc40', '#7be3ff', '#ff7a7a', '#8a6cff', '#5fe0b4'];
    new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: { labels: data.labels, datasets: [{ data: data.values, backgroundColor: colors }] },
        options: { plugins: { legend: { display: false } } }
    });
    const legend = document.getElementById('stocks-legend');
    legend.innerHTML = '';
    data.labels.forEach((lab, i) => {
        const row = document.createElement('div');
        row.className = 'legend-row';
        row.innerHTML = `<span class="dot" style="background:${colors[i % colors.length]}"></span> ${lab} <strong style="float:right">${data.values[i]}</strong>`;
        legend.appendChild(row);
    });
    document.getElementById('kpi-total').textContent = data.items_total || data.values.reduce((a, b) => a + b, 0);
    document.getElementById('kpi-value').textContent = (data.value_total ? (data.value_total / 1000).toFixed(1) + ' k€' : '—');
    document.getElementById('kpi-cat').textContent = data.labels.length;
}

async function loadFinances() {
    const sampleFinances = {
        months: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'],
        charges: [30, 35, 38, 42, 39, 45, 40, 36, 44, 48, 46, 50],
        ressources: [45, 52, 48, 61, 55, 67, 58, 49, 62, 72, 66, 76]
    };
    const data = await fetchJson('/dashboard/data/finances') || sampleFinances;
    const ctx = document.getElementById('finances-bar');
    if (!ctx) return;
    new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: { labels: data.months, datasets: [{ label: 'Charges', data: data.charges, backgroundColor: '#ff4d4f' }, { label: 'Ressources', data: data.ressources, backgroundColor: '#16a085' }] },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    loadOrders();
    loadStocks();
    loadFinances();
});
