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
async function proceedToExtraction() {
    console.log('Starting extraction process...');
    
    // Show loading
    showLoading('Extracting passport data...');
    
    try {
        // Get session from localStorage
        const sessionData = JSON.parse(localStorage.getItem('uploadSession'));
        console.log('Session data:', sessionData);
        
        if (!sessionData || !sessionData.sessionId) {
            throw new Error('No upload session found. Please upload documents first.');
        }
        
        // Call extraction API
        console.log('Calling extraction API for session:', sessionData.sessionId);
        const response = await fetch(`/api/extract/passport/${sessionData.sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Extraction API error:', errorText);
            throw new Error(`Extraction failed: ${response.status} - ${errorText}`);
        }
        
        const result = await response.json();
        console.log('Extraction result:', result);
        
        hideLoading();
        
        // Display extraction results
        displayExtractionResults(result);
        
    } catch (error) {
        console.error('Extraction error:', error);
        hideLoading();
        
        // Show more detailed error message
        const errorMsg = `
            <div style="text-align: left;">
                <strong>Extraction failed:</strong><br>
                ${error.message}<br><br>
                <small>Check browser console for details. Make sure Docker is running.</small>
            </div>
        `;
        
        // Display error in the UI
        document.getElementById('successState').innerHTML = `
            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; color: #856404;">
                ${errorMsg}
                <br><br>
                <button class="btn-continue" onclick="location.reload()">Try Again</button>
            </div>
        `;
    }
}

// Display extraction results
function displayExtractionResults(result) {
    // Hide success state, show extraction results
    document.getElementById('successState').style.display = 'none';
    
    // Create extraction results UI
    const extractionHTML = `
        <div class="extraction-results">
            <h2 class="extraction-title">Passport Data Extracted</h2>
            <p class="extraction-subtitle">
                ${result.method === 'mrz' ? 'Data extracted from MRZ' : 'Data extracted using OCR'} 
                (${Math.round(result.confidence * 100)}% confidence)
            </p>
            
            <div class="extraction-data">
                <div class="data-group">
                    <h3>Personal Information</h3>
                    <div class="data-field">
                        <label>Full Name:</label>
                        <input type="text" value="${result.data.full_name || ''}" id="fullName">
                    </div>
                    <div class="data-field">
                        <label>Last Name:</label>
                        <input type="text" value="${result.data.last_name || ''}" id="lastName">
                    </div>
                    <div class="data-field">
                        <label>First Name:</label>
                        <input type="text" value="${result.data.first_name || ''}" id="firstName">
                    </div>
                </div>
                
                <div class="data-group">
                    <h3>Document Details</h3>
                    <div class="data-field">
                        <label>Passport Number:</label>
                        <input type="text" value="${result.data.passport_number || ''}" id="passportNumber">
                    </div>
                    <div class="data-field">
                        <label>Nationality:</label>
                        <input type="text" value="${result.data.nationality || ''}" id="nationality">
                    </div>
                    <div class="data-field">
                        <label>Country Code:</label>
                        <input type="text" value="${result.data.country_code || ''}" id="countryCode">
                    </div>
                </div>
                
                <div class="data-group">
                    <h3>Important Dates</h3>
                    <div class="data-field">
                        <label>Date of Birth:</label>
                        <input type="date" value="${result.data.date_of_birth || ''}" id="dateOfBirth">
                    </div>
                    <div class="data-field">
                        <label>Issue Date:</label>
                        <input type="date" value="${result.data.issue_date || ''}" id="issueDate">
                    </div>
                    <div class="data-field">
                        <label>Expiry Date:</label>
                        <input type="date" value="${result.data.expiry_date || ''}" id="expiryDate">
                    </div>
                </div>
                
                <div class="data-group">
                    <h3>Additional Info</h3>
                    <div class="data-field">
                        <label>Sex:</label>
                        <select id="sex">
                            <option value="">Select</option>
                            <option value="M" ${result.data.sex === 'M' ? 'selected' : ''}>Male</option>
                            <option value="F" ${result.data.sex === 'F' ? 'selected' : ''}>Female</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <div class="extraction-actions">
                <button class="btn-secondary" onclick="location.reload()">Upload Different Documents</button>
                <button class="btn-primary" onclick="proceedToG28Extraction()">Continue to G-28 Extraction</button>
            </div>
        </div>
    `;
    
    // Add styles if not already present
    if (!document.querySelector('.extraction-styles')) {
        const styles = document.createElement('style');
        styles.className = 'extraction-styles';
        styles.innerHTML = `
            .extraction-results {
                background: var(--alma-white);
                border-radius: 16px;
                padding: 32px;
                max-width: 800px;
                margin: 0 auto;
            }
            .extraction-title {
                color: var(--alma-teal);
                margin-bottom: 8px;
            }
            .extraction-subtitle {
                color: var(--alma-text-light);
                margin-bottom: 32px;
            }
            .extraction-data {
                display: grid;
                gap: 32px;
                margin-bottom: 32px;
            }
            .data-group {
                padding: 20px;
                background: var(--alma-light-bg);
                border-radius: 8px;
            }
            .data-group h3 {
                color: var(--alma-teal);
                margin-bottom: 16px;
                font-size: 16px;
            }
            .data-field {
                display: grid;
                grid-template-columns: 150px 1fr;
                align-items: center;
                margin-bottom: 12px;
            }
            .data-field label {
                font-weight: 500;
                color: var(--alma-text);
            }
            .data-field input,
            .data-field select {
                padding: 8px 12px;
                border: 1px solid var(--alma-border);
                border-radius: 4px;
                font-size: 14px;
            }
            .extraction-actions {
                display: flex;
                gap: 16px;
                justify-content: space-between;
            }
            .btn-secondary {
                background: var(--alma-border);
                color: var(--alma-text);
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
            }
            .btn-primary {
                background: var(--alma-teal);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
            }
            .btn-primary:hover {
                background: var(--alma-teal-dark);
            }
        `;
        document.head.appendChild(styles);
    }
    
    // Replace main content with extraction results
    document.querySelector('.main-content').innerHTML = extractionHTML;
}

// Proceed to G-28 extraction (Phase 4)
function proceedToG28Extraction() {
    alert('G-28 extraction will be implemented in Phase 4');
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