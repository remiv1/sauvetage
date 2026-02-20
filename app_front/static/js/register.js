document.addEventListener('DOMContentLoaded', () => {
    console.log('Register JS loaded');
    const form = document.querySelector('.register-container__form');
    if (!form) return; // Sortir si le formulaire n'existe pas

    const passwordInput = form.querySelector('input[name="password"]');
    const confirmPasswordInput = form.querySelector('input[name="confirm_password"]');
    const emailInput = form.querySelector('input[name="email"]');
    
    if (!passwordInput || !confirmPasswordInput || !emailInput) return; // Sortir si les champs n'existent pas

    const passwordToggle = document.getElementById('password-toggle');
    const confirmPasswordToggle = document.getElementById('confirm-password-toggle');
    const passwordMatchDiv = document.getElementById('password-match');
    const emailErrorDiv = document.getElementById('email-error');

    const passwordCriteria = {
        length: document.querySelector('#password-length'),
        uppercase: document.querySelector('#password-uppercase'),
        lowercase: document.querySelector('#password-lowercase'),
        number: document.querySelector('#password-number'),
        special: document.querySelector('#password-special')
    };

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

    // Toggle affichage du mot de passe
    if (passwordToggle) {
        passwordToggle.addEventListener('click', () => {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                passwordToggle.textContent = '🙈';
            } else {
                passwordInput.type = 'password';
                passwordToggle.textContent = '👁️';
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
        console.log('Form found');
        passwordInput.addEventListener('input', () => {
            validatePassword(passwordInput.value);
            checkPasswordMatch();
        });

        confirmPasswordInput.addEventListener('input', () => {
            checkPasswordMatch();
        });

        form.addEventListener('submit', (event) => {
            console.log('Form submitted');
            const password = passwordInput.value;
            const confirmPassword = confirmPasswordInput.value;
            const email = emailInput.value.trim();

            if (!validateEmail(email)) {
                event.preventDefault();
                emailErrorDiv.textContent = '✗ Veuillez entrer une adresse e-mail valide';
                emailErrorDiv.style.display = 'block';
            } else if (!validatePassword(password)) {
                event.preventDefault();
                alert('Le mot de passe ne respecte pas les critères requis.');
            } else if (password !== confirmPassword) {
                event.preventDefault();
                alert('Les mots de passe ne correspondent pas. Veuillez réessayer.');
            }
        });
    }
});