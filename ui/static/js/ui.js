// Show main page
function showMainPage() {
    // Add transition classes
    if (document.getElementById('settingsPage').style.display === 'block') {
        document.getElementById('settingsPage').classList.remove('fade-in');
        document.getElementById('settingsPage').classList.add('fade-out');
    } else if (document.getElementById('addTokenPage').style.display === 'block') {
        document.getElementById('addTokenPage').classList.remove('fade-in');
        document.getElementById('addTokenPage').classList.add('fade-out');
    } else if (document.getElementById('aboutPage').style.display === 'block') {
        document.getElementById('aboutPage').classList.remove('fade-in');
        document.getElementById('aboutPage').classList.add('fade-out');
    } else if (document.getElementById('importTokensPage').style.display === 'block') {
        document.getElementById('importTokensPage').classList.remove('fade-in');
        document.getElementById('importTokensPage').classList.add('fade-out');
    } else if (document.getElementById('googleAuthImportPage').style.display === 'block') {
        document.getElementById('googleAuthImportPage').classList.remove('fade-in');
        document.getElementById('googleAuthImportPage').classList.add('fade-out');
    }
    
    setTimeout(() => {
        document.getElementById('settingsPage').style.display = 'none';
        document.getElementById('addTokenPage').style.display = 'none';
        document.getElementById('aboutPage').style.display = 'none';
        document.getElementById('importTokensPage').style.display = 'none';
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('googleAuthImportPage').style.display = 'none';
        document.getElementById('importProgressPage').style.display = 'none';
        document.getElementById('mainPage').style.display = 'block';
        
        // Force reflow
        void document.getElementById('mainPage').offsetWidth;
        
        document.getElementById('mainPage').classList.add('fade-in');
        
        // Load icons
        loadPlusIcon();
        loadSettingsIcon();
        loadSortIcon();
        
        // Start auth check when returning to main page
        startAuthCheck();
        
        // Load tokens
        loadTokens();

        // Check for updates on main page load (if enabled)
        checkUpdatesOnLoad();
    }, 300);
}

// Show settings page
function showSettingsPage() {
    // Add transition classes
    if (document.getElementById('aboutPage').style.display === 'block') {
        document.getElementById('aboutPage').classList.remove('fade-in');
        document.getElementById('aboutPage').classList.add('fade-out');
    } else if (document.getElementById('importTokensPage').style.display === 'block') {
        document.getElementById('importTokensPage').classList.remove('fade-in');
        document.getElementById('importTokensPage').classList.add('fade-out');
    } else if (document.getElementById('appProtectionPage').style.display === 'block') {
        document.getElementById('appProtectionPage').classList.remove('fade-in');
        document.getElementById('appProtectionPage').classList.add('fade-out');
    } else {
        document.getElementById('mainPage').classList.add('fade-out');
    }
    
    setTimeout(() => {
        document.getElementById('mainPage').style.display = 'none';
        document.getElementById('aboutPage').style.display = 'none';
        document.getElementById('importTokensPage').style.display = 'none';
        document.getElementById('appProtectionPage').style.display = 'none';
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('settingsPage').style.display = 'block';
        
        // Force reflow
        void document.getElementById('settingsPage').offsetWidth;
        
        document.getElementById('settingsPage').classList.add('fade-in');
        
        // Update protection status
        updateProtectionStatus();
        // Load settings
        loadMinimizeToTraySetting();
        loadUpdateCheckerSetting();
        // Load back icon
        loadBackIcon();
        // Load about icon
        loadAboutIcon();
    }, 300);
}

// Show about page
function showAboutPage() {
    // Add transition classes
    document.getElementById('mainPage').classList.remove('fade-in');
    document.getElementById('mainPage').classList.add('fade-out');
    document.getElementById('settingsPage').classList.remove('fade-in');
    document.getElementById('settingsPage').classList.add('fade-out');
    
    setTimeout(() => {
        document.getElementById('mainPage').style.display = 'none';
        document.getElementById('settingsPage').style.display = 'none';
        document.getElementById('addTokenPage').style.display = 'none';
        document.getElementById('importTokensPage').style.display = 'none';
        document.getElementById('appProtectionPage').style.display = 'none';
        document.getElementById('aboutPage').style.display = 'block';
        
        // Force reflow
        void document.getElementById('aboutPage').offsetWidth;
        
        document.getElementById('aboutPage').classList.add('fade-in');
        
        // Load back icon
        loadBackIconForAbout();

        // Fetch and display the version
        loadAppVersion();

        // Stop auth check when navigating away from main page
        stopAuthCheck();
    }, 300); // Match transition duration
}

// Show add token page
function showAddTokenPage() {
    // Add transition classes
    document.getElementById('mainPage').classList.add('fade-out');
    
    setTimeout(() => {
        document.getElementById('mainPage').style.display = 'none';
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('addTokenPage').style.display = 'block';
        
        // Force reflow
        void document.getElementById('addTokenPage').offsetWidth;
        
        document.getElementById('addTokenPage').classList.add('fade-in');
        
        // Load back icon for add token page
        loadBackIconForAddToken();
        
        // Clear form fields
        clearTokenForm();
    }, 300);
}

// Show import tokens page
function showImportTokensPage() {
    // Add transition classes
    document.getElementById('settingsPage').classList.remove('fade-in');
    document.getElementById('settingsPage').classList.add('fade-out');
    
    setTimeout(() => {
        document.getElementById('settingsPage').style.display = 'none';
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('importTokensPage').style.display = 'block';
        
        // Force reflow
        void document.getElementById('importTokensPage').offsetWidth;
        
        document.getElementById('importTokensPage').classList.add('fade-in');
        
        // Load back icon for import page
        loadBackIconForImport();
    }, 300);
}

// Show app protection page
function showAppProtectionPage() {
    document.getElementById('settingsPage').classList.remove('fade-in');
    document.getElementById('settingsPage').classList.add('fade-out');
    
    setTimeout(() => {
        document.getElementById('settingsPage').style.display = 'none';
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('appProtectionPage').style.display = 'block';
        
        // Force reflow
        void document.getElementById('appProtectionPage').offsetWidth;
        
        document.getElementById('appProtectionPage').classList.add('fade-in');
        
        // Load back icon
        loadBackIconForProtection();
        
        // Show or hide forms based on current protection status
        updateProtectionForms();
    }, 300);
}

// Show login page
function showLoginPage(authType) {
    // Hide all other pages
    document.getElementById('mainPage').style.display = 'none';
    document.getElementById('settingsPage').style.display = 'none';
    document.getElementById('addTokenPage').style.display = 'none';
    document.getElementById('aboutPage').style.display = 'none';
    document.getElementById('importTokensPage').style.display = 'none';
    document.getElementById('appProtectionPage').style.display = 'none';
    
    // Update login page based on auth type
    if (authType === 'pin') {
        document.getElementById('loginTitle').textContent = 'Enter PIN';
        document.getElementById('loginDescription').textContent = 'Please enter your PIN to access the app';
        document.getElementById('loginCredential').placeholder = 'Enter your PIN';
        document.getElementById('loginCredential').type = 'password';
        document.getElementById('loginCredential').inputMode = 'numeric';
        document.getElementById('loginCredential').pattern = '[0-9]*';
    } else {
        document.getElementById('loginTitle').textContent = 'Enter Password';
        document.getElementById('loginDescription').textContent = 'Please enter your password to access the app';
        document.getElementById('loginCredential').placeholder = 'Enter your password';
        document.getElementById('loginCredential').type = 'password';
        document.getElementById('loginCredential').inputMode = 'text';
        document.getElementById('loginCredential').pattern = '';
    }
    
    // Show login page
    document.getElementById('loginPage').style.display = 'block';
    
    // Focus on credential input
    document.getElementById('loginCredential').focus();
}

// Function to fetch and display the app version
async function loadAppVersion() {
    try {
        await waitForPywebviewApi(); // Ensure API is ready
        const version = await window.pywebview.api.get_current_version();
        document.getElementById('appVersion').textContent = `Version: ${version}`;
    } catch (error) {
        console.error('Error loading app version:', error);
        document.getElementById('appVersion').textContent = 'Version: Unknown';
    }
}

// Show notification
function showNotification(message, type) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = 'notification ' + type;
    notification.classList.add('show');
    
    // Keep the notification visible until manually dismissed or another notification appears
    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000); // 5 seconds timeout
}

// Open modal
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Clear token form
function clearTokenForm() {
    document.getElementById('tokenIssuer').value = '';
    document.getElementById('tokenName').value = '';
    document.getElementById('tokenSecret').value = '';
    document.getElementById('tokenUri').value = '';
}

// Function to update import progress UI
function updateImportProgress(current, total, percentage) {
    document.getElementById('importProgressBar').style.width = percentage + '%';
    document.getElementById('importProgressCount').textContent = `(${current}/${total})`;
}

// Function called by Python backend to update progress
function updateProgress(data) {
    if (!data) return;
    
    // Update progress bar and status text
    const progressBar = document.getElementById('importProgressBar');
    const progressCount = document.getElementById('importProgressCount');
    const progressStatus = document.getElementById('importProgressStatus');
    
    if (progressBar && progressCount && progressStatus) {
        // Calculate percentage
        const percentage = Math.min(100, Math.max(0, (data.current / data.total) * 100));
        
        // Update UI
        progressBar.style.width = percentage + '%';
        progressCount.textContent = `(${data.current}/${data.total})`;
        
        if (data.status) {
            progressStatus.textContent = data.status;
        }
    }
} 