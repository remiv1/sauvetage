document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.register-form');
    const passwordInput = form.querySelector('input[name="password"]');
    const confirmPasswordInput = form.querySelector('input[name="confirm_password"]');
    const passwordCriteria = {
        length: document.querySelector('#password-length'),
        uppercase: document.querySelector('#password-uppercase'),
        lowercase: document.querySelector('#password-lowercase'),
        number: document.querySelector('#password-number'),
        special: document.querySelector('#password-special')
    };

    const validatePassword = (password) => {
        const criteria = {
            length: password.length >= 15,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /[0-9]/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
        };

        for (const [key, isValid] of Object.entries(criteria)) {
            if (isValid) {
                passwordCriteria[key].classList.add('valid');
                passwordCriteria[key].classList.remove('invalid');
            } else {
                passwordCriteria[key].classList.add('invalid');
                passwordCriteria[key].classList.remove('valid');
            }
        }

        return Object.values(criteria).every(Boolean);
    };

    if (form) {
        passwordInput.addEventListener('input', () => {
            validatePassword(passwordInput.value);
        });

        form.addEventListener('submit', (event) => {
            const password = passwordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            if (!validatePassword(password)) {
                event.preventDefault();
                alert('Le mot de passe ne respecte pas les critères requis.');
            } else if (password !== confirmPassword) {
                event.preventDefault();
                alert('Les mots de passe ne correspondent pas. Veuillez réessayer.');
            }
        });
    }
});