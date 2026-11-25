// ============================================================
// js/processing.js — CV Pipeline Status Polling
// ============================================================
// This script:
//   1. Reads ?project_id=N from the URL
//   2. Triggers POST /api/v1/projects/{id}/analyze (CV pipeline)
//   3. Polls GET /api/v1/projects/{id} every 3 seconds
//   4. Redirects when analysis is complete
// ============================================================

// ----------------------------------------------------------
// Configuration
// ----------------------------------------------------------
const POLL_INTERVAL_MS = 3000;    // Poll every 3 seconds
const MAX_POLL_ATTEMPTS = 60;     // Max 3 minutes before timeout

// ----------------------------------------------------------
// State
// ----------------------------------------------------------
let projectId = null;
let pollTimer = null;
let pollCount = 0;
let analysisStarted = false;

// ----------------------------------------------------------
// Stage labels shown in the progress UI
// ----------------------------------------------------------
const STAGES = [
    { label: 'Loading floor plan image…',      pct: 10 },
    { label: 'Preprocessing & denoising…',     pct: 25 },
    { label: 'Detecting walls…',               pct: 40 },
    { label: 'Detecting rooms…',               pct: 55 },
    { label: 'Detecting doors & windows…',     pct: 68 },
    { label: 'Reading dimension labels (OCR)…', pct: 78 },
    { label: 'Detecting staircases…',          pct: 85 },
    { label: 'Building 3D geometry data…',     pct: 92 },
    { label: 'Saving results…',                pct: 97 },
];

let currentStageIndex = 0;
let stageTimer = null;

// ----------------------------------------------------------
// DOM References
// ----------------------------------------------------------
const progressFill  = document.getElementById('progress-fill');
const progressPct   = document.getElementById('progress-pct');
const stageLabel    = document.getElementById('stage-label');
const statusTitle   = document.getElementById('status-title');
const statusDesc    = document.getElementById('status-desc');
const errorBox      = document.getElementById('error-box');
const errorMsg      = document.getElementById('error-msg');
const retryBtn      = document.getElementById('retry-btn');

// ----------------------------------------------------------
// Entry point
// ----------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
    // Guard: redirect to login if not authenticated
    if (typeof isAuthenticated === 'function' && !isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    // Parse project_id from URL: processing.html?project_id=5
    const params = new URLSearchParams(window.location.search);
    projectId = parseInt(params.get('project_id'), 10);

    if (!projectId || isNaN(projectId)) {
        showError('No project ID found in URL. Please go back to the dashboard.');
        return;
    }

    // Start animated stage ticker (simulates progress before real data arrives)
    startStageTicker();

    // Start CV analysis
    await triggerAnalysis();
});

// ----------------------------------------------------------
// triggerAnalysis — POST /api/v1/projects/{id}/analyze
// ----------------------------------------------------------
async function triggerAnalysis() {
    try {
        const token = localStorage.getItem('access_token');
        const resp = await fetch(`/api/v1/projects/${projectId}/analyze`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });

        if (resp.ok) {
            // Analysis triggered successfully — now poll for status
            analysisStarted = true;
            startPolling();
        } else if (resp.status === 400) {
            // Project not in correct state — may already be done
            startPolling();
        } else {
            const data = await resp.json().catch(() => ({}));
            const detail = data.detail || `Server returned ${resp.status}`;
            showError(`Analysis failed to start: ${detail}`);
        }
    } catch (err) {
        showError(`Could not connect to the server. Please check that the app is running.\n\n${err.message}`);
    }
}

// ----------------------------------------------------------
// startPolling — GET /api/v1/projects/{id} every 3s
// ----------------------------------------------------------
function startPolling() {
    pollCount = 0;
    pollTimer = setInterval(pollStatus, POLL_INTERVAL_MS);
    // Poll immediately on first call
    pollStatus();
}

async function pollStatus() {
    pollCount++;

    if (pollCount > MAX_POLL_ATTEMPTS) {
        clearInterval(pollTimer);
        showError('Analysis is taking longer than expected. Please try again.');
        return;
    }

    try {
        const token = localStorage.getItem('access_token');
        const resp = await fetch(`/api/v1/projects/${projectId}`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!resp.ok) {
            console.warn('[Processing] Poll failed with status', resp.status);
            return; // Keep polling; transient error
        }

        const project = await resp.json();
        handleStatusUpdate(project.status);

    } catch (err) {
        console.warn('[Processing] Poll error (retrying):', err.message);
    }
}

// ----------------------------------------------------------
// handleStatusUpdate — act on project status
// ----------------------------------------------------------
function handleStatusUpdate(status) {
    console.log('[Processing] Project status:', status);

    switch (status) {
        case 'uploaded':
        case 'analyzing':
            // Still processing — keep polling & animating
            break;

        case 'needs_review':
            // Low confidence — go to correction interface
            clearInterval(pollTimer);
            clearInterval(stageTimer);
            setProgress(100, 'Review required');
            statusTitle.textContent = '⚠️ Review Needed';
            statusDesc.textContent = 'The AI found your floor plan but needs your help to verify some details.';
            setTimeout(() => {
                window.location.href = `correction.html?project_id=${projectId}`;
            }, 1500);
            break;

        case 'generating':
        case 'ready':
            // High confidence — go straight to viewer
            clearInterval(pollTimer);
            clearInterval(stageTimer);
            setProgress(100, 'Complete!');
            statusTitle.textContent = '✅ Analysis Complete!';
            statusDesc.textContent = 'Your floor plan has been processed. Opening the 3D viewer…';
            setTimeout(() => {
                window.location.href = `viewer.html?project_id=${projectId}`;
            }, 1500);
            break;

        case 'error':
            clearInterval(pollTimer);
            clearInterval(stageTimer);
            showError('The analysis encountered an error. Please try uploading again.');
            break;

        default:
            console.warn('[Processing] Unknown status:', status);
    }
}

// ----------------------------------------------------------
// startStageTicker — animates stage labels + progress bar
// while we wait for real API responses
// ----------------------------------------------------------
function startStageTicker() {
    setProgress(STAGES[0].pct, STAGES[0].label);

    stageTimer = setInterval(() => {
        currentStageIndex++;
        if (currentStageIndex >= STAGES.length) {
            clearInterval(stageTimer);
            return;
        }
        const stage = STAGES[currentStageIndex];
        setProgress(stage.pct, stage.label);
    }, 2800); // Advance every 2.8s (slightly under poll interval for smooth feel)
}

// ----------------------------------------------------------
// setProgress — updates the progress bar and label
// ----------------------------------------------------------
function setProgress(pct, label) {
    if (progressFill) progressFill.style.width = `${pct}%`;
    if (progressPct)  progressPct.textContent   = `${pct}%`;
    if (stageLabel)   stageLabel.textContent     = label || '';
}

// ----------------------------------------------------------
// showError — displays the error panel
// ----------------------------------------------------------
function showError(message) {
    clearInterval(pollTimer);
    clearInterval(stageTimer);

    if (errorBox) errorBox.classList.remove('hidden');
    if (errorMsg) errorMsg.textContent = message;
    if (statusTitle) statusTitle.textContent = '❌ Analysis Failed';
    if (statusDesc)  statusDesc.textContent  = 'Something went wrong. See the error below.';
    setProgress(0, '');
}

// ----------------------------------------------------------
// Retry button
// ----------------------------------------------------------
if (retryBtn) {
    retryBtn.addEventListener('click', () => {
        window.location.reload();
    });
}
