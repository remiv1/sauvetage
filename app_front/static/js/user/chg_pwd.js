document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.register-container__form');
    if (!form) return; // Sortir si le formulaire n'existe pas

    const oldPasswordInput = form.querySelector('input[name="old_password"]');
    const passwordInput = form.querySelector('input[name="new_password"]');
    const confirmPasswordInput = form.querySelector('input[name="new_password_confirm"]');
    
    if (!oldPasswordInput || !passwordInput || !confirmPasswordInput) return; // Sortir si les champs n'existent pas

    const passwordToggle = document.getElementById('old-password-toggle');
    const newPasswordToggle = document.getElementById('new-password-toggle');
    const confirmPasswordToggle = document.getElementById('new-password-confirm-toggle');
    const passwordMatchDiv = document.getElementById('new-password-match');

    const passwordCriteria = {
        length: document.querySelector('#password-length'),
        uppercase: document.querySelector('#password-uppercase'),
        lowercase: document.querySelector('#password-lowercase'),
        number: document.querySelector('#password-number'),
        special: document.querySelector('#password-special')
    };

    // Toggle affichage du mot de passe
    if (passwordToggle) {
        passwordToggle.addEventListener('click', () => {
            if (oldPasswordInput.type === 'password') {
                oldPasswordInput.type = 'text';
                passwordToggle.textContent = '🙈';
            } else {
                oldPasswordInput.type = 'password';
                passwordToggle.textContent = '👁️';
            }
        });
    }

    if (newPasswordToggle) {
        newPasswordToggle.addEventListener('click', () => {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                newPasswordToggle.textContent = '🙈';
            } else {
                passwordInput.type = 'password';
                newPasswordToggle.textContent = '👁️';
            }
        });
    }

    if (confirmPasswordToggle) {
        confirmPasswordToggle.addEventListener('click', () => {
            if (confirmPasswordInput.type === 'password') {
                confirmPasswordInput.type = 'text';
                confirmPasswordToggle.textContent = '🙈';
            } else {
                confirmPasswordInput.type = 'password';
                confirmPasswordToggle.textContent = '👁️';
            }
        });
    }

    const validatePassword = (password) => {
        const criteria = {
            length: password.length >= 15,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /\d/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
        };

        for (const [key, isValid] of Object.entries(criteria)) {
            const element = passwordCriteria[key];
            if (!element) continue; // Ignorer si l'élément n'existe pas
            
            if (isValid) {
                element.classList.add('valid');
                element.classList.remove('invalid');
            } else {
                element.classList.add('invalid');
                element.classList.remove('valid');
            }
        }

        return Object.values(criteria).every(Boolean);
    };

    const checkPasswordMatch = () => {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        if (confirmPassword.length === 0) {
            passwordMatchDiv.style.display = 'none';
            return false;
        }

        if (password === confirmPassword) {
            passwordMatchDiv.classList.remove('invalid');
            passwordMatchDiv.classList.add('valid');
            passwordMatchDiv.textContent = '✓ Les mots de passe correspondent';
            passwordMatchDiv.style.display = 'block';
            return true;
        } else {
            passwordMatchDiv.classList.remove('valid');
            passwordMatchDiv.classList.add('invalid');
            passwordMatchDiv.textContent = '✗ Les mots de passe ne correspondent pas';
            passwordMatchDiv.style.display = 'block';
            return false;
        }
    };

    if (form) {
        passwordInput.addEventListener('input', () => {
            validatePassword(passwordInput.value);
            checkPasswordMatch();
        });

        confirmPasswordInput.addEventListener('input', () => {
            checkPasswordMatch();
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