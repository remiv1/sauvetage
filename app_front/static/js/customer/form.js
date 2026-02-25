/**
 * Module de gestion du formulaire de création de client.
 * Gère le toggle Particulier / Professionnel et la validation côté client.
 */

/**
 * Initialise le toggle Part/Pro et la logique du formulaire de création.
 */
export function setupCreateForm() {
    const togglePart = document.getElementById('toggle-part');
    const togglePro = document.getElementById('toggle-pro');
    const hiddenSelect = document.getElementById('customer-type');
    const sectionPart = document.getElementById('section-part');
    const sectionPro = document.getElementById('section-pro');

    if (!togglePart || !togglePro || !hiddenSelect) return;

    // Sync l'état initial
    syncToggle(hiddenSelect.value || 'part');

    togglePart.addEventListener('click', () => syncToggle('part'));
    togglePro.addEventListener('click', () => syncToggle('pro'));

    function syncToggle(value) {
        hiddenSelect.value = value;

        // Active/désactive les boutons toggle
        togglePart.classList.toggle('active', value === 'part');
        togglePro.classList.toggle('active', value === 'pro');

        // Affiche/masque les sections
        if (sectionPart) sectionPart.classList.toggle('hidden', value !== 'part');
        if (sectionPro) sectionPro.classList.toggle('hidden', value !== 'pro');

        // Active/désactive les required pour éviter les erreurs de validation
        toggleRequiredFields(sectionPart, value === 'part');
        toggleRequiredFields(sectionPro, value === 'pro');
    }

    // Validation SIRET en temps réel
    const siretInput = document.getElementById('siret-number');
    if (siretInput) {
        siretInput.addEventListener('input', () => {
            const val = siretInput.value.replaceAll(/\s/g, '');
            if (val.length > 0 && val.length !== 14) {
                siretInput.classList.add('input-error');
            } else {
                siretInput.classList.remove('input-error');
            }
        });
    }

    // Validation date de naissance
    const dobInput = document.getElementById('date-of-birth');
    if (dobInput) {
        dobInput.addEventListener('change', () => {
            const val = dobInput.value;
            if (val) {
                const date = new Date(val);
                const now = new Date();
                if (date > now) {
                    dobInput.classList.add('input-error');
                } else {
                    dobInput.classList.remove('input-error');
                }
            }
        });
    }
}

/**
 * Active ou désactive les attributs required des champs d'une section.
 * @param {HTMLElement|null} section - La section contenant les champs.
 * @param {boolean} enabled - Si true, active les required ; sinon les retire.
 */
function toggleRequiredFields(section, enabled) {
    if (!section) return;
    const inputs = section.querySelectorAll('input, select');
    inputs.forEach(input => {
        if (enabled) {
            if (input.dataset.wasRequired === 'true') {
                input.setAttribute('required', '');
            }
        } else {
            if (input.hasAttribute('required')) {
                input.dataset.wasRequired = 'true';
            }
            input.removeAttribute('required');
        }
    });
}
