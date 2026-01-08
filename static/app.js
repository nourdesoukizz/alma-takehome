// Application State
const appState = {
    sessionId: generateSessionId(),
    files: {
        passport: null,
        g28: null
    },
    uploadStatus: {
        passport: 'waiting',
        g28: 'waiting'
    }
};

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    setupDropZone();
    setupFileInput();
    console.log('Session ID:', appState.sessionId);
});

// Setup drag and drop zone
function setupDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    // Click to upload
    dropZone.addEventListener('click', () => fileInput.click());

    // Drag events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });
}

// Setup file input
function setupFileInput() {
    const fileInput = document.getElementById('fileInput');
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

// Handle uploaded files
async function handleFiles(files) {
    clearError();
    
    for (let file of files) {
        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
            showError(validation.error);
            continue;
        }

        // Show loading
        showLoading(`Analyzing ${file.name}...`);

        try {
            // Upload and detect file type
            const result = await uploadFile(file);
            
            // Update UI based on detected type
            if (result.documentType) {
                updateDocumentCard(result.documentType, file, result);
                appState.files[result.documentType] = file;
                appState.uploadStatus[result.documentType] = 'success';
            } else {
                // If auto-detection fails, ask user
                hideLoading();
                askUserForDocumentType(file, result);
            }
        } catch (error) {
            hideLoading();
            showError(`Upload failed: ${error.message}`);
        }
    }

    hideLoading();
    updateProcessButton();
}

// Validate file before upload
function validateFile(file) {
    // Check file type
    const validTypes = ['image/jpeg', 'image/png', 'application/pdf'];
    const extension = file.name.split('.').pop().toLowerCase();
    const validExtensions = ['jpg', 'jpeg', 'png', 'pdf'];

    if (!validTypes.includes(file.type) && !validExtensions.includes(extension)) {
        return { 
            valid: false, 
            error: `Invalid file type: ${file.name}. Please upload PDF, JPEG, or PNG files.` 
        };
    }

    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        return { 
            valid: false, 
            error: `File too large: ${file.name}. Maximum size is 10MB.` 
        };
    }

    return { valid: true };
}

// Upload file to server
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', appState.sessionId);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
        }

        const result = await response.json();
        return {
            success: result.success,
            documentType: result.documentType,
            fileName: result.fileName,
            fileSize: formatFileSize(result.fileSize),
            sessionId: result.sessionId,
            previewUrl: result.previewUrl
        };
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

// Simulate upload response for testing (remove when backend is ready)
function simulateUploadResponse(file) {
    const fileName = file.name.toLowerCase();
    let documentType = null;

    // Simple detection based on filename
    if (fileName.includes('passport')) {
        documentType = 'passport';
    } else if (fileName.includes('g28') || fileName.includes('g-28')) {
        documentType = 'g28';
    }

    return {
        success: true,
        documentType: documentType,
        fileName: file.name,
        fileSize: formatFileSize(file.size),
        sessionId: appState.sessionId,
        previewUrl: URL.createObjectURL(file)
    };
}

// Update document card with uploaded file
function updateDocumentCard(type, file, uploadResult) {
    const card = document.getElementById(`${type}Card`);
    const status = document.getElementById(`${type}Status`);
    const preview = document.getElementById(`${type}Preview`);
    const actions = document.getElementById(`${type}Actions`);

    // Update status
    status.innerHTML = '<span class="status-success">✓ Uploaded</span>';

    // Update preview
    if (uploadResult.previewUrl) {
        preview.innerHTML = `
            <div class="file-preview">
                ${file.type.startsWith('image/') 
                    ? `<img src="${uploadResult.previewUrl}" alt="${file.name}" class="preview-image">`
                    : '<div class="card-icon">📄</div>'
                }
                <div class="preview-filename">${file.name}</div>
                <div class="preview-filesize">${formatFileSize(file.size)}</div>
            </div>
        `;
    }

    // Show actions
    actions.style.display = 'block';
}

// Ask user to specify document type if auto-detection fails
function askUserForDocumentType(file, uploadResult) {
    // Check which slots are empty
    const passportEmpty = !appState.files.passport;
    const g28Empty = !appState.files.g28;

    if (passportEmpty && !g28Empty) {
        // Only passport slot empty
        updateDocumentCard('passport', file, uploadResult);
        appState.files.passport = file;
        appState.uploadStatus.passport = 'success';
    } else if (!passportEmpty && g28Empty) {
        // Only G-28 slot empty
        updateDocumentCard('g28', file, uploadResult);
        appState.files.g28 = file;
        appState.uploadStatus.g28 = 'success';
    } else if (passportEmpty && g28Empty) {
        // Both empty - show selection dialog
        showDocumentTypeDialog(file, uploadResult);
    } else {
        // Both full - ask which to replace
        showReplaceDialog(file, uploadResult);
    }

    updateProcessButton();
}

// Show document type selection dialog
function showDocumentTypeDialog(file, uploadResult) {
    const message = `Unable to auto-detect document type for "${file.name}". Is this a Passport or G-28 form?`;
    
    // Simple implementation - use confirm for now
    const isPassport = confirm(message + '\n\nClick OK for Passport, Cancel for G-28');
    const type = isPassport ? 'passport' : 'g28';
    
    updateDocumentCard(type, file, uploadResult);
    appState.files[type] = file;
    appState.uploadStatus[type] = 'success';
    updateProcessButton();
}

// Show replace dialog when both slots are full
function showReplaceDialog(file, uploadResult) {
    const message = `Both document slots are full. Replace Passport or G-28 with "${file.name}"?`;
    
    const replacePassport = confirm(message + '\n\nClick OK to replace Passport, Cancel to replace G-28');
    const type = replacePassport ? 'passport' : 'g28';
    
    updateDocumentCard(type, file, uploadResult);
    appState.files[type] = file;
    appState.uploadStatus[type] = 'success';
    updateProcessButton();
}

// Remove uploaded file
function removeFile(type) {
    appState.files[type] = null;
    appState.uploadStatus[type] = 'waiting';

    // Reset card UI
    const status = document.getElementById(`${type}Status`);
    const preview = document.getElementById(`${type}Preview`);
    const actions = document.getElementById(`${type}Actions`);

    status.innerHTML = '<span class="status-waiting">Waiting for upload</span>';
    preview.innerHTML = '<div class="empty-state"><p>No file uploaded yet</p></div>';
    actions.style.display = 'none';

    updateProcessButton();
}

// Update process button state
function updateProcessButton() {
    const processBtn = document.getElementById('processBtn');
    const actionHint = document.querySelector('.action-hint');
    
    const bothUploaded = appState.files.passport && appState.files.g28;
    
    processBtn.disabled = !bothUploaded;
    
    if (bothUploaded) {
        actionHint.textContent = 'Ready to process documents';
        actionHint.style.color = 'var(--alma-success)';
    } else {
        const passportStatus = appState.files.passport ? '✓' : '○';
        const g28Status = appState.files.g28 ? '✓' : '○';
        actionHint.innerHTML = `Passport ${passportStatus} &nbsp;&nbsp; G-28 Form ${g28Status}`;
        actionHint.style.color = 'var(--alma-text-light)';
    }
}

// Process documents
document.getElementById('processBtn').addEventListener('click', async function() {
    if (!appState.files.passport || !appState.files.g28) {
        showError('Please upload both documents before processing.');
        return;
    }

    // Hide upload section, show processing state
    document.querySelector('.upload-section').style.display = 'none';
    document.getElementById('processingState').style.display = 'block';

    try {
        // Call real API
        const response = await fetch(`/api/process/${appState.sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Processing failed');
        }

        const result = await response.json();
        
        // Show success state
        document.getElementById('processingState').style.display = 'none';
        document.getElementById('successState').style.display = 'block';
        
        // Store session for next phase
        localStorage.setItem('uploadSession', JSON.stringify({
            sessionId: appState.sessionId,
            files: {
                passport: appState.files.passport.name,
                g28: appState.files.g28.name
            },
            processed: true,
            timestamp: Date.now()
        }));
    } catch (error) {
        console.error('Processing error:', error);
        showError(`Processing failed: ${error.message}`);
        document.getElementById('processingState').style.display = 'none';
        document.querySelector('.upload-section').style.display = 'block';
    }
});

// Proceed to extraction phase
function proceedToExtraction() {
    // This will be implemented in Phase 3
    alert('Proceeding to document extraction... (Phase 3)');
    // window.location.href = '/extraction';
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showLoading(text = 'Uploading...') {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    loadingText.textContent = text;
    overlay.style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showError(message) {
    const container = document.getElementById('errorContainer');
    const errorText = document.getElementById('errorText');
    errorText.textContent = message;
    container.style.display = 'block';
}

function clearError() {
    document.getElementById('errorContainer').style.display = 'none';
}