// Global variables
let tokens = [];
let searchTerm = '';
let sortAscending = true;
let isAuthenticated = false;
let updateInterval;
let apiCheckInterval;
let authCheckInterval;  // Interval for checking auth timeout
let apiReady = false; // Flag to track API readiness
let currentQRScanner = null; // QR scanner instance

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Wait for API to be ready
    waitForApi();
    
    // Set up event listeners
    document.getElementById('settingsBtn').addEventListener('click', showSettingsPage);
    document.getElementById('backToMainBtn').addEventListener('click', showMainPage);
    document.getElementById('addTokenBtn').addEventListener('click', showAddTokenPage);
    document.getElementById('backFromAddTokenBtn').addEventListener('click', showMainPage);
    document.getElementById('aboutBtnSettings').addEventListener('click', showAboutPage);
    document.getElementById('backFromAboutBtn').addEventListener('click', showSettingsPage);
    document.getElementById('uploadQrBtn').addEventListener('click', function() {
        document.getElementById('qrFileInput').click();
    });
    
    // Wait for all pages to be loaded (including dynamic ones)
    document.addEventListener('allPagesLoaded', function() {
        // Initialize update page elements once they're loaded
        const backButton = document.getElementById('backFromUpdateBtn');
        const cancelButton = document.getElementById('cancelUpdateBtn');
        
        if (backButton) {
            backButton.addEventListener('click', function() {
                document.getElementById('updatePage').style.display = 'none';
                showMainPage();
            });
        }
        
        if (cancelButton) {
            cancelButton.addEventListener('click', function() {
                document.getElementById('updatePage').style.display = 'none';
                showMainPage();
            });
        }
        
        const downloadButton = document.getElementById('downloadUpdateBtn');
        if (downloadButton) {
            downloadButton.addEventListener('click', downloadUpdate);
        }
    });
    
    // Rest of your initialization code
    document.getElementById('qrFileInput').addEventListener('change', handleQrFileUpload);
    document.getElementById('saveTokenBtn').addEventListener('click', saveManualToken);
    document.getElementById('saveUriTokenBtn').addEventListener('click', saveUriToken);
    document.getElementById('toggleSortBtn').addEventListener('click', toggleSortOrder);
    document.getElementById('exportTokensBtn').addEventListener('click', exportTokens);
    document.getElementById('searchInput').addEventListener('input', async (e) => {
        searchTerm = e.target.value.toLowerCase();
        await renderTokens();
    });

    // Load settings
    loadMinimizeToTraySetting();
    loadUpdateCheckerSetting();
    loadNextCodePreviewSetting();

    // Import tokens button in settings
    document.getElementById('importTokensBtn').addEventListener('click', showImportTokensPage);
    // Back button from import page
    document.getElementById('backFromImportBtn').addEventListener('click', showSettingsPage);
    // Import buttons
    document.getElementById('importFromWinOTPBtn').addEventListener('click', importFromWinOTP);
    document.getElementById('importFrom2FASBtn').addEventListener('click', importFrom2FAS);
    document.getElementById('importFromAuthenticatorPluginBtn').addEventListener('click', importFromAuthenticatorPlugin);
    document.getElementById('importFromGoogleAuthBtn').addEventListener('click', importFromGoogleAuth);
    
    // App protection settings
    document.getElementById('appProtectionBtn').addEventListener('click', showAppProtectionPage);
    document.getElementById('backFromProtectionBtn').addEventListener('click', showSettingsPage);
    document.getElementById('setPinBtn').addEventListener('click', setPin);
    document.getElementById('setPasswordBtn').addEventListener('click', setPassword);
    document.getElementById('disableProtectionBtn').addEventListener('click', disableProtection);
    
    // Login page
    document.getElementById('loginBtn').addEventListener('click', login);
    document.getElementById('loginCredential').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            login();
        }
    });

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

    // Start periodic auth check
    startAuthCheck();

    // Google Auth import page
    document.getElementById('backFromGoogleAuthBtn').addEventListener('click', backFromGoogleAuth);
    document.getElementById('finishGoogleAuthImportBtn').addEventListener('click', finishGoogleAuthImport);

    // Add event listener for start scan button
    document.getElementById('startScanBtn').addEventListener('click', initializeQrScanner);
});

// Wait for API to be ready
function waitForApi() {
    console.log("Waiting for API to be ready...");
    
    // Show a loading indicator
    document.getElementById('mainPage').style.display = 'none';
    document.getElementById('loginPage').style.display = 'none';
    
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
    
    // Check if API is available
    const checkApi = () => {
        if (window.pywebview && window.pywebview.api) {
            console.log("API is ready!");
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
            console.log("API not ready yet, retrying...");
            setTimeout(checkApi, 100);
        }
    };
    
    // Start checking for API
    checkApi();
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
    
    // If no download URL is available, use the GitHub releases page as fallback
    const targetUrl = downloadUrl || `https://github.com/xBounceIT/WinOTP/releases`;
    
    try {
        // Open the download URL in the default browser
        await window.pywebview.api.open_url(targetUrl);
        
        // Show success message
        showNotification('Download started in your browser', 'success');
    } catch (error) {
        console.error("Error starting download:", error);
        showNotification('Failed to start download. Please visit the releases page manually.', 'error');
        
        // Fallback to opening the releases page
        window.pywebview.api.open_url('https://github.com/xBounceIT/WinOTP/releases');
    }
} 