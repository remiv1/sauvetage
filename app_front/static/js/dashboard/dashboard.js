import { loadOrders } from './orders.js';
import { loadStocks } from './stocks.js';
import { loadFinances } from './finances.js';

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

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    loadOrders();
    loadStocks();
    loadFinances();
});
