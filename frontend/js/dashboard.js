// ============================================================
// dashboard.js — Dashboard Page Logic
// ============================================================
// This file handles the dashboard page:
//   - Checks if the user is logged in (redirects if not)
//   - Fetches and displays user info (name, role)
//   - Fetches and displays the user's projects
//   - Handles the "Create New Project" button
//   - Handles the logout button
//
// Depends on: api.js (must be loaded first)
// ============================================================

// ----------------------------------------------------------
// Utility: Format date for display
// ----------------------------------------------------------

/**
 * Format an ISO date string into a human-readable format.
 * @param {string} isoString - ISO 8601 date string from the API
 * @returns {string} Formatted date like "23 Nov 2026"
 */
function formatDate(isoString) {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    });
}

// ----------------------------------------------------------
// Utility: Get a human-readable status label
// ----------------------------------------------------------

/**
 * Map a project status code to a readable label.
 * @param {string} status - Status from the API
 * @returns {string} Human-readable label
 */
function getStatusLabel(status) {
    const labels = {
        'created':    'Created',
        'uploaded':   'Uploaded',
        'analyzing':  'Analysing',
        'needs_review': 'Needs Review',
        'generating': 'Generating',
        'ready':      'Ready',
    };
    return labels[status] || status;
}

// ----------------------------------------------------------
// Display User Info
// ----------------------------------------------------------

/**
 * Update the UI with the current user's information.
 * @param {Object} user - User object from the API
 */
function displayUserInfo(user) {
    // Set the welcome message
    const welcomeEl = document.getElementById('welcome-name');
    if (welcomeEl) {
        welcomeEl.textContent = user.full_name.split(' ')[0]; // First name only
    }

    // Set the user name in the top nav
    const userNameEl = document.getElementById('user-name');
    if (userNameEl) {
        userNameEl.textContent = user.full_name;
    }

    // Set the user role in the top nav
    const userRoleEl = document.getElementById('user-role');
    if (userRoleEl) {
        const roleLabels = { 'homeowner': 'Homeowner', 'builder': 'Builder' };
        userRoleEl.textContent = roleLabels[user.account_type] || user.account_type;
    }

    // Set the avatar initials
    const avatarEl = document.getElementById('user-avatar');
    if (avatarEl) {
        // Get initials: "John Smith" → "JS"
        const initials = user.full_name
            .split(' ')
            .map(n => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2);
        avatarEl.textContent = initials;
    }
}

// ----------------------------------------------------------
// Update Stat Cards
// ----------------------------------------------------------

/**
 * Update the three stat cards with project counts.
 * @param {Array} projects - List of project objects
 */
function updateStats(projects) {
    const totalEl    = document.getElementById('stat-total');
    const readyEl    = document.getElementById('stat-ready');
    const progressEl = document.getElementById('stat-progress');

    if (totalEl) totalEl.textContent = projects.length;

    if (readyEl) {
        const readyCount = projects.filter(p => p.status === 'ready').length;
        readyEl.textContent = readyCount;
    }

    if (progressEl) {
        const inProgress = projects.filter(p =>
            ['uploaded', 'analyzing', 'generating'].includes(p.status)
        ).length;
        progressEl.textContent = inProgress;
    }
}

// ----------------------------------------------------------
// Render Projects
// ----------------------------------------------------------

/**
 * Create the HTML for a single project card.
 * @param {Object} project - Project data from the API
 * @returns {string} HTML string for the project card
 */
function createProjectCard(project) {
    const statusClass = `status-${project.status}`;
    const statusLabel = getStatusLabel(project.status);
    const dateStr     = formatDate(project.created_at);
    const description = project.description || 'No description provided.';

    return `
        <div class="project-card fade-in">
            <div class="project-card-header">
                <div class="project-card-title">${escapeHtml(project.name)}</div>
                <span class="status-badge ${statusClass}">${statusLabel}</span>
            </div>
            <div class="project-card-desc">${escapeHtml(description)}</div>
            <div class="project-card-meta">
                <span>📅 ${dateStr}</span>
                <span>ID: #${project.id}</span>
            </div>
            <div class="project-card-actions">
                <button class="btn-open" onclick="openProject(${project.id})">
                    Open Project →
                </button>
            </div>
        </div>
    `;
}

/**
 * Escape HTML to prevent XSS attacks.
 * @param {string} str - String to escape
 * @returns {string} Safe HTML string
 */
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Render the projects list into the projects grid.
 * @param {Array} projects - List of project objects from the API
 */
function renderProjects(projects) {
    const gridEl     = document.getElementById('projects-grid');
    const emptyEl    = document.getElementById('empty-state');
    const loadingEl  = document.getElementById('projects-loading');

    // Hide loading indicator
    if (loadingEl) loadingEl.style.display = 'none';

    if (projects.length === 0) {
        // Show the empty state message
        if (gridEl)  gridEl.style.display  = 'none';
        if (emptyEl) emptyEl.style.display = 'block';
        return;
    }

    // Show the projects grid and hide empty state
    if (emptyEl) emptyEl.style.display = 'none';
    if (gridEl) {
        gridEl.style.display = 'grid';
        gridEl.innerHTML = projects.map(createProjectCard).join('');
    }
}

// ----------------------------------------------------------
// Action Handlers
// ----------------------------------------------------------

/**
 * Open a project. (Phase 2 will implement the 3D viewer)
 * For now, we show an alert.
 * @param {number} projectId - The project's ID
 */
function openProject(projectId) {
    alert(`Project viewer coming in Phase 2!\n\nProject ID: ${projectId}\n\nThis will open the 3D model viewer.`);
}

/**
 * Handle the "Create New Project" button click.
 * Redirects to the upload page which handles project creation + file upload.
 */
async function handleCreateProject() {
    // Navigate to the dedicated upload page (built in Phase 2)
    window.location.href = 'upload.html';
}

// ----------------------------------------------------------
// Data Loading
// ----------------------------------------------------------

/**
 * Fetch and display the current user's projects.
 */
async function loadProjects() {
    const loadingEl = document.getElementById('projects-loading');
    if (loadingEl) loadingEl.style.display = 'flex';

    try {
        const projects = await ProjectsAPI.list();
        updateStats(projects);
        renderProjects(projects);

    } catch (error) {
        // Projects API might not be ready yet (Phase 2)
        // Show empty state instead of crashing
        console.warn('Projects API not available yet:', error.message);
        updateStats([]);
        renderProjects([]);
    }
}

/**
 * Fetch and display the current user's info.
 */
async function loadUserInfo() {
    // First try to use cached user data for instant display
    const cachedUser = getUserData();
    if (cachedUser) {
        displayUserInfo(cachedUser);
    }

    try {
        // Then fetch fresh data from the API
        const user = await AuthAPI.getMe();
        displayUserInfo(user);
        setUserData(user);  // Update the cache

    } catch (error) {
        console.error('Could not fetch user info:', error.message);
        // If we have no user data at all, log out
        if (!cachedUser) {
            logout();
        }
    }
}

// ----------------------------------------------------------
// Page Initialisation
// ----------------------------------------------------------

/**
 * Main function that runs when the dashboard page loads.
 */
async function initDashboard() {
    // Check if the user is logged in
    if (!isLoggedIn()) {
        // Not logged in — send them to the login page
        window.location.href = '/app/login.html';
        return;
    }

    // Load data in parallel (both requests happen at the same time)
    await Promise.all([
        loadUserInfo(),
        loadProjects(),
    ]);
}

// Make handlers available globally (called from onclick in HTML)
window.openProject       = openProject;
window.handleCreateProject = handleCreateProject;
window.logout            = logout;

// Run the dashboard when the page finishes loading
document.addEventListener('DOMContentLoaded', initDashboard);
