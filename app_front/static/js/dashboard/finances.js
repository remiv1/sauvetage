import { fetchJson } from './functions.js';

export async function loadFinances() {
    const response = await fetchJson('/dashboard/data/finances');
    const data = response && typeof response === 'object'
        ? response
        : { months: [], charges: [], ressources: [] };
    const ctx = document.getElementById('finances-bar');
    if (!ctx) return;
    new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: { labels: data.months, datasets: [{ label: 'Charges', data: data.charges, backgroundColor: '#ff4d4f' }, { label: 'Ressources', data: data.ressources, backgroundColor: '#16a085' }] },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
}
