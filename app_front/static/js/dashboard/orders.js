import { formatCurrency, createClassName, fetchJson } from "./functions.js";

export async function loadOrders() {
    const sampleOrders = [
        { name: 'M Rémi Verschuur', date: '01/01/2026', amount: 1253, availability: 'Disponible', status: 'En cours' },
        { name: 'M Christian de la Pellequirole', date: '03/01/2026', amount: 126.32, availability: 'Disponible', status: 'Annulée' }
    ];
    const data = await fetchJson('/dashboard/data/commandes') || sampleOrders;
    const wrap = document.getElementById('orders-table');
    if (!wrap) return;
    const table = document.createElement('table');
    table.className = 'dashboard-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Nom du client</th>
                <th>Date commande</th>
                <th>Montant</th>
                <th>Disponibilité</th>
                <th>Status</th>
            </tr>
        </thead>
    `;
    const tbody = document.createElement('tbody');
    const nbOrders = data.length;
    data.forEach(o => {
        const orderAvailability = o.availability || '';
        const orderStatus = o.status || '';
        const orderAvailabilityClass = createClassName('availability', orderAvailability);
        const orderStatusClass = createClassName('status', orderStatus);
        const tr = document.createElement('tr');
        tr.className = 'order';
        tr.innerHTML = `
            <td class="order-name">${o.name}</td>
            <td class="order-date">${o.date}</td>
            <td class="order-amount">${formatCurrency(o.amount)}</td>
            <td class="order-availability">
                <span class="${orderAvailabilityClass}">
                    ${orderAvailability}
                </span>
            </td>
            <td class="order-status">
                <span class="${orderStatusClass}">
                    ${orderStatus}
                </span>
            </td>
        `;
        tbody.appendChild(tr);
    });
    const tfoot = document.createElement('tfoot');
    tfoot.innerHTML = `
        <tr>
            <td class="orders-total">
                Nb: ${nbOrders}
            </td>
            <td class="orders-total" style="text-align: right;">TOTAL :</td>
            <td class="orders-total" style="text-align: right;">
                ${formatCurrency(data.reduce((total, o) => total + o.amount, 0))}
            </td>
            <td class="orders-total" colspan="2"></td>
        </tr>
    `;
    table.appendChild(tfoot);
    table.appendChild(tbody);
    wrap.innerHTML = '';
    wrap.appendChild(table);
}
