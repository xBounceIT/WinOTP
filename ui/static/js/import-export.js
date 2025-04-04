// Export tokens to file
async function exportTokens() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }

        // Export tokens using native file dialog
        const result = await window.pywebview.api.export_tokens_to_json();
        
        if (result.status === 'success') {
            showNotification(result.message, 'success');
        } else if (result.status === 'cancelled') {
            // User cancelled the file dialog, no need to show notification
            console.log('Export cancelled by user');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error exporting tokens: ' + error, 'error');
    }
}

// Import from WinOTP
function importFromWinOTP() {
    // Create a hidden file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);
    
    // Add event listener for file selection
    fileInput.addEventListener('change', async function(event) {
        const file = event.target.files[0];
        if (!file) {
            document.body.removeChild(fileInput);
            return;
        }
        
        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                if (!window.pywebview || !window.pywebview.api) {
                    console.error("pywebview API not available");
                    showNotification('Error: API not available', 'error');
                    document.body.removeChild(fileInput);
                    return;
                }
                
                // Call API to import tokens
                const result = await window.pywebview.api.import_tokens_from_json(e.target.result);
                if (result.status === 'success') {
                    showNotification(result.message, 'success');
                    // Go back to main page to show the imported tokens
                    showMainPage();
                    loadTokens();
                } else {
                    showNotification(result.message, 'error');
                }
            } catch (error) {
                showNotification('Error importing tokens: ' + error, 'error');
            }
            
            document.body.removeChild(fileInput);
        };
        
        reader.readAsText(file);
    });
    
    // Trigger file selection dialog
    fileInput.click();
}

// Import from 2FAS
function importFrom2FAS() {
    // Create a hidden file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.2fas'; // Accept .2fas files
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    // Add event listener for file selection
    fileInput.addEventListener('change', async function(event) {
        const file = event.target.files[0];
        if (!file) {
            if (document.body.contains(fileInput)) { // Check if exists before removing
                 document.body.removeChild(fileInput);
            }
            return;
        }

        const reader = new FileReader();
        reader.onload = async function(e) {
            // --- Show Progress UI ---
            console.log("Showing import progress UI");
            document.getElementById('importTokensPage').style.display = 'none'; // Hide import options
            const progressPage = document.getElementById('importProgressPage');
            if(progressPage) {
                progressPage.style.display = 'block'; // Show progress page
                // Reset progress bar/text initially
                updateImportProgress(0, '?', 0); 
            } else {
                 console.error("Import progress page element not found!");
                 // Don't proceed if UI is broken
                 if (document.body.contains(fileInput)) {
                     document.body.removeChild(fileInput);
                 }
                 showNotification("UI Error: Cannot display import progress.", "error");
                 return;
            }

            try {
                if (!window.pywebview || !window.pywebview.api) {
                    console.error("pywebview API not available");
                    throw new Error("API not available"); // Throw error to be caught below
                }

                // --- Call API (now reports progress) ---
                console.log("Calling backend import_tokens_from_2fas");
                const result = await window.pywebview.api.import_tokens_from_2fas(e.target.result);
                console.log("Backend import finished, result:", result);

                // --- Hide Progress UI ---
                if(progressPage) progressPage.style.display = 'none';

                // --- Handle Result ---
                showNotification(result.message || 'Import finished', result.status === 'success' ? 'success' : (result.status === 'warning' ? 'warning' : 'error'));

                if (result.status === 'success') {
                    // Go back to main page to show the imported tokens
                    console.log("Import successful, showing main page.");
                    showMainPage();
                    await loadTokens(); // Ensure tokens are reloaded AFTER navigation
                } else {
                    // Go back to the import selection page on failure/warning
                    console.log("Import failed or warning, showing import tokens page.");
                    showImportTokensPage();
                }
            } catch (error) {
                 console.error("Error during 2FAS import process:", error);
                // --- Hide Progress UI on error ---
                 if(progressPage) progressPage.style.display = 'none';
                 showNotification('Error importing from 2FAS: ' + (error.message || error), 'error');
                 // Go back to the import selection page on error
                 showImportTokensPage();
            } finally {
                // Clean up the file input
                if (document.body.contains(fileInput)) {
                    document.body.removeChild(fileInput);
                }
            }
        };

        reader.readAsText(file);
    });

    // Trigger file selection dialog
    fileInput.click();
}

// Import from Authenticator Plugin
function importFromAuthenticatorPlugin() {
    // Create a hidden file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.txt'; // Accept .txt files from Authenticator Plugin
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    // Add event listener for file selection
    fileInput.addEventListener('change', async function(event) {
        const file = event.target.files[0];
        if (!file) {
            if (document.body.contains(fileInput)) {
                document.body.removeChild(fileInput);
            }
            return;
        }

        const reader = new FileReader();
        reader.onload = async function(e) {
            // Show Progress UI
            document.getElementById('importTokensPage').style.display = 'none';
            const progressPage = document.getElementById('importProgressPage');
            if(progressPage) {
                progressPage.style.display = 'block';
                updateImportProgress(0, '?', 0);
            } else {
                console.error("Import progress page element not found!");
                if (document.body.contains(fileInput)) {
                    document.body.removeChild(fileInput);
                }
                showNotification("UI Error: Cannot display import progress.", "error");
                return;
            }

            try {
                if (!window.pywebview || !window.pywebview.api) {
                    console.error("pywebview API not available");
                    throw new Error("API not available");
                }

                // Call API for authenticator plugin import
                console.log("Calling backend import_tokens_from_authenticator_plugin");
                const result = await window.pywebview.api.import_tokens_from_authenticator_plugin(e.target.result);
                console.log("Backend import finished, result:", result);

                // Hide Progress UI
                if(progressPage) progressPage.style.display = 'none';

                // Handle Result
                showNotification(result.message || 'Import finished', result.status === 'success' ? 'success' : (result.status === 'warning' ? 'warning' : 'error'));

                if (result.status === 'success') {
                    // Go back to main page to show the imported tokens
                    console.log("Import successful, showing main page.");
                    showMainPage();
                    await loadTokens();
                } else {
                    // Go back to the import selection page on failure/warning
                    console.log("Import failed or warning, showing import tokens page.");
                    showImportTokensPage();
                }
            } catch (error) {
                console.error("Error during Authenticator Plugin import process:", error);
                if(progressPage) progressPage.style.display = 'none';
                showNotification('Error importing from Authenticator Plugin: ' + (error.message || error), 'error');
                showImportTokensPage();
            } finally {
                if (document.body.contains(fileInput)) {
                    document.body.removeChild(fileInput);
                }
            }
        };

        reader.readAsText(file);
    });

    // Trigger file selection dialog
    fileInput.click();
}

// Import from Google Authenticator
function importFromGoogleAuth() {
    // Switch to Google Auth import page
    document.getElementById('importTokensPage').style.display = 'none';
    document.getElementById('googleAuthImportPage').style.display = 'block';
    
    // Initialize and load the back icon
    loadBackIconForGoogleAuth();
    
    // Initialize QR scanner
    initializeGoogleAuthQrScanner();
}

// Initialize Google Auth QR scanner
function initializeGoogleAuthQrScanner() {
    try {
        if (currentQRScanner) {
            currentQRScanner.stop();
            currentQRScanner = null;
        }
        
        const qrScannerArea = document.getElementById('qrScannerArea');
        if (!qrScannerArea) {
            console.error('QR scanner area not found');
            return;
        }
        
        // Set up QR scanner
        const setupQrScanner = async () => {
            try {
                if (!window.pywebview || !window.pywebview.api) {
                    console.error("pywebview API not available");
                    showNotification('Error: API not available', 'error');
                    return;
                }
                
                // Call backend to initialize QR scanning
                await window.pywebview.api.initialize_google_auth_qr_scanner();
                
                // Show file upload button or other UI elements as needed
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = 'image/*';
                fileInput.id = 'googleAuthQrInput';
                fileInput.style.display = 'none';
                document.body.appendChild(fileInput);
                
                // Create a visible button to trigger file selection
                const uploadButton = document.createElement('button');
                uploadButton.className = 'btn';
                uploadButton.textContent = 'Upload QR Code Image';
                uploadButton.addEventListener('click', function() {
                    fileInput.click();
                });
                
                qrScannerArea.innerHTML = '';
                qrScannerArea.appendChild(uploadButton);
                
                // Handle file selection
                fileInput.addEventListener('change', async function(event) {
                    const file = event.target.files[0];
                    if (!file) return;
                    
                    try {
                        // Show loading indicator
                        qrScannerArea.innerHTML = '<div class="loading-spinner"></div><p>Processing QR code...</p>';
                        
                        // Read the file as a data URL
                        const reader = new FileReader();
                        reader.onload = async function(e) {
                            try {
                                // Call API to scan QR code with the data URL
                                const result = await window.pywebview.api.scan_google_auth_qr(e.target.result);
                                if (result.status === 'success') {
                                    // Show success message with icon
                                    qrScannerArea.innerHTML = `
                                        <div class="google-auth-success">
                                            <span class="success-icon">✔</span> <!-- Simple checkmark icon -->
                                            QR Code scanned successfully! ${result.tokens_count} tokens found.
                                        </div>`;
                                    
                                    // Reset file input
                                    fileInput.value = '';
                                    
                                    // Show another upload button for adding more QR codes
                                    const anotherButton = document.createElement('button');
                                    anotherButton.className = 'btn';
                                    anotherButton.textContent = 'Scan Another QR Code';
                                    anotherButton.addEventListener('click', function() {
                                        setupQrScanner();
                                    });
                                    qrScannerArea.appendChild(anotherButton);
                                } else {
                                    // Show error message
                                    qrScannerArea.innerHTML = `<div class="error-message">${result.message}</div>`;
                                    
                                    // Show retry button
                                    const retryButton = document.createElement('button');
                                    retryButton.className = 'btn';
                                    retryButton.textContent = 'Try Again';
                                    retryButton.addEventListener('click', function() {
                                        setupQrScanner();
                                    });
                                    qrScannerArea.appendChild(retryButton);
                                }
                            } catch (error) {
                                console.error('Error calling API to scan QR code:', error);
                                qrScannerArea.innerHTML = `<div class="error-message">Error scanning QR code: ${error.message || error}</div>`;
                                
                                // Show retry button
                                const retryButton = document.createElement('button');
                                retryButton.className = 'btn';
                                retryButton.textContent = 'Try Again';
                                retryButton.addEventListener('click', function() {
                                    setupQrScanner();
                                });
                                qrScannerArea.appendChild(retryButton);
                            }
                        };
                        
                        reader.readAsDataURL(file);
                    } catch (error) {
                        console.error('Error reading file:', error);
                        qrScannerArea.innerHTML = `<div class="error-message">Error reading file</div>`;
                    }
                });
            } catch (error) {
                console.error('Error setting up QR scanner:', error);
                qrScannerArea.innerHTML = `<div class="error-message">Error initializing QR scanner</div>`;
            }
        };
        
        setupQrScanner();
    } catch (error) {
        console.error('Error initializing Google Auth QR scanner:', error);
        showNotification('Error initializing QR scanner', 'error');
    }
}

// Back from Google Auth import
function backFromGoogleAuth() {
    document.getElementById('googleAuthImportPage').style.display = 'none';
    document.getElementById('importTokensPage').style.display = 'block';
    
    // Clean up QR scanner if active
    if (currentQRScanner) {
        currentQRScanner.stop();
        currentQRScanner = null;
    }
}

// Finish Google Auth import
async function finishGoogleAuthImport() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        // Call API to complete the import
        const result = await window.pywebview.api.finish_google_auth_import();
        if (result.status === 'success') {
            // Hide Google Auth import page first
            document.getElementById('googleAuthImportPage').style.display = 'none';
            
            // Go back to main page to show the imported tokens without showing success notification
            showMainPage();
            loadTokens();
        } else {
            showNotification(result.message || 'No tokens were imported', result.status === 'warning' ? 'warning' : 'error');
            // Stay on the current page
        }
    } catch (error) {
        console.error('Error finishing Google Auth import:', error);
        showNotification('Error finishing import: ' + error, 'error');
    }
}

// Initialize QR scanner for adding tokens
async function initializeQrScanner() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        // Update the UI to reflect the new screen capture functionality
        const permissionInfo = document.getElementById('cameraPermissionInfo');
        const startScanBtn = document.getElementById('startScanBtn');
        
        if (permissionInfo) {
            permissionInfo.innerHTML = '<p>Click "Capture Screen Region" to select and scan a portion of your screen containing a QR code.</p>';
        }
        
        if (startScanBtn) {
            startScanBtn.disabled = false;
            startScanBtn.textContent = 'Capture Screen Region';
            startScanBtn.classList.add('primary');
            
            // Update the click handler to start screen capture
            startScanBtn.onclick = startScreenCapture;
            
            // Immediately start screen capture without requiring a second click
            startScreenCapture();
        }
    } catch (error) {
        console.error('Error initializing QR scanner:', error);
        const permissionInfo = document.getElementById('cameraPermissionInfo');
        const startScanBtn = document.getElementById('startScanBtn');
        
        if (permissionInfo) {
            permissionInfo.innerHTML = '<p class="error">Error initializing: ' + error + '</p>';
        }
        if (startScanBtn) {
            startScanBtn.disabled = false;
            startScanBtn.textContent = 'Try Again';
        }
    }
}

// Start screen capture for QR scanning
async function startScreenCapture() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        const scanQrTab = document.getElementById('scanQr');
        const permissionInfo = document.getElementById('cameraPermissionInfo');
        const startScanBtn = document.getElementById('startScanBtn');
        
        // Show loading state
        if (permissionInfo) {
            permissionInfo.innerHTML = '<p>Preparing to capture screen region...</p>';
        }
        if (startScanBtn) {
            startScanBtn.disabled = true;
            startScanBtn.textContent = 'Preparing...';
        }
        
        // Update UI to show that capture is in progress
        if (scanQrTab) {
            // Create loading indicator
            const loadingContainer = document.createElement('div');
            loadingContainer.id = 'qrCaptureContainer';
            loadingContainer.style.width = '100%';
            loadingContainer.style.maxWidth = '400px';
            loadingContainer.style.margin = '0 auto';
            loadingContainer.style.textAlign = 'center';
            loadingContainer.style.padding = '20px';
            
            const loadingSpinner = document.createElement('div');
            loadingSpinner.className = 'loading-spinner';
            loadingSpinner.style.margin = '0 auto 20px auto';
            loadingContainer.appendChild(loadingSpinner);
            
            const statusText = document.createElement('p');
            statusText.id = 'captureStatusText';
            statusText.textContent = 'Select the region of your screen containing the QR code...';
            loadingContainer.appendChild(statusText);
            
            // Create cancel button
            const cancelButton = document.createElement('button');
            cancelButton.className = 'btn';
            cancelButton.textContent = 'Cancel';
            cancelButton.style.margin = '10px auto';
            cancelButton.style.display = 'block';
            cancelButton.onclick = resetQrScannerUI;
            
            // Replace content
            scanQrTab.innerHTML = '';
            scanQrTab.appendChild(loadingContainer);
            scanQrTab.appendChild(cancelButton);
        }
        
        // Call API to capture screen region and scan for QR code
        const result = await window.pywebview.api.capture_screen_for_qr();
        
        // Update status based on the result
        if (result.status === 'success') {
            // QR code found, process it
            const tokenData = result.data;
            const addResult = await window.pywebview.api.add_token(tokenData);
            
            if (addResult.status === 'success') {
                showNotification(addResult.message, 'success');
                showMainPage();
                loadTokens();
            } else {
                showNotification(addResult.message, 'error');
                resetQrScannerUI();
            }
        } else if (result.status === 'cancelled') {
            // User cancelled the selection
            showNotification('Screen capture cancelled', 'info');
            resetQrScannerUI();
        } else {
            // Error occurred
            showNotification(result.message, 'error');
            resetQrScannerUI();
        }
    } catch (error) {
        console.error('Error capturing screen region:', error);
        showNotification('Error capturing screen: ' + error, 'error');
        resetQrScannerUI();
    }
}

// Reset the QR scanner UI to its initial state
function resetQrScannerUI() {
    const scanQrTab = document.getElementById('scanQr');
    if (scanQrTab) {
        // Restore original content
        scanQrTab.innerHTML = `
            <div class="info-box" id="cameraPermissionInfo" style="margin-bottom: 20px;">
                <p>Click "Capture Screen Region" to select and scan a portion of your screen containing a QR code.</p>
            </div>
            <div class="form-actions">
                <button class="btn" id="startScanBtn">Capture Screen Region</button>
                <button class="btn" id="uploadQrBtn">Upload QR Image</button>
                <input type="file" id="qrFileInput" accept="image/*" style="display: none;">
            </div>
        `;
        
        // Restore event listeners
        document.getElementById('startScanBtn').addEventListener('click', startScreenCapture);
        document.getElementById('uploadQrBtn').addEventListener('click', function() {
            document.getElementById('qrFileInput').click();
        });
        document.getElementById('qrFileInput').addEventListener('change', handleQrFileUpload);
    }
}

// Poll for QR scan results
function startQrResultPolling() {
    let polling = true;
    
    const pollForResult = async () => {
        if (!polling) return;
        
        try {
            if (!window.pywebview || !window.pywebview.api) {
                console.error("pywebview API not available");
                polling = false;
                return;
            }
            
            // Call API to check for QR code results
            const result = await window.pywebview.api.get_qr_scan_result();
            
            if (result.status === 'success' && result.data) {
                // QR code detected, handle it
                polling = false;
                
                // Stop the scanner
                await window.pywebview.api.stop_qr_scanning();
                
                // Process the token data
                const tokenData = result.data;
                const addResult = await window.pywebview.api.add_token(tokenData);
                
                if (addResult.status === 'success') {
                    showNotification(addResult.message, 'success');
                    showMainPage();
                    loadTokens();
                } else {
                    showNotification(addResult.message, 'error');
                    // Reset the scanner UI
                    stopQrScanning();
                }
            } else {
                // Keep polling
                setTimeout(pollForResult, 500);
            }
        } catch (error) {
            console.error('Error polling for QR results:', error);
            polling = false;
            showNotification('Error scanning QR code', 'error');
            stopQrScanning();
        }
    };
    
    // Start polling
    pollForResult();
} 