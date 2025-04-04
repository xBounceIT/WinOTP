// Check authentication status
async function checkAuthStatus() {
    try {
        if (!apiReady) {
            console.error("API not ready yet, cannot check auth status");
            showMainPage();
            return;
        }
        
        const status = await window.pywebview.api.get_auth_status();
        console.log("Auth status:", status);
        
        if (status.is_enabled && !status.is_authenticated) {
            // Show login page
            showLoginPage(status.auth_type);
        } else {
            // Already authenticated or no auth required
            isAuthenticated = true;
            showMainPage();
            loadTokens();
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        // Default to showing main page
        showMainPage();
        loadTokens();
    }
}

// Function to start periodic auth check
function startAuthCheck() {
    // Clear existing interval if any
    if (authCheckInterval) {
        clearInterval(authCheckInterval);
    }
    
    // Check auth status every 30 seconds
    authCheckInterval = setInterval(async () => {
        try {
            const status = await window.pywebview.api.get_auth_status();
            if (status.is_enabled && !status.is_authenticated) {
                // Show login page if authentication has expired
                showLoginPage(status.auth_type);
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
        }
    }, 30000); // Check every 30 seconds
}

// Function to stop auth check
function stopAuthCheck() {
    if (authCheckInterval) {
        clearInterval(authCheckInterval);
        authCheckInterval = null;
    }
}

// Login function
async function login() {
    const credential = document.getElementById('loginCredential').value;
    
    try {
        const result = await window.pywebview.api.verify_authentication(credential);
        if (result.status === 'success') {
            document.getElementById('loginCredential').value = '';
            isAuthenticated = true;
            
            // Ensure all icons are loaded before showing main page
            await loadAllIcons();
            
            showMainPage();
            startAuthCheck();

            // Check for update info in the response
            if (result.update_info && result.update_info.available) {
                console.log("Update info found in auth response, showing update button...");
                showUpdateNotification(result.update_info);
            } else {
                console.log("No update info found or update not available.");
            }
        } else {
            // Use showNotification for login errors
            showNotification(result.message, 'error'); 
        }
    } catch (error) {
        console.error('Error during login:', error);
        showNotification('Login failed', 'error');
    }
}

// Show or hide protection forms based on current status
async function updateProtectionForms() {
    try {
        await waitForPywebviewApi();
        
        const status = await window.pywebview.api.get_auth_status();
        const formsDiv = document.getElementById('protectionForms');
        const disableSection = document.getElementById('disableProtectionSection');
        const separator = document.getElementById('protectionSetupSeparator');
        
        if (status.is_enabled) {
            // If protection is already enabled, hide forms and show disable button
            if (formsDiv) formsDiv.style.display = 'none';
            if (disableSection) disableSection.style.display = 'block';
            if (separator) separator.style.display = 'none';
        } else {
            // If protection is not enabled, show forms and hide disable button
            if (formsDiv) formsDiv.style.display = 'block';
            if (disableSection) disableSection.style.display = 'none';
            if (separator) separator.style.display = 'flex';
        }
        
        // Update status text
        const statusText = document.getElementById('protectionStatusText');
        if (statusText) {
            if (status.is_enabled) {
                statusText.textContent = status.auth_type === 'pin' ? 'PIN Protected' : 'Password Protected';
                statusText.className = 'protection-status-badge protected';
            } else {
                statusText.textContent = 'Not Protected';
                statusText.className = 'protection-status-badge not-protected';
            }
        }
    } catch (error) {
        console.error('Error updating protection forms:', error);
    }
}

// Update protection status in settings page
async function updateProtectionStatus() {
    try {
        await waitForPywebviewApi();
        
        const status = await window.pywebview.api.get_auth_status();
        const statusBadge = document.getElementById('settingsProtectionStatus');
        
        if (statusBadge) {
            if (status.is_enabled) {
                statusBadge.textContent = status.auth_type === 'pin' ? 'PIN Protected' : 'Password Protected';
                statusBadge.className = 'protection-status-badge protected';
            } else {
                statusBadge.textContent = 'Not Protected';
                statusBadge.className = 'protection-status-badge not-protected';
            }
        }
        
        // Update timeout select
        const timeoutSelect = document.getElementById('timeoutSelect');
        if (timeoutSelect && status.timeout_minutes !== undefined) {
            const options = Array.from(timeoutSelect.options);
            const option = options.find(opt => parseInt(opt.value) === status.timeout_minutes);
            
            if (option) {
                timeoutSelect.value = option.value;
            }
        }
    } catch (error) {
        console.error('Error updating protection status:', error);
    }
}

// Load minimize to tray setting
async function loadMinimizeToTraySetting() {
    try {
        // Wait for pywebview API to be ready
        await waitForPywebviewApi();
        const result = await window.pywebview.api.get_minimize_to_tray();
        if (result.status === 'success') {
            document.getElementById('minimizeToTrayToggle').checked = result.enabled;
        }
    } catch (error) {
        console.error('Error loading minimize to tray setting:', error);
    }
}

// Function to load update checker setting
async function loadUpdateCheckerSetting() {
    try {
        // Wait for pywebview API to be ready
        await waitForPywebviewApi();
        const enabled = await window.pywebview.api.get_setting('update_check_enabled');
        // Default to true if the value is undefined
        document.getElementById('updateCheckerToggle').checked = enabled !== undefined ? enabled : true;
    } catch (error) {
        console.error('Error loading update checker setting:', error);
        // Default to true if there's an error
        document.getElementById('updateCheckerToggle').checked = true;
    }
}

// Function to load run at startup setting
async function loadRunAtStartupSetting() {
    try {
        // Wait for pywebview API to be ready
        await waitForPywebviewApi();
        const enabled = await window.pywebview.api.get_setting('run_at_startup');
        // Default to false if the value is undefined
        const toggle = document.getElementById('runAtStartupToggle');
        if (toggle) {
            toggle.checked = enabled !== undefined ? enabled : false;
        }
    } catch (error) {
        console.error('Error loading run at startup setting:', error);
        // Default to false if there's an error
        const toggle = document.getElementById('runAtStartupToggle');
        if (toggle) {
            toggle.checked = false;
        }
    }
}

// Function to load next code preview setting
async function loadNextCodePreviewSetting() {
    try {
        // Wait for pywebview API to be ready
        await waitForPywebviewApi();
        const enabled = await window.pywebview.api.get_setting('next_code_preview_enabled');
        // Default to false if the value is undefined
        document.getElementById('nextCodePreviewToggle').checked = enabled !== undefined ? enabled : false;
    } catch (error) {
        console.error('Error loading next code preview setting:', error);
        // Default to false if there's an error
        document.getElementById('nextCodePreviewToggle').checked = false;
    }
}

// Set PIN protection
async function setPin() {
    const pin = document.getElementById('pinInput').value.trim();
    
    // Validate PIN (should be at least 4 digits)
    if (!/^\d{4,}$/.test(pin)) {
        showNotification('PIN must be at least 4 digits', 'error');
        return;
    }
    
    try {
        await waitForPywebviewApi();
        
        const result = await window.pywebview.api.set_pin_protection(pin);
        if (result.status === 'success') {
            showNotification(result.message, 'success');
            updateProtectionForms();
            updateProtectionStatus();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error setting PIN protection:', error);
        showNotification('Failed to set PIN protection', 'error');
    }
}

// Set password protection
async function setPassword() {
    const password = document.getElementById('passwordInput').value.trim();
    
    // Validate password (should be at least 6 characters)
    if (password.length < 6) {
        showNotification('Password must be at least 6 characters long', 'error');
        return;
    }
    
    try {
        await waitForPywebviewApi();
        
        const result = await window.pywebview.api.set_password_protection(password);
        if (result.status === 'success') {
            showNotification(result.message, 'success');
            updateProtectionForms();
            updateProtectionStatus();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error setting password protection:', error);
        showNotification('Failed to set password protection', 'error');
    }
}

// Disable protection
async function disableProtection() {
    try {
        await waitForPywebviewApi();

        // Get the current auth type to customize the prompt
        const authStatus = await window.pywebview.api.get_auth_status();
        const authType = authStatus.auth_type; // 'pin' or 'password'

        if (!authType) {
            showNotification('Protection is already disabled.', 'info');
            return; // Nothing to do
        }

        // Use the custom modal to get the credential
        const credential = await showCredentialPrompt(authType);

        if (credential === null) {
            // User cancelled the dialog
            console.log('Disable protection cancelled by user.');
            showNotification('Disable protection cancelled.', 'success');
        } else {
            // Credential entered, proceed directly to backend call (confirmation removed)
            console.log("Attempting to disable protection with provided credential...");
            
            // Send the credential to the backend
            const result = await window.pywebview.api.disable_protection(credential);
            if (result.status === 'success') {
                showNotification(result.message, 'success');
                document.getElementById('pinInput').value = '';
                document.getElementById('passwordInput').value = '';
                updateProtectionForms();
                updateProtectionStatus();
            } else {
                // Display the specific error from the backend (e.g., incorrect PIN/password)
                showNotification(result.message || 'Failed to disable protection', 'error');
            }
        }
        
    } catch (error) {
        console.error('Error disabling protection:', error);
        showNotification('Failed to disable protection: ' + (error.message || 'Unknown error'), 'error');
    }
}

// --- Helper Function for Custom Credential Prompt ---
function showCredentialPrompt(authType) {
    return new Promise((resolve) => {
        const modal = document.getElementById('credentialPromptModal');
        const title = document.getElementById('credentialPromptTitle');
        const message = document.getElementById('credentialPromptMessage');
        const input = document.getElementById('credentialPromptInput');
        const confirmBtn = document.getElementById('credentialPromptConfirmBtn');
        const cancelBtn = document.getElementById('credentialPromptCancelBtn');

        // Customize prompt based on auth type
        if (authType === 'pin') {
            title.textContent = 'Enter PIN';
            message.textContent = 'Please enter your current PIN to disable protection:';
            input.type = 'password'; // Keep it masked
            input.inputMode = 'numeric';
            input.pattern = '[0-9]*';
            input.placeholder = 'Enter current PIN';
        } else {
            title.textContent = 'Enter Password';
            message.textContent = 'Please enter your current password to disable protection:';
            input.type = 'password';
            input.inputMode = 'text';
            input.pattern = '';
            input.placeholder = 'Enter current password';
        }
        input.value = ''; // Clear previous input

        // Event listeners for buttons
        const confirmHandler = () => {
            cleanup();
            const value = input.value.trim();
            if (value) {
                resolve(value);
            } else {
                showNotification('Credential cannot be empty.', 'error');
                resolve(null); // Treat empty input as cancellation after showing error
            }
        };

        const cancelHandler = () => {
            cleanup();
            resolve(null); // Resolve with null when cancelled
        };
        
        const keypressHandler = (e) => {
            if (e.key === 'Enter') {
                confirmHandler();
            }
            if (e.key === 'Escape') {
                 cancelHandler();
            }
        };

        // Function to remove listeners and hide modal
        const cleanup = () => {
            confirmBtn.removeEventListener('click', confirmHandler);
            cancelBtn.removeEventListener('click', cancelHandler);
            input.removeEventListener('keypress', keypressHandler);
            modal.style.display = 'none';
        };

        // Attach listeners
        confirmBtn.addEventListener('click', confirmHandler);
        cancelBtn.addEventListener('click', cancelHandler);
        input.addEventListener('keypress', keypressHandler); 

        // Show modal
        modal.style.display = 'flex';
        input.focus(); // Focus the input field
    });
} 