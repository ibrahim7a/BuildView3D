// ============================================================
// auth.js — Login & Register Page Logic
// ============================================================
// This file handles all authentication page interactions:
//   - Register form submission
//   - Login form submission
//   - Showing/hiding error messages
//   - Redirecting if already logged in
//   - Logout
//
// Depends on: api.js (must be loaded first in the HTML)
// ============================================================

// ----------------------------------------------------------
// Utility: Show an error message in the error box
// ----------------------------------------------------------

/**
 * Display an error message on the auth page.
 * @param {string} message - The error text to show
 */
function showError(message) {
    const errorEl = document.getElementById('error-message');
    if (!errorEl) return;

    errorEl.textContent = message;
    errorEl.classList.add('visible');

    // Automatically hide the error after 8 seconds
    setTimeout(() => {
        hideError();
    }, 8000);
}

/**
 * Hide the error message box.
 */
function hideError() {
    const errorEl = document.getElementById('error-message');
    if (!errorEl) return;
    errorEl.classList.remove('visible');
    errorEl.textContent = '';
}

// ----------------------------------------------------------
// Utility: Set button loading state
// ----------------------------------------------------------

/**
 * Put a button into a loading state (shows spinner text).
 * @param {HTMLButtonElement} btn - The button element
 * @param {boolean} loading       - True to show loading, false to restore
 * @param {string} originalText   - The original button text to restore
 */
function setButtonLoading(btn, loading, originalText) {
    if (loading) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-sm"></span> Please wait...';
        btn.classList.add('loading');
    } else {
        btn.disabled = false;
        btn.textContent = originalText;
        btn.classList.remove('loading');
    }
}

// ----------------------------------------------------------
// Register Page
// ----------------------------------------------------------

/**
 * Set up the register form handler.
 * Called when the register page loads.
 */
function setupRegisterForm() {
    const form = document.getElementById('register-form');
    if (!form) return;  // Not on the register page

    // If already logged in, redirect to dashboard
    if (isLoggedIn()) {
        window.location.href = '/app/dashboard.html';
        return;
    }

    form.addEventListener('submit', async function(event) {
        // Prevent the default form submission (page reload)
        event.preventDefault();
        hideError();

        // Get form values
        const fullName    = document.getElementById('full-name').value.trim();
        const email       = document.getElementById('email').value.trim();
        const password    = document.getElementById('password').value;
        const confirmPass = document.getElementById('confirm-password').value;
        const accountType = document.querySelector('input[name="account_type"]:checked')?.value || 'homeowner';

        const submitBtn = form.querySelector('[type="submit"]');

        // --------------------------------------------------
        // Client-side validation
        // --------------------------------------------------
        if (!fullName) {
            showError('Please enter your full name.');
            return;
        }

        if (!email) {
            showError('Please enter your email address.');
            return;
        }

        if (password.length < 6) {
            showError('Password must be at least 6 characters long.');
            return;
        }

        if (password !== confirmPass) {
            showError('Passwords do not match. Please try again.');
            return;
        }

        // --------------------------------------------------
        // Submit to API
        // --------------------------------------------------
        setButtonLoading(submitBtn, true, 'Create Account');

        try {
            const result = await AuthAPI.register({
                full_name: fullName,
                email: email,
                password: password,
                account_type: accountType,
            });

            // Save the token and user data
            setToken(result.access_token);
            setUserData(result.user);

            // Redirect to dashboard
            window.location.href = '/app/dashboard.html';

        } catch (error) {
            // Show the error message from the server
            showError(error.message || 'Registration failed. Please try again.');
            setButtonLoading(submitBtn, false, 'Create Account');
        }
    });
}

// ----------------------------------------------------------
// Login Page
// ----------------------------------------------------------

/**
 * Set up the login form handler.
 * Called when the login page loads.
 */
function setupLoginForm() {
    const form = document.getElementById('login-form');
    if (!form) return;  // Not on the login page

    // If already logged in, redirect to dashboard
    if (isLoggedIn()) {
        window.location.href = '/app/dashboard.html';
        return;
    }

    form.addEventListener('submit', async function(event) {
        // Prevent the default form submission
        event.preventDefault();
        hideError();

        // Get form values
        const email    = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        const submitBtn = form.querySelector('[type="submit"]');

        // --------------------------------------------------
        // Client-side validation
        // --------------------------------------------------
        if (!email) {
            showError('Please enter your email address.');
            return;
        }

        if (!password) {
            showError('Please enter your password.');
            return;
        }

        // --------------------------------------------------
        // Submit to API
        // --------------------------------------------------
        setButtonLoading(submitBtn, true, 'Log In');

        try {
            const result = await AuthAPI.login({
                email: email,
                password: password,
            });

            // Save the token and user data
            setToken(result.access_token);
            setUserData(result.user);

            // Redirect to dashboard
            window.location.href = '/app/dashboard.html';

        } catch (error) {
            showError(error.message || 'Login failed. Please check your email and password.');
            setButtonLoading(submitBtn, false, 'Log In');
        }
    });
}

// ----------------------------------------------------------
// Logout Function
// ----------------------------------------------------------

/**
 * Log the user out by removing their token and redirecting to login.
 * Can be called from any page.
 */
function logout() {
    removeToken();
    window.location.href = '/app/login.html';
}

// Make logout available globally (called from onclick attributes in HTML)
window.logout = logout;

// ----------------------------------------------------------
// Initialise on Page Load
// ----------------------------------------------------------
document.addEventListener('DOMContentLoaded', function() {
    setupRegisterForm();
    setupLoginForm();
});
