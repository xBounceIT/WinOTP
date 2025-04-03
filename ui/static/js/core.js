// Global variables
let tokens = [];
let searchTerm = '';
let sortAscending = true;
let isAuthenticated = false;
let updateInterval;
let apiCheckInterval;
let authCheckInterval;  // Interval for checking auth timeout
let apiReady = false; // Flag to track API readiness
let pagesLoaded = false; // Flag to track if pages are loaded
let currentQRScanner = null; // QR scanner instance

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Wait for API and pages to be ready
    waitForApi();
});

// Listen for pages being loaded
document.addEventListener('allPagesLoaded', function() {
    console.log("All pages loaded");
    pagesLoaded = true;
    
    console.log("Setting up event listeners for all elements");
    
    // Set up event listeners for elements in the main page
    const settingsBtn = document.getElementById('settingsBtn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', showSettingsPage);
    }
    
    const addTokenBtn = document.getElementById('addTokenBtn');
    if (addTokenBtn) {
        addTokenBtn.addEventListener('click', showAddTokenPage);
    }
    
    const toggleSortBtn = document.getElementById('toggleSortBtn');
    if (toggleSortBtn) {
        toggleSortBtn.addEventListener('click', toggleSortOrder);
    }
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', async (e) => {
            searchTerm = e.target.value.toLowerCase();
            const clearSearchBtn = document.getElementById('clearSearchBtn');
            if (clearSearchBtn) {
                clearSearchBtn.style.display = searchTerm ? 'block' : 'none';
            }
            await renderTokens();
        });
    }
    
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', async () => {
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.value = '';
                searchTerm = '';
                clearSearchBtn.style.display = 'none';
                await renderTokens();
            }
        });
    }
    
    // Set up event listeners for elements in dynamically loaded pages
    const backToMainBtn = document.getElementById('backToMainBtn');
    if (backToMainBtn) {
        backToMainBtn.addEventListener('click', showMainPage);
    }
    
    const backFromAddTokenBtn = document.getElementById('backFromAddTokenBtn');
    if (backFromAddTokenBtn) {
        backFromAddTokenBtn.addEventListener('click', showMainPage);
    }
    
    const aboutBtnSettings = document.getElementById('aboutBtnSettings'); 
    if (aboutBtnSettings) {
        aboutBtnSettings.addEventListener('click', showAboutPage);
    }
    
    const backFromAboutBtn = document.getElementById('backFromAboutBtn');
    if (backFromAboutBtn) {
        backFromAboutBtn.addEventListener('click', showSettingsPage);
    }

    const uploadQrBtn = document.getElementById('uploadQrBtn');
    if (uploadQrBtn) {
        uploadQrBtn.addEventListener('click', function() {
            document.getElementById('qrFileInput').click();
        });
    }
    
    // Import tokens button in settings
    const importTokensBtn = document.getElementById('importTokensBtn');
    if (importTokensBtn) {
        importTokensBtn.addEventListener('click', showImportTokensPage);
    }
    
    // Back button from import page
    const backFromImportBtn = document.getElementById('backFromImportBtn');
    if (backFromImportBtn) {
        backFromImportBtn.addEventListener('click', showSettingsPage);
    }
    
    // Import buttons
    const importFromWinOTPBtn = document.getElementById('importFromWinOTPBtn');
    if (importFromWinOTPBtn) {
        importFromWinOTPBtn.addEventListener('click', importFromWinOTP);
    }
    
    const importFrom2FASBtn = document.getElementById('importFrom2FASBtn');
    if (importFrom2FASBtn) {
        importFrom2FASBtn.addEventListener('click', importFrom2FAS);
    }
    
    const importFromAuthenticatorPluginBtn = document.getElementById('importFromAuthenticatorPluginBtn');
    if (importFromAuthenticatorPluginBtn) {
        importFromAuthenticatorPluginBtn.addEventListener('click', importFromAuthenticatorPlugin);
    }
    
    const importFromGoogleAuthBtn = document.getElementById('importFromGoogleAuthBtn');
    if (importFromGoogleAuthBtn) {
        importFromGoogleAuthBtn.addEventListener('click', importFromGoogleAuth);
    }
    
    // App protection settings
    const appProtectionBtn = document.getElementById('appProtectionBtn');
    if (appProtectionBtn) {
        appProtectionBtn.addEventListener('click', showAppProtectionPage);
    }
    
    const backFromProtectionBtn = document.getElementById('backFromProtectionBtn');
    if (backFromProtectionBtn) {
        backFromProtectionBtn.addEventListener('click', showSettingsPage);
    }
    
    const setPinBtn = document.getElementById('setPinBtn');
    if (setPinBtn) {
        setPinBtn.addEventListener('click', setPin);
    }
    
    const setPasswordBtn = document.getElementById('setPasswordBtn');
    if (setPasswordBtn) {
        setPasswordBtn.addEventListener('click', setPassword);
    }
    
    const disableProtectionBtn = document.getElementById('disableProtectionBtn');
    if (disableProtectionBtn) {
        disableProtectionBtn.addEventListener('click', disableProtection);
    }
    
    // Login page
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
        loginBtn.addEventListener('click', login);
    }
    
    const loginCredential = document.getElementById('loginCredential');
    if (loginCredential) {
        loginCredential.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                login();
            }
        });
    }
    
    // Set up tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and tab contents
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active class to selected tab and tab content
            this.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Google Auth import page
    const backFromGoogleAuthBtn = document.getElementById('backFromGoogleAuthBtn');
    if (backFromGoogleAuthBtn) {
        backFromGoogleAuthBtn.addEventListener('click', backFromGoogleAuth);
    }
    
    const finishGoogleAuthImportBtn = document.getElementById('finishGoogleAuthImportBtn');
    if (finishGoogleAuthImportBtn) {
        finishGoogleAuthImportBtn.addEventListener('click', finishGoogleAuthImport);
    }
    
    // Add event listener for start scan button
    const startScanBtn = document.getElementById('startScanBtn');
    if (startScanBtn) {
        startScanBtn.addEventListener('click', initializeQrScanner);
    }
    
    // Update page elements
    const backFromUpdateBtn = document.getElementById('backFromUpdateBtn');
    const cancelUpdateBtn = document.getElementById('cancelUpdateBtn');
    
    if (backFromUpdateBtn) {
        backFromUpdateBtn.addEventListener('click', function() {
            document.getElementById('updatePage').style.display = 'none';
            showMainPage();
        });
    }
    
    if (cancelUpdateBtn) {
        cancelUpdateBtn.addEventListener('click', function() {
            document.getElementById('updatePage').style.display = 'none';
            showMainPage();
        });
    }
    
    const downloadUpdateBtn = document.getElementById('downloadUpdateBtn');
    if (downloadUpdateBtn) {
        downloadUpdateBtn.addEventListener('click', downloadUpdate);
    }
    
    // Start periodic auth check
    startAuthCheck();

    // Add the event listeners that were previously outside
    const qrFileInput = document.getElementById('qrFileInput');
    if (qrFileInput) {
        qrFileInput.addEventListener('change', handleQrFileUpload);
    }

    const saveTokenBtn = document.getElementById('saveTokenBtn');
    if (saveTokenBtn) {
        saveTokenBtn.addEventListener('click', saveManualToken);
    }

    const saveUriTokenBtn = document.getElementById('saveUriTokenBtn');
    if (saveUriTokenBtn) {
        saveUriTokenBtn.addEventListener('click', saveUriToken);
    }

    const exportTokensBtn = document.getElementById('exportTokensBtn');
    if (exportTokensBtn) {
        exportTokensBtn.addEventListener('click', exportTokens);
    }

    // Load settings
    loadMinimizeToTraySetting();
    loadUpdateCheckerSetting();
    loadNextCodePreviewSetting();
});

// Wait for API to be ready
function waitForApi() {
    console.log("Waiting for API and pages to be ready...");
    
    // Create a loading element if it doesn't exist
    if (!document.getElementById('loadingIndicator')) {
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loadingIndicator';
        loadingDiv.style.position = 'fixed';
        loadingDiv.style.top = '0';
        loadingDiv.style.left = '0';
        loadingDiv.style.width = '100%';
        loadingDiv.style.height = '100%';
        loadingDiv.style.display = 'flex';
        loadingDiv.style.flexDirection = 'column';
        loadingDiv.style.alignItems = 'center';
        loadingDiv.style.justifyContent = 'center';
        loadingDiv.style.backgroundColor = 'var(--background-color)';
        loadingDiv.style.zIndex = '9999';
        
        const loadingText = document.createElement('h2');
        loadingText.textContent = 'Loading WinOTP...';
        loadingText.style.marginBottom = '20px';
        
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        spinner.style.width = '40px';
        spinner.style.height = '40px';
        spinner.style.border = '4px solid var(--border-color)';
        spinner.style.borderTop = '4px solid var(--primary-color)';
        spinner.style.borderRadius = '50%';
        spinner.style.animation = 'spin 1s linear infinite';
        
        // Add keyframes for spinner animation
        const style = document.createElement('style');
        style.textContent = '@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }';
        document.head.appendChild(style);
        
        loadingDiv.appendChild(loadingText);
        loadingDiv.appendChild(spinner);
        document.body.appendChild(loadingDiv);
    }
    
    // Check if both API and pages are available
    const checkReadiness = () => {
        if (window.pywebview && window.pywebview.api && pagesLoaded) {
            console.log("API and pages are ready!");
            apiReady = true;
            
            // Preload all icons as soon as the API is ready
            loadAllIcons().then(() => {
                console.log("Icons preloaded successfully");
            }).catch(error => {
                console.error("Error preloading icons:", error);
            });
            
            // Remove loading indicator
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                document.body.removeChild(loadingIndicator);
            }
            
            // Check authentication status
            checkAuthStatus();
        } else {
            console.log("Still waiting for API and pages...");
            setTimeout(checkReadiness, 100);
        }
    };
    
    // Start checking for readiness
    checkReadiness();
}

// Helper function to wait for pywebview API
function waitForPywebviewApi() {
    return new Promise((resolve, reject) => {
        const checkApi = () => {
            if (window.pywebview && window.pywebview.api) {
                resolve();
            } else {
                setTimeout(checkApi, 100);
            }
        };
        checkApi();
    });
}

// Check for updates on page load
async function checkUpdatesOnLoad() {
    try {
        // Wait until API is ready before proceeding
        if (!apiReady) {
            console.log("API not ready yet for update check, will retry when ready or during login.");
            return;
        }

        // Check if update checking is enabled in settings
        const updateCheckEnabled = await window.pywebview.api.get_setting('update_check_enabled');
        // Default to true if undefined
        if (updateCheckEnabled === undefined || updateCheckEnabled) {
            if (apiReady) {
                const updateInfo = await window.pywebview.api.check_for_updates();
                if (updateInfo && updateInfo.available) {
                    console.log("Update available on load, showing update button...");
                    showUpdateNotification(updateInfo);
                }
            }
        } else {
            console.log("Update check is disabled in settings.");
        }
    } catch (error) {
        console.error('Error checking for updates on load:', error);
    }
}

// Function to show update notification
function showUpdateNotification(updateInfo) {
    console.log("showUpdateNotification called with:", updateInfo);
    if (!updateInfo || !updateInfo.available) {
        console.log("No update available or invalid info.");
        return;
    }

    const updateButton = document.getElementById('updateAvailableBtn');
    if (!updateButton) {
        console.error("Update button element not found!");
        return;
    }

    // Make the button visible
    updateButton.style.display = 'inline-block';

    // Store update info in a data attribute for later use
    updateButton.setAttribute('data-version', updateInfo.version);
    updateButton.setAttribute('data-notes', encodeURIComponent(updateInfo.notes));
    updateButton.setAttribute('data-download-url', updateInfo.download_url || '');
    updateButton.setAttribute('data-release-date', updateInfo.release_date || '');

    // Remove any existing listener to avoid duplicates
    updateButton.removeEventListener('click', showUpdatePage);
    
    // Add click listener to show the update page
    updateButton.addEventListener('click', showUpdatePage);
}

// Function to show the update page with release notes
function showUpdatePage() {
    // Hide all other pages
    hideAllPages();
    
    // Get the update information from the button's data attributes
    const updateVersion = document.getElementById('updateAvailableBtn').getAttribute('data-version');
    const updateNotes = decodeURIComponent(document.getElementById('updateAvailableBtn').getAttribute('data-notes'));
    const releaseDate = document.getElementById('updateAvailableBtn').getAttribute('data-release-date');
    
    // Format the version display with release date if available
    let versionDisplay = `New Version: ${updateVersion}`;
    if (releaseDate && releaseDate !== 'Unknown date') {
        try {
            const date = new Date(releaseDate);
            versionDisplay += ` (${date.toLocaleDateString()})`;
        } catch (error) {
            console.error("Error formatting date:", error);
        }
    }
    
    // Update the page with the version and notes
    document.getElementById('updateVersion').textContent = versionDisplay;
    document.getElementById('update-notes').textContent = updateNotes || 'No release notes available.';
    
    // Remove any existing event listeners to prevent duplicates
    const backButton = document.getElementById('backFromUpdateBtn');
    const cancelButton = document.getElementById('cancelUpdateBtn');
    const downloadButton = document.getElementById('downloadUpdateBtn');
    
    // Clone and replace elements to remove all event listeners
    if (backButton) {
        const newBackButton = backButton.cloneNode(true);
        backButton.parentNode.replaceChild(newBackButton, backButton);
        newBackButton.addEventListener('click', function() {
            // Hide the update page first, then show main page
            document.getElementById('updatePage').style.display = 'none';
            showMainPage();
        });
    }
    
    if (cancelButton) {
        const newCancelButton = cancelButton.cloneNode(true);
        cancelButton.parentNode.replaceChild(newCancelButton, cancelButton);
        newCancelButton.addEventListener('click', function() {
            // Hide the update page first, then show main page
            document.getElementById('updatePage').style.display = 'none';
            showMainPage();
        });
    }
    
    if (downloadButton) {
        const newDownloadButton = downloadButton.cloneNode(true);
        downloadButton.parentNode.replaceChild(newDownloadButton, downloadButton);
        newDownloadButton.addEventListener('click', downloadUpdate);
    }
    
    // Load the back icon
    loadIconForElement('backFromUpdateIcon', 'back_arrow.png');
    
    // Show the update page
    document.getElementById('updatePage').style.display = 'block';
}

// Function to download the update
async function downloadUpdate() {
    // Get the download URL from the button's data attribute
    const downloadUrl = document.getElementById('updateAvailableBtn').getAttribute('data-download-url');
    
    // If no download URL is available, show error
    if (!downloadUrl) {
        showNotification('No download URL available. Please try again later.', 'error');
        return;
    }
    
    try {
        // Show loading notification
        showNotification('Downloading update...', 'info');
        
        // Use the API to download the file
        const result = await window.pywebview.api.download_update_file(downloadUrl);
        
        if (result.status === 'success') {
            showNotification('Update downloaded successfully', 'success');
            
            // Format the file path for better readability
            const filePath = result.download_path;
            const fileName = filePath.split('\\').pop();
            
            // Show additional information
            const downloadPathInfo = document.createElement('div');
            downloadPathInfo.className = 'update-download-info';
            downloadPathInfo.innerHTML = `
                <p><strong>Download Complete</strong></p>
                <p>File: <span class="file-path">${fileName}</span></p>
                <p>Location: <span class="file-path">${filePath}</span></p>
                <p>Please close this application before running the new version.</p>
            `;
            
            // Replace the info-box content
            const infoBox = document.querySelector('#updatePage .info-box');
            if (infoBox) {
                infoBox.innerHTML = '';
                infoBox.appendChild(downloadPathInfo);
            }
            
            // Change download button text
            document.getElementById('downloadUpdateBtn').textContent = 'Downloaded';
            document.getElementById('downloadUpdateBtn').disabled = true;
        } else if (result.is_release_page) {
            // Handle release page URL (not a direct file download)
            showNotification('Opening release page in browser...', 'info');
            
            // Open the URL in the browser
            await window.pywebview.api.open_url(result.url);
            
            // Show fallback message
            const downloadPathInfo = document.createElement('div');
            downloadPathInfo.className = 'update-download-info';
            downloadPathInfo.innerHTML = `
                <p><strong>Manual Download Required</strong></p>
                <p>The release page has been opened in your browser.</p>
                <p>Please download the latest version from the GitHub releases page and run it after closing this application.</p>
            `;
            
            // Replace the info-box content
            const infoBox = document.querySelector('#updatePage .info-box');
            if (infoBox) {
                infoBox.innerHTML = '';
                infoBox.appendChild(downloadPathInfo);
            }
            
            // Change download button text
            document.getElementById('downloadUpdateBtn').textContent = 'Open in Browser';
        } else {
            showNotification(result.message || 'Download failed', 'error');
        }
    } catch (error) {
        console.error("Error downloading update:", error);
        showNotification('Failed to download update. Please try again later.', 'error');
    }
} 