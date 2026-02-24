import { fetchJson } from './functions.js';

export async function loadStocks() {
    const sampleStocks = {
        labels: ['Livres Ados', 'Petite enfance', 'Jeunesse', 'Spiritualité', 'Foyer', 'Objets'],
        values: [503, 652, 498, 395, 198, 760],
        value_total: 55300,
        items_total: 3006
    };
    const data = await fetchJson('/dashboard/data/stock') || sampleStocks;
    const ctx = document.getElementById('stocks-donut');
    if (!ctx) return;
    const colors = [
        '#ff6fcf',
        '#2ecc40',
        '#7be3ff',
        '#ff7a7a',
        '#8a6cff',
        '#14a776',
        '#ffb347',
        '#257c25',
        '#2e5481',
        '#fdfd96',
        '#ba2106'
    ];
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
