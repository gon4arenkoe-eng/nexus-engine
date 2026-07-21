/**
 * NEXUS Engine V10 — Login JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const toggleBtn = document.getElementById('toggle-form');

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            loginForm.classList.toggle('hidden');
            registerForm.classList.toggle('hidden');
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password}),
                    credentials: 'same-origin',
                });

                const data = await response.json();

                if (response.ok) {
                    window.location.href = '/dashboard';
                } else {
                    showError(data.error || 'Login failed');
                }
            } catch (error) {
                showError('Network error');
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('reg-username').value;
            const email = document.getElementById('reg-email').value;
            const password = document.getElementById('reg-password').value;

            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, email, password}),
                });

                const data = await response.json();

                if (response.ok) {
                    showSuccess('Registration successful! Please login.');
                    loginForm.classList.remove('hidden');
                    registerForm.classList.add('hidden');
                } else {
                    showError(data.error || 'Registration failed');
                }
            } catch (error) {
                showError('Network error');
            }
        });
    }

    function showError(message) {
        const errorDiv = document.getElementById('error-message');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.className = 'error-message';
            setTimeout(() => errorDiv.textContent = '', 5000);
        }
    }

    function showSuccess(message) {
        const errorDiv = document.getElementById('error-message');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.className = 'success-message';
            setTimeout(() => errorDiv.textContent = '', 5000);
        }
    }
});
