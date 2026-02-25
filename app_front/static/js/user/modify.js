document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.register-container__form');
    if (!form) return; // Sortir si le formulaire n'existe pas

    const emailInput = form.querySelector('input[name="email"]');
    
    if (!emailInput) return; // Sortir si le champ email n'existe pas

    const emailErrorDiv = document.getElementById('email-error');

    // Validation du mail
    const validateEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    emailInput.addEventListener('blur', () => {
        const email = emailInput.value.trim();
        if (email && !validateEmail(email)) {
            emailErrorDiv.textContent = '✗ Veuillez entrer une adresse e-mail valide';
            emailErrorDiv.style.display = 'block';
        } else {
            emailErrorDiv.style.display = 'none';
        }
    });

    emailInput.addEventListener('focus', () => {
        emailErrorDiv.style.display = 'none';
    });

    if (form) {
        form.addEventListener('submit', (event) => {
            const email = emailInput.value.trim();

            if (!validateEmail(email)) {
                event.preventDefault();
                emailErrorDiv.textContent = '✗ Veuillez entrer une adresse e-mail valide';
                emailErrorDiv.style.display = 'block';
            }
        });
    }
});