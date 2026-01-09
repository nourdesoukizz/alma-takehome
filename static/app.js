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
            <div style="background: #FFF3CD; border: 1px solid var(--alma-warning); padding: 20px; border-radius: 8px; color: #856404;">
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
                <button class="btn-primary" id="g28ExtractionBtn">Continue to G-28 Extraction</button>
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
    
    // Add event listener for G-28 extraction button after a short delay to ensure DOM is ready
    setTimeout(() => {
        const g28Btn = document.getElementById('g28ExtractionBtn');
        console.log('Looking for G-28 button:', g28Btn);
        if (g28Btn) {
            g28Btn.onclick = function() {
                console.log('G-28 button clicked via onclick');
                window.proceedToG28Extraction();
            };
            console.log('G-28 button onclick handler attached');
        } else {
            console.error('G-28 button not found in DOM');
        }
    }, 100);
}

// Proceed to G-28 extraction (Phase 4)
async function proceedToG28Extraction() {
    console.log('proceedToG28Extraction function called');
    
    try {
        // Get session from localStorage (we're in extraction phase now)
        const sessionData = JSON.parse(localStorage.getItem('uploadSession'));
        console.log('Session data from localStorage:', sessionData);
        
        if (!sessionData || !sessionData.sessionId) {
            console.error('No session found in localStorage');
            alert('No session found. Please upload documents first.');
            return;
        }
        
        console.log('Starting G-28 extraction with session:', sessionData.sessionId);
        showLoading('Extracting G-28 data...');
        
        const response = await fetch(`/api/extract/g28/${sessionData.sessionId}`, {
            method: 'POST'
        });
        
        console.log('G-28 extraction response status:', response.status);
        
        if (!response.ok) {
            const error = await response.json();
            console.error('G-28 extraction API error:', error);
            throw new Error(error.detail || 'G-28 extraction failed');
        }
        
        const result = await response.json();
        console.log('G-28 extraction result:', result);
        
        hideLoading();
        
        if (result.success) {
            displayG28Results(result);
        } else {
            showError('G-28 extraction failed. Please try again or check the document quality.');
        }
    } catch (error) {
        console.error('G-28 extraction error:', error);
        hideLoading();
        alert(`G-28 extraction failed: ${error.message}`);
    }
}

// Make function globally available
window.proceedToG28Extraction = proceedToG28Extraction;

// Proceed to form filling
async function proceedToFormFilling() {
    console.log('Proceeding to form filling...');
    
    try {
        // Get session data
        const sessionData = JSON.parse(localStorage.getItem('uploadSession') || '{}');
        
        // Get passport extraction data
        const passportResponse = await fetch(`/api/extract/passport/${sessionData.sessionId}`);
        const passportResult = await passportResponse.json();
        
        // Get G-28 extraction data
        const g28Response = await fetch(`/api/extract/g28/${sessionData.sessionId}`);
        const g28Result = await g28Response.json();
        
        // Store extraction data for form filling page
        const extractionData = {
            sessionId: sessionData.sessionId,
            passport: passportResult.data || {},
            g28: g28Result.data || {}
        };
        
        localStorage.setItem('extractionData', JSON.stringify(extractionData));
        
        // Navigate to form filling page
        window.location.href = '/form-fill.html';
        
    } catch (error) {
        console.error('Error proceeding to form filling:', error);
        showError('Failed to proceed to form filling. Please try again.');
    }
}

window.proceedToFormFilling = proceedToFormFilling;

// Display G-28 extraction results
function displayG28Results(result) {
    const extractionHTML = `
        <div class="extraction-results">
            <style>
                .extraction-results {
                    padding: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                }
                .results-header {
                    background: var(--alma-teal);
                    color: white;
                    padding: 24px;
                    border-radius: 12px;
                    margin-bottom: 24px;
                }
                .results-header h2 {
                    margin: 0;
                    font-size: 24px;
                }
                .extraction-info {
                    background: #f8f9fa;
                    padding: 16px;
                    border-radius: 8px;
                    margin-top: 12px;
                }
                .extraction-info span {
                    display: inline-block;
                    margin-right: 24px;
                    font-size: 14px;
                }
                .confidence-badge {
                    background: ${result.confidence >= 0.8 ? '#28a745' : result.confidence >= 0.6 ? '#ffc107' : '#dc3545'};
                    color: white;
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-size: 12px;
                    font-weight: bold;
                }
                .form-section {
                    background: white;
                    border: 1px solid var(--alma-border);
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 20px;
                }
                .form-section h3 {
                    color: var(--alma-teal);
                    margin-top: 0;
                    margin-bottom: 20px;
                    font-size: 18px;
                    border-bottom: 2px solid var(--alma-light);
                    padding-bottom: 8px;
                }
                .form-group {
                    margin-bottom: 20px;
                }
                .form-group label {
                    display: block;
                    color: var(--alma-text-secondary);
                    font-size: 14px;
                    margin-bottom: 6px;
                    font-weight: 600;
                }
                .form-group input, .form-group select {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid var(--alma-border);
                    border-radius: 6px;
                    font-size: 16px;
                }
                .form-row {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                }
                .action-buttons {
                    display: flex;
                    justify-content: space-between;
                    margin-top: 32px;
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
            </style>
            
            <div class="results-header">
                <h2>G-28 Form Data Extracted</h2>
                <div class="extraction-info">
                    <span>📄 Document: ${result.filename || 'G-28 Form'}</span>
                    <span class="confidence-badge">
                        Confidence: ${Math.round((result.confidence || 0) * 100)}%
                    </span>
                    <span>Method: ${result.method || 'OCR'}</span>
                </div>
            </div>
            
            <form id="g28DataForm">
                <!-- Attorney Information -->
                <div class="form-section">
                    <h3>Attorney/Representative Information</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Last Name</label>
                            <input type="text" name="attorney_last_name" 
                                value="${result.data?.attorney_name?.last || ''}" />
                        </div>
                        <div class="form-group">
                            <label>First Name</label>
                            <input type="text" name="attorney_first_name" 
                                value="${result.data?.attorney_name?.first || ''}" />
                        </div>
                        <div class="form-group">
                            <label>Middle Name</label>
                            <input type="text" name="attorney_middle_name" 
                                value="${result.data?.attorney_name?.middle || ''}" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Law Firm/Organization Name</label>
                        <input type="text" name="firm_name" 
                            value="${result.data?.firm_name || ''}" />
                    </div>
                </div>
                
                <!-- Eligibility Information -->
                <div class="form-section">
                    <h3>Eligibility Information</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Type</label>
                            <select name="attorney_type">
                                <option value="attorney" ${result.data?.eligibility?.type === 'attorney' ? 'selected' : ''}>
                                    Attorney
                                </option>
                                <option value="accredited_representative" 
                                    ${result.data?.eligibility?.type === 'accredited_representative' ? 'selected' : ''}>
                                    Accredited Representative
                                </option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Bar Number</label>
                            <input type="text" name="bar_number" 
                                value="${result.data?.eligibility?.bar_number || ''}" />
                        </div>
                        <div class="form-group">
                            <label>Bar State</label>
                            <input type="text" name="bar_state" 
                                value="${result.data?.eligibility?.bar_state || ''}" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label>USCIS Account Number (if any)</label>
                        <input type="text" name="uscis_account" 
                            value="${result.data?.eligibility?.uscis_account || ''}" />
                    </div>
                </div>
                
                <!-- Contact Information -->
                <div class="form-section">
                    <h3>Contact Information</h3>
                    <div class="form-group">
                        <label>Street Address</label>
                        <input type="text" name="street_address" 
                            value="${result.data?.address?.street || ''}" />
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Suite/Floor/Apt</label>
                            <input type="text" name="suite" 
                                value="${result.data?.address?.suite || ''}" />
                        </div>
                        <div class="form-group">
                            <label>City</label>
                            <input type="text" name="city" 
                                value="${result.data?.address?.city || ''}" />
                        </div>
                        <div class="form-group">
                            <label>State</label>
                            <input type="text" name="state" 
                                value="${result.data?.address?.state || ''}" />
                        </div>
                        <div class="form-group">
                            <label>ZIP Code</label>
                            <input type="text" name="zip" 
                                value="${result.data?.address?.zip || ''}" />
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Daytime Phone</label>
                            <input type="tel" name="phone" 
                                value="${result.data?.contact?.phone || ''}" />
                        </div>
                        <div class="form-group">
                            <label>Mobile Phone</label>
                            <input type="tel" name="mobile" 
                                value="${result.data?.contact?.mobile || ''}" />
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Email Address</label>
                            <input type="email" name="email" 
                                value="${result.data?.contact?.email || ''}" />
                        </div>
                        <div class="form-group">
                            <label>Fax Number</label>
                            <input type="tel" name="fax" 
                                value="${result.data?.contact?.fax || ''}" />
                        </div>
                    </div>
                </div>
                
                <div class="action-buttons">
                    <button type="button" class="btn-secondary" onclick="location.reload()">
                        Start Over
                    </button>
                    <button type="button" class="btn-primary" onclick="proceedToFormFilling()">
                        Continue to Form Filling
                    </button>
                </div>
            </form>
        </div>
    `;
    
    // Add styles if not already present
    if (!document.querySelector('style[data-extraction-styles]')) {
        const styles = document.createElement('style');
        styles.setAttribute('data-extraction-styles', 'true');
        styles.textContent = `
            :root {
                --alma-teal: #4A7C7E;
                --alma-teal-dark: #3a6c6e;
                --alma-light: #B8D4D3;
                --alma-lighter: #E8F3F3;
                --alma-text: #2C3E50;
                --alma-text-secondary: #5A6C7D;
                --alma-border: #D1D9E0;
                --alma-bg: #F7FAFA;
                --alma-white: #FFFFFF;
                --alma-success: #28a745;
                --alma-warning: #ffc107;
                --alma-error: #dc3545;
            }
        `;
        document.head.appendChild(styles);
    }
    
    // Replace main content with extraction results
    document.querySelector('.main-content').innerHTML = extractionHTML;
}

// Proceed to form filling - this function was moved earlier in the file
// The actual implementation is around line 646-679

// Utility Functions
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showLoading(text = 'Uploading...') {
    let overlay = document.getElementById('loadingOverlay');
    
    // If loading overlay doesn't exist, create it
    if (!overlay) {
        // Add styles if not present
        if (!document.querySelector('style[data-loading-styles]')) {
            const styles = document.createElement('style');
            styles.setAttribute('data-loading-styles', 'true');
            styles.textContent = `
                .loading-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9999;
                }
                .loading-content {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    text-align: center;
                }
                .spinner {
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #4A7C7E;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 20px;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(styles);
        }
        
        const overlayHTML = `
            <div id="loadingOverlay" class="loading-overlay" style="display: none;">
                <div class="loading-content">
                    <div class="spinner"></div>
                    <p id="loadingText">Loading...</p>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', overlayHTML);
        overlay = document.getElementById('loadingOverlay');
    }
    
    const loadingText = document.getElementById('loadingText');
    if (loadingText) {
        loadingText.textContent = text;
    }
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showError(message) {
    let container = document.getElementById('errorContainer');
    
    // If error container doesn't exist, create it
    if (!container) {
        const errorHTML = `
            <div id="errorContainer" class="error-container" style="display: none;">
                <div class="error-content">
                    <span id="errorText"></span>
                    <button onclick="clearError()" class="error-close">×</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', errorHTML);
        
        // Add styles if not present
        if (!document.querySelector('style[data-error-styles]')) {
            const styles = document.createElement('style');
            styles.setAttribute('data-error-styles', 'true');
            styles.textContent = `
                .error-container {
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #dc3545;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 5px;
                    z-index: 10000;
                    max-width: 500px;
                }
                .error-content {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                .error-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 24px;
                    cursor: pointer;
                    margin-left: 20px;
                }
            `;
            document.head.appendChild(styles);
        }
        
        container = document.getElementById('errorContainer');
    }
    
    const errorText = document.getElementById('errorText');
    if (errorText) {
        errorText.textContent = message;
    }
    if (container) {
        container.style.display = 'block';
    }
}

function clearError() {
    const container = document.getElementById('errorContainer');
    if (container) {
        container.style.display = 'none';
    }
}