// MedGuard AI - Frontend JavaScript
// Simple vanilla JS - no build tools needed

const API_URL = 'http://localhost:8000';

// State
let validationResults = null;
let ocrResults = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeFileUploads();
    initializeButtons();
    checkBackendStatus();
});

// Tab Navigation
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Update buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update content
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
}

// File Upload Handling
function initializeFileUploads() {
    // CSV Upload
    const csvInput = document.getElementById('csv-file');
    const csvArea = document.getElementById('csv-upload-area');
    const csvInfo = document.getElementById('csv-file-info');
    const csvFileName = document.getElementById('csv-file-name');
    const csvClear = document.getElementById('csv-clear');
    const validateBtn = document.getElementById('validate-btn');
    
    csvInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            csvFileName.textContent = file.name;
            csvInfo.style.display = 'flex';
            validateBtn.disabled = false;
        }
    });
    
    csvClear.addEventListener('click', () => {
        csvInput.value = '';
        csvInfo.style.display = 'none';
        validateBtn.disabled = true;
    });
    
    // Drag & drop for CSV
    csvArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        csvArea.classList.add('drag-over');
    });
    
    csvArea.addEventListener('dragleave', () => {
        csvArea.classList.remove('drag-over');
    });
    
    csvArea.addEventListener('drop', (e) => {
        e.preventDefault();
        csvArea.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length > 0) {
            csvInput.files = e.dataTransfer.files;
            csvInput.dispatchEvent(new Event('change'));
        }
    });
    
    // PDF Upload
    const pdfInput = document.getElementById('pdf-file');
    const pdfArea = document.getElementById('pdf-upload-area');
    const pdfInfo = document.getElementById('pdf-file-info');
    const pdfFileName = document.getElementById('pdf-file-name');
    const pdfClear = document.getElementById('pdf-clear');
    const ocrBtn = document.getElementById('ocr-btn');
    
    pdfInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            pdfFileName.textContent = file.name;
            pdfInfo.style.display = 'flex';
            ocrBtn.disabled = false;
        }
    });
    
    pdfClear.addEventListener('click', () => {
        pdfInput.value = '';
        pdfInfo.style.display = 'none';
        ocrBtn.disabled = true;
    });
    
    // Drag & drop for PDF
    pdfArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        pdfArea.classList.add('drag-over');
    });
    
    pdfArea.addEventListener('dragleave', () => {
        pdfArea.classList.remove('drag-over');
    });
    
    pdfArea.addEventListener('drop', (e) => {
        e.preventDefault();
        pdfArea.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length > 0) {
            pdfInput.files = e.dataTransfer.files;
            pdfInput.dispatchEvent(new Event('change'));
        }
    });
}

// Button Event Handlers
function initializeButtons() {
    document.getElementById('validate-btn').addEventListener('click', handleValidation);
    document.getElementById('ocr-btn').addEventListener('click', handleOCR);
    document.getElementById('download-results').addEventListener('click', downloadResults);
    document.getElementById('validate-ocr-btn').addEventListener('click', validateOCRData);
    document.getElementById('search-btn').addEventListener('click', handleSearch);
}

// Check Backend Status
async function checkBackendStatus() {
    const statusEl = document.getElementById('backend-status');
    
    try {
        const response = await fetch(`${API_URL}/health`);
        if (response.ok) {
            statusEl.textContent = '🟢 Backend Online';
            statusEl.classList.add('online');
        } else {
            throw new Error('Backend not responding');
        }
    } catch (error) {
        statusEl.textContent = '🔴 Backend Offline';
        statusEl.classList.add('offline');
        console.error('Backend status check failed:', error);
    }
}

// Handle CSV Validation
async function handleValidation() {
    const fileInput = document.getElementById('csv-file');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    showLoading('Validating providers...');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_URL}/validate`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Validation failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        validationResults = data;
        
        displayValidationResults(data);
        logActivity('CSV Validation', `Processed ${data.summary.total} providers`);
        
    } catch (error) {
        hideLoading();
        alert(`Error: ${error.message}`);
        console.error('Validation error:', error);
    }
    
    hideLoading();
}

// Display Validation Results
function displayValidationResults(data) {
    const resultsCard = document.getElementById('validation-results');
    resultsCard.style.display = 'block';
    
    // Update stats
    document.getElementById('total-providers').textContent = data.summary.total;
    document.getElementById('valid-count').textContent = data.summary.valid;
    document.getElementById('warning-count').textContent = data.summary.warnings;
    document.getElementById('error-count').textContent = data.summary.errors;
    
    // Update progress bar
    const successRate = (data.summary.valid / data.summary.total * 100).toFixed(1);
    document.getElementById('progress-fill').style.width = `${successRate}%`;
    
    // Populate table
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';
    
    data.results.forEach(result => {
        const row = document.createElement('tr');
        
        const statusClass = result.is_valid ? 'valid' : 
                           result.issues.length > 0 ? 'warning' : 'error';
        const statusText = result.is_valid ? '✓ Valid' : 
                          result.issues.length > 0 ? '⚠ Warning' : '✗ Error';
        
        row.innerHTML = `
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>${result.provider.name || 'N/A'}</td>
            <td>${result.provider.npi || 'N/A'}</td>
            <td>${result.provider.specialty || 'N/A'}</td>
            <td>${result.validation_score.toFixed(1)}%</td>
            <td>${result.issues.length > 0 ? result.issues.join(', ') : 'None'}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Scroll to results
    resultsCard.scrollIntoView({ behavior: 'smooth' });
}

// Handle PDF OCR
async function handleOCR() {
    const fileInput = document.getElementById('pdf-file');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    showLoading('Processing PDF with OCR...');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_URL}/upload/pdf`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`OCR failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        ocrResults = data;
        
        displayOCRResults(data);
        logActivity('PDF OCR', `Processed ${file.name}`);
        
    } catch (error) {
        hideLoading();
        alert(`Error: ${error.message}`);
        console.error('OCR error:', error);
    }
    
    hideLoading();
}

// Display OCR Results
function displayOCRResults(data) {
    const resultsCard = document.getElementById('ocr-results');
    resultsCard.style.display = 'block';
    
    // Update stats
    document.getElementById('ocr-confidence').textContent = 
        `${data.ocr_confidence.toFixed(1)}%`;
    document.getElementById('ocr-pages').textContent = data.total_pages || 1;
    document.getElementById('ocr-fields').textContent = data.extracted_fields || 0;
    document.getElementById('ocr-time').textContent = 
        `${(data.processing_time || 0).toFixed(2)}s`;
    
    // Display extracted data
    const dataGrid = document.getElementById('ocr-data');
    dataGrid.innerHTML = '';
    
    const fields = {
        'NPI': data.extracted_data?.npi,
        'Name': data.extracted_data?.name,
        'Specialty': data.extracted_data?.specialty,
        'Phone': data.extracted_data?.phone,
        'Email': data.extracted_data?.email,
        'Address': data.extracted_data?.street,
        'City': data.extracted_data?.city,
        'State': data.extracted_data?.state,
        'ZIP': data.extracted_data?.zip,
        'License': data.extracted_data?.license
    };
    
    Object.entries(fields).forEach(([label, value]) => {
        if (value) {
            const item = document.createElement('div');
            item.className = 'data-item';
            item.innerHTML = `
                <label>${label}</label>
                <value>${value}</value>
            `;
            dataGrid.appendChild(item);
        }
    });
    
    // Scroll to results
    resultsCard.scrollIntoView({ behavior: 'smooth' });
}

// Validate OCR Data
async function validateOCRData() {
    if (!ocrResults) {
        alert('No OCR data to validate');
        return;
    }
    
    showLoading('Validating extracted data...');
    
    try {
        const response = await fetch(`${API_URL}/api/v1/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(ocrResults.extracted_data)
        });
        
        if (!response.ok) {
            throw new Error(`Validation failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Show results in a simple format
        const resultsText = `
Validation Results:
- Valid: ${data.is_valid ? 'Yes' : 'No'}
- Confidence: ${data.validation_score.toFixed(1)}%
- Issues: ${data.issues.length > 0 ? data.issues.join(', ') : 'None'}
        `;
        
        alert(resultsText);
        logActivity('OCR Validation', `Confidence: ${data.validation_score.toFixed(1)}%`);
        
    } catch (error) {
        hideLoading();
        alert(`Error: ${error.message}`);
        console.error('Validation error:', error);
    }
    
    hideLoading();
}

// Handle Search
async function handleSearch() {
    const query = document.getElementById('search-input').value;
    const specialty = document.getElementById('filter-specialty').value;
    const status = document.getElementById('filter-status').value;
    
    if (!query && !specialty && !status) {
        alert('Please enter search criteria');
        return;
    }
    
    showLoading('Searching providers...');
    
    try {
        // Build query parameters
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (specialty) params.append('specialty', specialty);
        if (status) params.append('status', status);
        
        const response = await fetch(`${API_URL}/api/v1/search?${params}`);
        
        if (!response.ok) {
            throw new Error(`Search failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        displaySearchResults(data);
        
    } catch (error) {
        hideLoading();
        alert(`Error: ${error.message}`);
        console.error('Search error:', error);
    }
    
    hideLoading();
}

// Display Search Results
function displaySearchResults(data) {
    const resultsCard = document.getElementById('search-results');
    const tbody = document.getElementById('search-results-body');
    
    resultsCard.style.display = 'block';
    tbody.innerHTML = '';
    
    if (!data.results || data.results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No providers found</td></tr>';
        return;
    }
    
    data.results.forEach(provider => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${provider.name || 'N/A'}</td>
            <td>${provider.npi || 'N/A'}</td>
            <td>${provider.specialty || 'N/A'}</td>
            <td>${provider.phone || 'N/A'}</td>
            <td><span class="status-badge ${provider.status || 'valid'}">${provider.status || 'Valid'}</span></td>
        `;
        tbody.appendChild(row);
    });
}

// Download Results as JSON
function downloadResults() {
    if (!validationResults) {
        alert('No results to download');
        return;
    }
    
    const dataStr = JSON.stringify(validationResults, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `medguard_results_${Date.now()}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
}

// Log Activity
function logActivity(action, details) {
    const activityLog = document.getElementById('activity-log');
    
    // Remove "no data" message if it exists
    const noData = activityLog.querySelector('.no-data');
    if (noData) {
        noData.remove();
    }
    
    const item = document.createElement('div');
    item.className = 'activity-item';
    
    const now = new Date().toLocaleString();
    item.innerHTML = `
        <strong>${action}</strong><br>
        ${details}<br>
        <span class="activity-time">${now}</span>
    `;
    
    activityLog.insertBefore(item, activityLog.firstChild);
    
    // Update stats
    updateStats();
}

// Update Statistics
function updateStats() {
    // This would normally come from backend API
    // For now, just increment based on activity
    const statTotal = document.getElementById('stat-total');
    const current = parseInt(statTotal.textContent) || 0;
    statTotal.textContent = current + 1;
}

// Loading Overlay
function showLoading(text = 'Processing...') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}
