// ============================================================
// js/upload.js — Upload Page Logic
// ============================================================
// Handles the full upload flow:
//   1. Create project (name + description → POST /projects)
//   2. Upload floor plan file (POST /projects/{id}/upload)
//   3. Redirect to processing page (to be built in Phase 3)
// ============================================================

// ----------------------------------------------------------
// State
// ----------------------------------------------------------
let selectedFile = null;        // The File object the user selected
let createdProjectId = null;    // Set after Step 1 creates the project

// ----------------------------------------------------------
// DOM References (resolved after DOMContentLoaded)
// ----------------------------------------------------------
const dom = {};

document.addEventListener('DOMContentLoaded', () => {
    // Guard: redirect to login if not authenticated
    if (!isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    // Load user info into the nav bar
    loadUserInfo();

    // Resolve DOM elements
    dom.step1 = document.getElementById('step-1');
    dom.step2 = document.getElementById('step-2');
    dom.step3 = document.getElementById('step-3');

    dom.step2Indicator = document.getElementById('step-2-indicator');
    dom.step3Indicator = document.getElementById('step-3-indicator');

    dom.projectForm    = document.getElementById('project-form');
    dom.projectName    = document.getElementById('project-name');
    dom.projectDesc    = document.getElementById('project-desc');
    dom.nameCount      = document.getElementById('name-count');
    dom.descCount      = document.getElementById('desc-count');
    dom.projectError   = document.getElementById('project-error');
    dom.createBtn      = document.getElementById('create-project-btn');

    dom.projectId      = document.getElementById('project-id');
    dom.dropZone       = document.getElementById('drop-zone');
    dom.fileInput      = document.getElementById('file-input');
    dom.filePreview    = document.getElementById('file-preview');
    dom.fileIcon       = document.getElementById('file-icon');
    dom.fileName       = document.getElementById('file-name');
    dom.fileSize       = document.getElementById('file-size');
    dom.fileRemoveBtn  = document.getElementById('file-remove-btn');
    dom.imgPreviewCont = document.getElementById('image-preview-container');
    dom.imgPreview     = document.getElementById('image-preview');
    dom.uploadProgress = document.getElementById('upload-progress');
    dom.progressText   = document.getElementById('progress-text');
    dom.progressPct    = document.getElementById('progress-pct');
    dom.progressFill   = document.getElementById('progress-bar-fill');
    dom.uploadError    = document.getElementById('upload-error');
    dom.uploadBtn      = document.getElementById('upload-btn');

    // Attach event listeners
    attachListeners();
});


// ----------------------------------------------------------
// Step 1: Create Project
// ----------------------------------------------------------

function attachListeners() {
    // Character counters
    dom.projectName.addEventListener('input', () => {
        dom.nameCount.textContent = dom.projectName.value.length;
    });
    dom.projectDesc.addEventListener('input', () => {
        dom.descCount.textContent = dom.projectDesc.value.length;
    });

    // Step 1 form submit
    dom.projectForm.addEventListener('submit', handleCreateProject);

    // ---- Drag & Drop ----
    dom.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dom.dropZone.classList.add('drag-over');
    });
    dom.dropZone.addEventListener('dragleave', () => {
        dom.dropZone.classList.remove('drag-over');
    });
    dom.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dom.dropZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) handleFileSelected(file);
    });

    // Keyboard accessibility for drop zone
    dom.dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') dom.fileInput.click();
    });

    // File input (Browse button)
    dom.fileInput.addEventListener('change', () => {
        if (dom.fileInput.files[0]) handleFileSelected(dom.fileInput.files[0]);
    });

    // Remove file button
    dom.fileRemoveBtn.addEventListener('click', clearSelectedFile);

    // Upload button
    dom.uploadBtn.addEventListener('click', handleUpload);
}


async function handleCreateProject(e) {
    e.preventDefault();
    hideError(dom.projectError);

    const name = dom.projectName.value.trim();
    if (!name) {
        showError(dom.projectError, 'Please enter a project name.');
        return;
    }

    dom.createBtn.disabled = true;
    dom.createBtn.textContent = 'Creating project...';

    try {
        const project = await createProject({
            name: name,
            description: dom.projectDesc.value.trim() || null,
        });

        createdProjectId = project.id;
        dom.projectId.value = project.id;

        // Advance to Step 2
        goToStep(2);

    } catch (err) {
        showError(dom.projectError, err.message || 'Failed to create project. Please try again.');
        dom.createBtn.disabled = false;
        dom.createBtn.textContent = 'Continue to Upload →';
    }
}


// ----------------------------------------------------------
// Step 2: File Selection
// ----------------------------------------------------------

function handleFileSelected(file) {
    // Client-side validation before we even show the file
    const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];
    const allowedExts = ['.jpg', '.jpeg', '.png', '.pdf'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!allowedExts.includes(ext)) {
        showError(dom.uploadError, `"${file.name}" is not a supported format. Please upload a JPG, PNG, or PDF file.`);
        return;
    }

    const maxSize = 20 * 1024 * 1024; // 20 MB
    if (file.size > maxSize) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
        showError(dom.uploadError, `The file (${sizeMB} MB) exceeds the 20 MB limit. Please reduce the file size.`);
        return;
    }

    if (file.size === 0) {
        showError(dom.uploadError, 'The selected file is empty. Please choose a valid floor plan file.');
        return;
    }

    hideError(dom.uploadError);
    selectedFile = file;

    // Show preview panel
    dom.filePreview.style.display = 'block';
    dom.dropZone.style.display = 'none';

    // Set icon based on type
    dom.fileIcon.textContent = file.type === 'application/pdf' ? '📄' : '🖼️';
    dom.fileName.textContent = file.name;
    dom.fileSize.textContent = formatBytes(file.size);

    // Show image thumbnail for JPG/PNG
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            dom.imgPreview.src = e.target.result;
            dom.imgPreviewCont.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        dom.imgPreviewCont.style.display = 'none';
    }

    // Enable the upload button
    dom.uploadBtn.disabled = false;
}


function clearSelectedFile() {
    selectedFile = null;
    dom.filePreview.style.display = 'none';
    dom.dropZone.style.display = 'block';
    dom.fileInput.value = '';
    dom.imgPreview.src = '';
    dom.imgPreviewCont.style.display = 'none';
    dom.uploadBtn.disabled = true;
    hideError(dom.uploadError);
}


// ----------------------------------------------------------
// Step 2: Upload
// ----------------------------------------------------------

async function handleUpload() {
    if (!selectedFile || !createdProjectId) return;

    dom.uploadBtn.disabled = true;
    dom.uploadBtn.textContent = 'Uploading...';
    dom.uploadProgress.style.display = 'block';
    hideError(dom.uploadError);

    // Animate progress to show activity (real XHR progress is below)
    setProgress(10, 'Uploading floor plan...');

    try {
        // Use XMLHttpRequest so we can get real upload progress events
        await uploadFloorPlanWithProgress(
            createdProjectId,
            selectedFile,
            (pct) => setProgress(pct, 'Uploading...')
        );

        setProgress(100, 'Upload complete!');

        // Brief pause before transitioning so user sees 100%
        await sleep(600);

        // Advance to success step
        goToStep(3);

        // Redirect to processing page after a moment
        await sleep(2000);
        window.location.href = `processing.html?project_id=${createdProjectId}`;

    } catch (err) {
        dom.uploadProgress.style.display = 'none';
        dom.uploadBtn.disabled = false;
        dom.uploadBtn.textContent = '🚀 Upload & Analyze Floor Plan';
        showError(dom.uploadError, err.message || 'Upload failed. Please try again.');
    }
}


function setProgress(pct, text) {
    dom.progressFill.style.width = pct + '%';
    dom.progressPct.textContent = pct + '%';
    dom.progressText.textContent = text;
}


// ----------------------------------------------------------
// Step Navigation
// ----------------------------------------------------------

function goToStep(step) {
    // Hide all steps
    dom.step1.style.display = 'none';
    dom.step2.style.display = 'none';
    dom.step3.style.display = 'none';

    // Show the target step
    if (step === 2) {
        dom.step2.style.display = 'block';
        dom.step2Indicator.classList.add('active');
    } else if (step === 3) {
        dom.step3.style.display = 'block';
        dom.step2Indicator.classList.remove('active');
        dom.step2Indicator.classList.add('completed');
        dom.step3Indicator.classList.add('active');
    }

    // Scroll to top of page
    window.scrollTo({ top: 0, behavior: 'smooth' });
}


// ----------------------------------------------------------
// API Calls (uses api.js helpers)
// ----------------------------------------------------------

async function createProject(data) {
    return await apiPost('/api/v1/projects/', data);
}


function uploadFloorPlanWithProgress(projectId, file, onProgress) {
    return new Promise((resolve, reject) => {
        const token = getToken();
        if (!token) {
            reject(new Error('Not authenticated. Please log in again.'));
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', `/api/v1/projects/${projectId}/upload`);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);

        // Real upload progress
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 90); // cap at 90% (10% for server processing)
                onProgress(pct);
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    resolve(data);
                } catch {
                    resolve({});
                }
            } else {
                let msg = `Upload failed (${xhr.status}).`;
                try {
                    const err = JSON.parse(xhr.responseText);
                    if (err.detail) msg = err.detail;
                } catch {}
                reject(new Error(msg));
            }
        };

        xhr.onerror = () => reject(new Error('Network error. Please check your connection and try again.'));
        xhr.ontimeout = () => reject(new Error('Upload timed out. Please try again.'));
        xhr.timeout = 120000; // 2 minute timeout

        xhr.send(formData);
    });
}


// ----------------------------------------------------------
// User Info in Nav (from auth.js)
// ----------------------------------------------------------

async function loadUserInfo() {
    try {
        const user = await getCurrentUser();
        const avatarEl = document.getElementById('user-avatar');
        const nameEl   = document.getElementById('user-name');
        if (avatarEl && user.full_name) avatarEl.textContent = user.full_name[0].toUpperCase();
        if (nameEl && user.full_name)   nameEl.textContent = user.full_name;
    } catch {}
}


// ----------------------------------------------------------
// Utilities
// ----------------------------------------------------------

function formatBytes(bytes) {
    if (bytes < 1024)        return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showError(el, msg) {
    el.textContent = msg;
    el.style.display = 'block';
}

function hideError(el) {
    el.textContent = '';
    el.style.display = 'none';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

