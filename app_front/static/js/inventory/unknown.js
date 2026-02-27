/**
 * Gestion de l'étape « Produits inconnus » (étape 3) et modale d'ajout (étape 4).
 */

import { showStep } from './functions.js';
import * as api from './api.js';

/** @type {string[]} Liste courante des EAN13 inconnus. */
let unknownList = [];

/** @type {Function|null} Callback lorsque tous les inconnus sont résolus. */
let onAllResolved = null;

/**
 * Initialise la gestion des produits inconnus.
 * @param {Function} onContinue — appelé quand l'utilisateur clique « Continuer ».
 */
export function setupUnknown(onContinue) {
    onAllResolved = onContinue;

    const btnContinue  = document.getElementById('btn-continue');
    const btnBackInput = document.getElementById('btn-back-input');

    btnContinue.addEventListener('click', () => {
        if (onAllResolved) onAllResolved();
    });

    btnBackInput.addEventListener('click', () => {
        showStep('step-input');
    });

    // Délégation d'événement pour le bouton « Ajouter »
    document.getElementById('unknown-table')
        .querySelector('tbody')
        .addEventListener('click', (ev) => {
            const btn = ev.target.closest('.btn-add-product');
            if (!btn) return;
            _openModal(btn.dataset.ean);
        });

    // Modale : annuler
    document.getElementById('btn-modal-cancel').addEventListener('click', _closeModal);
    document.getElementById('product-modal').addEventListener('click', (ev) => {
        if (ev.target === ev.currentTarget) _closeModal();
    });

    // Modale : changement du type de produit → afficher/masquer les champs livre
    document.getElementById('modal-product-type').addEventListener('change', _toggleBookFields);

    // Modale : autocomplete fournisseur
    _setupSupplierAutocomplete();

    // Modale : autocomplete champs produit
    _setupFieldAutocomplete('modal-author',   'author-suggestions',   'author');
    _setupFieldAutocomplete('modal-diffuser',  'diffuser-suggestions',  'diffuser');
    _setupFieldAutocomplete('modal-editor',   'editor-suggestions',   'editor');
    _setupFieldAutocomplete('modal-genre',    'genre-suggestions',    'genre');

    // Modale : soumission du formulaire
    document.getElementById('product-form').addEventListener('submit', async (ev) => {
        ev.preventDefault();
        await _submitProduct();
    });
}

/**
 * Affiche l'étape « Produits inconnus » avec la liste donnée.
 * @param {string[]} eans
 */
export function showUnknownStep(eans) {
    unknownList = [...eans];
    _render();
    showStep('step-unknown');
}

// ----- Rendu du tableau -------------------------------------------------- //

function _render() {
    const tbody    = document.querySelector('#unknown-table tbody');
    const btnCont  = document.getElementById('btn-continue');
    tbody.innerHTML = '';

    unknownList.forEach(ean => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${ean}</td>
            <td><span class="badge badge-warning">Inconnu</span></td>
            <td><button class="btn btn-sm btn-primary btn-add-product"
                        data-ean="${ean}">Ajouter</button></td>`;
        tbody.appendChild(tr);
    });

    btnCont.disabled = unknownList.length > 0;
}

// ----- Modale ------------------------------------------------------------ //

/**
 * Affiche/masque les champs spécifiques « Livre » selon le type sélectionné.
 */
function _toggleBookFields() {
    const isBook = document.getElementById('modal-product-type').value === 'book';
    document.querySelectorAll('.book-field').forEach(el => {
        el.classList.toggle('hidden', !isBook);
    });
}

// ----- Autocomplete champs produit (author, diffuser, editor, genre) ------- //

/** Timers de debounce par champ. */
const _fieldDebounces = {};

/**
 * Branche un autocomplete générique sur un champ texte.
 * @param {string} inputId       - id de l'input
 * @param {string} suggestionsId - id de la ul de suggestions
 * @param {string} fieldName     - clé de recherche dans l'API (ex: 'author')
 */
function _setupFieldAutocomplete(inputId, suggestionsId, fieldName) {
    const input       = document.getElementById(inputId);
    const suggestions = document.getElementById(suggestionsId);
    if (!input || !suggestions) return;

    // Saisie → recherche avec debounce
    input.addEventListener('input', () => {
        clearTimeout(_fieldDebounces[fieldName]);
        const q = input.value.trim();
        if (q.length < 2) {
            suggestions.classList.add('hidden');
            return;
        }
        _fieldDebounces[fieldName] = setTimeout(async () => {
            const results = await api.searchObjectsInfo(fieldName, q);
            _renderFieldSuggestions(suggestions, results);
        }, 250);
    });

    // Clic sur une suggestion → remplir l'input
    suggestions.addEventListener('click', (ev) => {
        const li = ev.target.closest('li');
        if (!li) return;
        input.value = li.textContent;
        suggestions.classList.add('hidden');
    });

    // Fermer la liste si clic en dehors
    const wrapper = input.closest('.autocomplete-wrapper');
    document.addEventListener('click', (ev) => {
        if (wrapper && !wrapper.contains(ev.target)) {
            suggestions.classList.add('hidden');
        }
    });

    // Fermer avec Escape
    input.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape') suggestions.classList.add('hidden');
    });
}

function _renderFieldSuggestions(listEl, results) {
    listEl.innerHTML = '';
    if (!results || results.length === 0) {
        listEl.classList.add('hidden');
        return;
    }
    results.forEach(value => {
        const li = document.createElement('li');
        li.textContent = value;
        li.className = 'autocomplete-item';
        listEl.appendChild(li);
    });
    listEl.classList.remove('hidden');
}

// ----- Autocomplete fournisseur ------------------------------------------ //

/** @type {number} Timer de debounce pour la recherche fournisseur. */
let _supplierDebounce = 0;

/** @type {number|null} ID du fournisseur sélectionné. */
let _selectedSupplierId = null;

function _setupSupplierAutocomplete() {
    const input              = document.getElementById('modal-supplier-name');
    const suggestions        = document.getElementById('supplier-suggestions');
    const createZone         = document.getElementById('supplier-create-zone');
    const btnCreate          = document.getElementById('btn-create-supplier');
    const btnClear           = document.getElementById('btn-clear-supplier');
    const formWrapper        = document.getElementById('supplier-form-wrapper');
    const btnFormSubmit      = document.getElementById('btn-supplier-form-submit');
    const btnFormCancel      = document.getElementById('btn-supplier-form-cancel');
    const supplierFormName   = document.getElementById('supplier-form-name');

    // Saisie → recherche avec debounce
    input.addEventListener('input', () => {
        clearTimeout(_supplierDebounce);
        const q = input.value.trim();
        if (q.length < 2) {
            suggestions.classList.add('hidden');
            createZone.classList.add('hidden');
            return;
        }
        _supplierDebounce = setTimeout(async () => {
            const results = await api.searchSuppliers(q);
            _renderSuggestions(results, q);
        }, 250);
    });

    // Clic sur une suggestion
    suggestions.addEventListener('click', (ev) => {
        const li = ev.target.closest('li');
        if (!li) return;
        _selectSupplier(Number(li.dataset.id), li.textContent);
    });

    // Créer un nouveau fournisseur → Afficher le formulaire complet
    btnCreate.addEventListener('click', () => {
        const name = input.value.trim();
        if (!name) return;
        supplierFormName.value = name;
        formWrapper.classList.remove('hidden');
        document.getElementById('supplier-form-name').focus();
    });

    // Soumettre le formulaire de création de fournisseur
    btnFormSubmit.addEventListener('click', async (ev) => {
        ev.preventDefault();
        const name = (document.getElementById('supplier-form-name').value || '').trim();
        if (!name) {
            alert('Le nom du fournisseur est requis.');
            return;
        }
        const data = {
            name,
            gln13: (document.getElementById('supplier-form-gln13').value || '').trim() || "",
            contact_email: (document.getElementById('supplier-form-email').value || '').trim() || "",
            contact_phone: (document.getElementById('supplier-form-phone').value || '').trim() || "",
        };
        try {
            const response = await fetch('/inventory/data/suppliers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                alert(`Erreur : ${errorData.error || 'Impossible de créer le fournisseur.'}`);
                return;
            }
            const result = await response.json();
            _selectSupplier(result.id, result.name);
            _hideSupplierForm();
        } catch (err) {
            console.error('Erreur création fournisseur:', err);
            alert('Erreur de connexion.');
        }
    });

    // Annuler le formulaire
    btnFormCancel.addEventListener('click', () => {
        _hideSupplierForm();
    });

    // Effacer la sélection
    btnClear.addEventListener('click', () => {
        _clearSupplier();
        input.focus();
    });

    // Fermer la liste si clic en dehors
    document.addEventListener('click', (ev) => {
        if (!ev.target.closest('#group-supplier')) {
            suggestions.classList.add('hidden');
            createZone.classList.add('hidden');
        }
    });
}

function _hideSupplierForm() {
    const formWrapper = document.getElementById('supplier-form-wrapper');
    formWrapper.classList.add('hidden');
    // Réinitialiser les champs
    document.getElementById('supplier-form-name').value = '';
    document.getElementById('supplier-form-gln13').value = '';
    document.getElementById('supplier-form-email').value = '';
    document.getElementById('supplier-form-phone').value = '';
}

function _renderSuggestions(results, query) {
    const suggestions = document.getElementById('supplier-suggestions');
    const createZone  = document.getElementById('supplier-create-zone');
    const createName  = document.getElementById('supplier-create-name');
    suggestions.innerHTML = '';

    if (results && results.length > 0) {
        results.forEach(s => {
            const li = document.createElement('li');
            li.textContent = s.name;
            li.dataset.id = s.id;
            li.className = 'autocomplete-item';
            suggestions.appendChild(li);
        });
        suggestions.classList.remove('hidden');
        createZone.classList.add('hidden');
    } else {
        suggestions.classList.add('hidden');
        createName.textContent = query;
        createZone.classList.remove('hidden');
    }
}

function _selectSupplier(id, name) {
    _selectedSupplierId = id;
    document.getElementById('modal-supplier-id').value = id;
    document.getElementById('modal-supplier-name').value = name;
    document.getElementById('supplier-badge-text').textContent = name;
    document.getElementById('supplier-selected-badge').classList.remove('hidden');
    document.getElementById('modal-supplier-name').classList.add('hidden');
    document.getElementById('supplier-suggestions').classList.add('hidden');
    document.getElementById('supplier-create-zone').classList.add('hidden');
}

function _clearSupplier() {
    _selectedSupplierId = null;
    document.getElementById('modal-supplier-id').value = '';
    document.getElementById('modal-supplier-name').value = '';
    document.getElementById('modal-supplier-name').classList.remove('hidden');
    document.getElementById('supplier-selected-badge').classList.add('hidden');
}

function _openModal(ean) {
    const modal = document.getElementById('product-modal');
    document.getElementById('modal-ean13').value = ean;
    document.getElementById('modal-product-type').value = 'book';
    document.getElementById('modal-name-input').value = '';
    document.getElementById('modal-description-input').value = '';
    document.getElementById('modal-price').value = '';
    document.getElementById('modal-author').value = '';
    document.getElementById('modal-diffuser').value = '';
    document.getElementById('modal-editor').value = '';
    document.getElementById('modal-genre').value = '';
    document.getElementById('modal-publication-year').value = '';
    document.getElementById('modal-pages').value = '';
    // Masquer toutes les listes de suggestions
    ['author-suggestions', 'diffuser-suggestions', 'editor-suggestions', 'genre-suggestions'].forEach(id => {
        document.getElementById(id)?.classList.add('hidden');
    });
    _clearSupplier();
    _toggleBookFields();
    modal.classList.remove('hidden');
    modal.classList.add('is_open');
    document.getElementById('modal-name-input').focus();
}

function _closeModal() {
    const modal = document.getElementById('product-modal');
    modal.classList.add('hidden');
    modal.classList.remove('is_open');
}

async function _submitProduct() {
    const ean13       = document.getElementById('modal-ean13').value;
    const productType = document.getElementById('modal-product-type').value;
    const name        = document.getElementById('modal-name-input').value.trim() || null;
    const description = document.getElementById('modal-description-input').value.trim() || null;
    const price       = Number.parseFloat(document.getElementById('modal-price').value) || 0;
    const author      = document.getElementById('modal-author').value.trim() || null;
    const diffuser   = document.getElementById('modal-diffuser').value.trim() || null;
    const editor     = document.getElementById('modal-editor').value.trim() || null;
    const genre      = document.getElementById('modal-genre').value.trim() || null;
    const pubYear    = document.getElementById('modal-publication-year').value.trim() || null;
    const pages      = document.getElementById('modal-pages').value.trim() || null;
    const supplierId  = Number(document.getElementById('modal-supplier-id').value);

    if (!name) { alert('Le nom est obligatoire.'); return; }
    if (!supplierId) { alert('Veuillez sélectionner ou créer un fournisseur.'); return; }

    const payload = {
        ean13, product_type: productType, supplier_id: supplierId, name, description,
        price, genre, publication_year: pubYear, pages
    };
    if (productType === 'book') {
        payload.author = author;
        payload.editor = editor;
        payload.diffuser = diffuser;
        payload.genre = genre;
        payload.publication_year = pubYear;
        payload.pages = pages;
    }

    const { ok, data } = await api.createProduct(payload);

    if (!ok || !data) {
        alert('Erreur lors de la création du produit.');
        return;
    }

    // Retirer l'EAN de la liste des inconnus et mettre à jour
    unknownList = unknownList.filter(e => e !== ean13);
    _closeModal();
    _render();
}
