import { fetchJson } from './functions.js';

export async function loadFinances() {
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
