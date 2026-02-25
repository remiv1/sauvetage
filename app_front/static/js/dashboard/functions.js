// Fonction utilitaire pour créer des classes CSS à partir de valeurs dynamiques
export function createClassName(prefixe, value) {
    return prefixe + '-' + value
                            .normalize('NFD')
                            .replaceAll(/[\u0300-\u036f]/g, '')
                            .toLowerCase()
                            .replaceAll(/\s+/g, '-');
}

// Data fetching with fallback sample data
export async function fetchJson(url) {
    try {
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) throw new Error('Network error');
        return await res.json();
    } catch (e) {
        console.warn('Fetch failed for', url, e);
        return null;
    }
}

export function formatCurrency(n) {
    if (typeof n !== 'number') return n;
    return n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
}
