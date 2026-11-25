// ============================================================
// api.js — API Client Module
// ============================================================
// This file provides all the functions needed to communicate
// with the BuildView 3D backend API.
//
// It handles:
//   - Storing and retrieving the JWT auth token
//   - Making authenticated API requests
//   - User authentication (register, login, get current user)
//   - Project management (list, create, get)
//
// Usage: Include this with <script src="js/api.js"></script>
// All functions are attached to the window object so they're
// accessible from other script files.
// ============================================================

// ----------------------------------------------------------
// Base API URL
// Change this if your backend runs on a different port.
// ----------------------------------------------------------
const API_BASE = 'http://localhost:8000/api/v1';

// ----------------------------------------------------------
// Token Management
// The JWT token is stored in localStorage so it persists
// across page refreshes and browser sessions.
// ----------------------------------------------------------

/**
 * Get the stored auth token from localStorage.
 * @returns {string|null} The token, or null if not logged in
 */
function getToken() {
    return localStorage.getItem('buildview_token');
}

/**
 * Save an auth token to localStorage.
 * @param {string} token - The JWT token to store
 */
function setToken(token) {
    localStorage.setItem('buildview_token', token);
}

/**
 * Remove the auth token (log out).
 */
function removeToken() {
    localStorage.removeItem('buildview_token');
    localStorage.removeItem('buildview_user');
}

/**
 * Check if the user is currently logged in.
 * @returns {boolean} True if a token exists
 */
function isLoggedIn() {
    return !!getToken();
}

/**
 * Save user info to localStorage for quick access.
 * @param {Object} user - The user object from the API
 */
function setUserData(user) {
    localStorage.setItem('buildview_user', JSON.stringify(user));
}

/**
 * Get saved user info from localStorage.
 * @returns {Object|null} The user object, or null if not found
 */
function getUserData() {
    const data = localStorage.getItem('buildview_user');
    if (!data) return null;
    try {
        return JSON.parse(data);
    } catch {
        return null;
    }
}

// ----------------------------------------------------------
// Core API Fetch Wrapper
// ----------------------------------------------------------

/**
 * Make an authenticated API request.
 *
 * Automatically:
 *   - Adds the Authorization header if a token is stored
 *   - Sets Content-Type to application/json
 *   - Parses the JSON response
 *   - Redirects to login if the token has expired (401)
 *   - Throws an error with the server's error message on failure
 *
 * @param {string} endpoint - The API path (e.g., '/auth/me')
 * @param {Object} options  - Fetch options (method, body, etc.)
 * @returns {Promise<Object>} Parsed JSON response data
 * @throws {Error} With the server's error message
 */
async function apiFetch(endpoint, options = {}) {
    const token = getToken();

    // Build the full URL
    const url = `${API_BASE}${endpoint}`;

    // Set up default headers
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,  // Allow caller to override/add headers
    };

    // Add the Authorization header if we have a token
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // Make the request
    const response = await fetch(url, {
        ...options,
        headers,
    });

    // Handle token expiry — redirect to login
    if (response.status === 401) {
        removeToken();
        window.location.href = '/app/login.html';
        return;
    }

    // Parse the JSON response body
    let data;
    try {
        data = await response.json();
    } catch {
        // If we can't parse JSON, throw a generic error
        if (!response.ok) {
            throw new Error(`Server error: ${response.status} ${response.statusText}`);
        }
        return {};
    }

    // If the response was not OK (4xx or 5xx), throw an error
    if (!response.ok) {
        // FastAPI returns errors in { detail: "..." } format
        const message = data.detail || data.message || `Request failed with status ${response.status}`;
        throw new Error(message);
    }

    return data;
}

// ----------------------------------------------------------
// Auth API
// Functions for authentication endpoints.
// ----------------------------------------------------------
const AuthAPI = {
    /**
     * Register a new user account.
     * @param {Object} data - { email, password, full_name, account_type }
     * @returns {Promise<Object>} { access_token, token_type, user }
     */
    async register(data) {
        return apiFetch('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Log in with email and password.
     * @param {Object} data - { email, password }
     * @returns {Promise<Object>} { access_token, token_type, user }
     */
    async login(data) {
        return apiFetch('/auth/login', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Get the currently logged-in user's information.
     * Requires a valid token to be stored.
     * @returns {Promise<Object>} User object
     */
    async getMe() {
        return apiFetch('/auth/me', {
            method: 'GET',
        });
    },
};

// ----------------------------------------------------------
// Projects API
// Functions for project-related endpoints.
// (Full implementation in Phase 2 — stubs here)
// ----------------------------------------------------------
const ProjectsAPI = {
    /**
     * Get all projects for the current user.
     * @returns {Promise<Array>} List of project objects
     */
    async list() {
        return apiFetch('/projects', {
            method: 'GET',
        });
    },

    /**
     * Create a new project.
     * @param {Object} data - { name, description }
     * @returns {Promise<Object>} The created project object
     */
    async create(data) {
        return apiFetch('/projects', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Get a single project by ID.
     * @param {number} id - The project ID
     * @returns {Promise<Object>} The project object
     */
    async get(id) {
        return apiFetch(`/projects/${id}`, {
            method: 'GET',
        });
    },
};

// ----------------------------------------------------------
// Make everything available globally
// (Since we're not using a module bundler, we attach to window)
// ----------------------------------------------------------
window.getToken    = getToken;
window.setToken    = setToken;
window.removeToken = removeToken;
window.isLoggedIn  = isLoggedIn;
window.setUserData = setUserData;
window.getUserData = getUserData;
window.apiFetch    = apiFetch;
window.AuthAPI     = AuthAPI;
window.ProjectsAPI = ProjectsAPI;

// ----------------------------------------------------------
// Convenience wrappers
// ----------------------------------------------------------

/**
 * Shorthand for a POST request via apiFetch.
 * @param {string} endpoint  - API path
 * @param {Object} body      - JSON body
 * @returns {Promise<Object>}
 */
async function apiPost(endpoint, body) {
    return apiFetch(endpoint, { method: 'POST', body: JSON.stringify(body) });
}

/**
 * Alias for isLoggedIn — used by some pages.
 */
function isAuthenticated() {
    return isLoggedIn();
}

/**
 * Fetch the currently logged-in user from the API.
 * @returns {Promise<Object>} User object
 */
async function getCurrentUser() {
    return AuthAPI.getMe();
}

window.apiPost        = apiPost;
window.isAuthenticated = isAuthenticated;
window.getCurrentUser  = getCurrentUser;
