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
    } else if (document.getElementById('updatePage').style.display === 'block') {
        document.getElementById('updatePage').classList.remove('fade-in');
        document.getElementById('updatePage').classList.add('fade-out');
    }
    
    setTimeout(() => {
        // Use hideAllPages to ensure all other pages are hidden
        hideAllPages();
        
        // Then show the main page
        document.getElementById('mainPage').style.display = 'block';
        
        // Force reflow
        void document.getElementById('mainPage').offsetWidth;
        
        document.getElementById('mainPage').classList.add('fade-in');
        
        // Load all icons at once using our new utility function
        loadAllIcons();
        
        // Start auth check when returning to main page
        startAuthCheck();
        
        // Load tokens
        loadTokens();

        // Check for updates on main page load (if enabled)
        checkUpdatesOnLoad();
    }, 300);
}

// Show settings page
async function showSettingsPage() {
    // Add transition classes
    if (document.getElementById('aboutPage').style.display === 'block') {
        document.getElementById('aboutPage').classList.remove('fade-in');
        document.getElementById('aboutPage').classList.add('fade-out');
        // Wait briefly for fade-out to start (optional, adjust timing as needed)
        await new Promise(resolve => setTimeout(resolve, 50)); 
    } else if (document.getElementById('importTokensPage').style.display === 'block') {
        document.getElementById('importTokensPage').classList.remove('fade-in');
        document.getElementById('importTokensPage').classList.add('fade-out');
        await new Promise(resolve => setTimeout(resolve, 50));
    } else if (document.getElementById('appProtectionPage').style.display === 'block') {
        document.getElementById('appProtectionPage').classList.remove('fade-in');
        document.getElementById('appProtectionPage').classList.add('fade-out');
        await new Promise(resolve => setTimeout(resolve, 50));
    } else {
        document.getElementById('mainPage').classList.add('fade-out');
        await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    // Hide all other pages
    document.getElementById('mainPage').style.display = 'none';
    document.getElementById('aboutPage').style.display = 'none';
    document.getElementById('importTokensPage').style.display = 'none';
    document.getElementById('appProtectionPage').style.display = 'none';
    document.getElementById('loginPage').style.display = 'none';
    
    // Show the settings page loaded from settings.html
    const settingsPage = document.getElementById('settingsPage');
    if (!settingsPage) {
        console.error('Settings page not found! Make sure settings.html is properly loaded.');
        showNotification('Error loading settings page', 'error');
        return;
    }
    
    settingsPage.style.display = 'block';
    
    // Force reflow before fade-in
    void settingsPage.offsetWidth;
    
    // Start fade-in animation
    settingsPage.classList.add('fade-in');
    
    // --- Load settings and icons concurrently --- 
    // (This part now runs immediately after the page is shown)
    try {
        await waitForPywebviewApi(); // Ensure API is ready once

        const [
            authStatusResult,
            minimizeResult,
            updateCheckEnabled,
            nextCodePreviewEnabled,
            runAtStartupEnabled,
            backIconResult,
            aboutIconResult
        ] = await Promise.all([
            window.pywebview.api.get_auth_status(),
            window.pywebview.api.get_minimize_to_tray(),
            window.pywebview.api.get_setting('update_check_enabled'),
            window.pywebview.api.get_setting('next_code_preview_enabled'),
            window.pywebview.api.get_setting('run_at_startup'),
            window.pywebview.api.get_icon_base64('back_arrow.png'),
            window.pywebview.api.get_icon_base64('question.png')
        ]);

        // --- Apply results --- 
        // (Same logic as before to apply the fetched data)

        // Apply auth status
        const statusBadge = document.getElementById('settingsProtectionStatus');
        if (statusBadge) {
            if (authStatusResult.is_enabled) {
                statusBadge.textContent = authStatusResult.auth_type === 'pin' ? 'PIN Protected' : 'Password Protected';
                statusBadge.className = 'protection-status-badge protected';
            } else {
                statusBadge.textContent = 'Not Protected';
                statusBadge.className = 'protection-status-badge not-protected';
            }
        }
        const timeoutSelect = document.getElementById('timeoutSelect');
        if (timeoutSelect && authStatusResult.timeout_minutes !== undefined) {
            const options = Array.from(timeoutSelect.options);
            const option = options.find(opt => parseInt(opt.value) === authStatusResult.timeout_minutes);
            if (option) {
                timeoutSelect.value = option.value;
            }
        }

        // Apply minimize setting
        if (minimizeResult.status === 'success') {
            document.getElementById('minimizeToTrayToggle').checked = minimizeResult.enabled;
        }

        // Apply update checker setting
        document.getElementById('updateCheckerToggle').checked = updateCheckEnabled !== undefined ? updateCheckEnabled : true;

        // Apply next code preview setting
        document.getElementById('nextCodePreviewToggle').checked = nextCodePreviewEnabled !== undefined ? nextCodePreviewEnabled : false;

        // Apply run at startup setting
        const runAtStartupToggleElement = document.getElementById('runAtStartupToggle');
        if (runAtStartupToggleElement) {
            runAtStartupToggleElement.checked = runAtStartupEnabled !== undefined ? runAtStartupEnabled : false;
            
            // Set up the event listener for run at startup toggle
            runAtStartupToggleElement.addEventListener('change', async (event) => {
                try {
                    console.log('Run at startup toggle changed:', event.target.checked);
                    await waitForPywebviewApi();
                    const isEnabled = event.target.checked;
                    const result = await window.pywebview.api.set_run_at_startup(isEnabled);
                    console.log('Run at startup API response:', result);
                    
                    if (result.status === 'success') {
                        showNotification(`Run at startup ${isEnabled ? 'enabled' : 'disabled'}`, 'success');
                    } else {
                        showNotification(result.message || 'Failed to update run at startup setting', 'error');
                        // Revert the toggle state on error
                        event.target.checked = !event.target.checked;
                    }
                } catch (error) {
                    console.error('Error setting run at startup:', error);
                    showNotification('Failed to update run at startup setting', 'error');
                    // Revert the toggle state on error
                    event.target.checked = !event.target.checked;
                }
            });
        } else {
            console.error("Could not find element with ID 'runAtStartupToggle' in settings page.");
        }


        // Set up event listener for Minimize to Tray toggle
        const minimizeToTrayToggle = document.getElementById('minimizeToTrayToggle');
        if (minimizeToTrayToggle) {
            minimizeToTrayToggle.addEventListener('change', async function(e) {
                try {
                    await waitForPywebviewApi();
                    const result = await window.pywebview.api.set_minimize_to_tray(e.target.checked);
                    if (result.status === 'success') {
                        showNotification(result.message, 'success');
                    } else {
                        showNotification(result.message, 'error');
                        e.target.checked = !e.target.checked; // Revert on error
                    }
                } catch (error) {
                    console.error('Error setting minimize to tray:', error);
                    showNotification('Failed to update minimize to tray setting', 'error');
                    e.target.checked = !e.target.checked; // Revert on error
                }
            });
        } else {
            console.error("Could not find element with ID 'minimizeToTrayToggle' in settings page.");
        }

        // Set up event listener for Update Checker toggle
        const updateCheckerToggle = document.getElementById('updateCheckerToggle');
        if (updateCheckerToggle) {
            updateCheckerToggle.addEventListener('change', async function(e) {
                try {
                    await waitForPywebviewApi();
                    const result = await window.pywebview.api.set_update_check_enabled(e.target.checked);
                    if (result.status === 'success') {
                        showNotification(result.message, 'success');
                    } else {
                        showNotification(result.message, 'error');
                        e.target.checked = !e.target.checked; // Revert on error
                    }
                } catch (error) {
                    console.error('Error setting update checker:', error);
                    showNotification('Failed to update the update checker setting', 'error');
                    e.target.checked = !e.target.checked; // Revert on error
                }
            });
        } else {
            console.error("Could not find element with ID 'updateCheckerToggle' in settings page.");
        }

        // Set up event listener for Next Code Preview toggle
        const nextCodePreviewToggle = document.getElementById('nextCodePreviewToggle');
        if (nextCodePreviewToggle) {
            nextCodePreviewToggle.addEventListener('change', async function(e) {
                try {
                    await waitForPywebviewApi();
                    const result = await window.pywebview.api.set_next_code_preview(e.target.checked);
                    if (result.status === 'success') {
                        showNotification(result.message, 'success');
                    } else {
                        showNotification(result.message, 'error');
                        e.target.checked = !e.target.checked; // Revert on error
                    }
                } catch (error) {
                    console.error('Error setting next code preview:', error);
                    showNotification('Failed to update setting', 'error');
                    e.target.checked = !e.target.checked; // Revert on error
                }
            });
        } else {
            console.error("Could not find element with ID 'nextCodePreviewToggle' in settings page.");
        }

        // Set up event listener for Backup Enabled toggle
        const backupEnabledToggle = document.getElementById('backupEnabledToggle');
        if (backupEnabledToggle) {
            // First, get the current backup status to set the initial toggle value and button states
            let backupEnabled = false;
            try {
                const backupStatus = await window.pywebview.api.get_backup_status();
                if (backupStatus.status === 'success') {
                    backupEnabled = backupStatus.data.enabled;
                    backupEnabledToggle.checked = backupEnabled;
                    // Update button states immediately
                    updateBackupButtonStates(backupEnabled);
                }
            } catch (error) {
                console.error('Error getting backup status for toggle:', error);
            }
            
            // Now set up the event listener
            backupEnabledToggle.addEventListener('change', async function(e) {
                try {
                    await waitForPywebviewApi();
                    const result = await window.pywebview.api.enable_backup(e.target.checked);
                    if (result.status === 'success') {
                        showNotification(result.message, 'success');
                        // Update backup status display and button states
                        updateBackupStatusDisplay();
                        updateBackupButtonStates(e.target.checked);
                    } else {
                        showNotification(result.message, 'error');
                        e.target.checked = !e.target.checked; // Revert on error
                    }
                } catch (error) {
                    console.error('Error enabling backup:', error);
                    showNotification('Failed to update backup setting', 'error');
                    e.target.checked = !e.target.checked; // Revert on error
                }
            });
        } else {
            console.error("Could not find element with ID 'backupEnabledToggle' in settings page.");
        }

        // Helper function to update backup sections visibility based on backup enabled status
        async function updateBackupButtonStates(backupEnabled) {
            const backupSectionsContainer = document.getElementById('backupSectionsContainer');
            const backupToggleItem = document.getElementById('backupEnabledToggle').closest('.setting-item');
            
            if (backupSectionsContainer) {
                backupSectionsContainer.style.display = backupEnabled ? 'block' : 'none';
            }
            
            // Remove bottom border from the backup toggle when sections are hidden
            if (backupToggleItem) {
                if (backupEnabled) {
                    backupToggleItem.style.borderBottom = '1px solid var(--border-color)';
                } else {
                    backupToggleItem.style.borderBottom = 'none';
                }
            }
        }

        // Set up event listener for Select Backup Folder button
        const selectBackupFolderBtn = document.getElementById('selectBackupFolderBtn');
        if (selectBackupFolderBtn) {
            selectBackupFolderBtn.addEventListener('click', async function() {
                try {
                    await waitForPywebviewApi();
                    
                    // Use webview's file dialog to select a folder location
                    const selectedFiles = await window.pywebview.api.select_directory_dialog();
                    
                    if (selectedFiles && selectedFiles.status === 'success' && selectedFiles.path) {
                        // The dialog already validated the filename and directory
                        // Set the selected directory as backup folder
                        const result = await window.pywebview.api.set_backup_folder(selectedFiles.path);
                        if (result.status === 'success') {
                            showNotification('Backup folder selected successfully', 'success');
                            // Update backup folder display
                            updateBackupFolderDisplay();
                        } else {
                            showNotification(result.message || 'Failed to set backup folder', 'error');
                        }
                    } else if (selectedFiles && selectedFiles.status === 'error') {
                        // Show the error message from the API
                        showNotification(selectedFiles.message, 'error');
                    } else {
                        // User cancelled or no directory selected
                        console.log('Folder selection cancelled');
                    }
                } catch (error) {
                    console.error('Error selecting backup folder:', error);
                    showNotification('Failed to select backup folder: ' + error.message, 'error');
                }
            });
        } else {
            console.error("Could not find element with ID 'selectBackupFolderBtn' in settings page.");
        }

        // Set up event listener for Create Backup button
        const createBackupBtn = document.getElementById('createBackupBtn');
        if (createBackupBtn) {
            createBackupBtn.addEventListener('click', async function() {
                try {
                    await waitForPywebviewApi();
                    const result = await window.pywebview.api.create_manual_backup();
                    if (result.status === 'success') {
                        showNotification('Manual backup executed successfully', 'success');
                        // Update backup status display
                        updateBackupStatusDisplay();
                    } else {
                        showNotification('Manual backup failed', 'error');
                    }
                } catch (error) {
                    console.error('Error creating backup:', error);
                    showNotification('Manual backup failed', 'error');
                }
            });
        } else {
            console.error("Could not find element with ID 'createBackupBtn' in settings page.");
        }

        // Helper function to update backup folder display
        async function updateBackupFolderDisplay() {
            try {
                await waitForPywebviewApi();
                const status = await window.pywebview.api.get_backup_status();
                if (status.status === 'success') {
                    const backupFolderDisplay = document.getElementById('backupFolderDisplay');
                    if (backupFolderDisplay) {
                        if (status.data.backup_folder) {
                            // Show last part of the path for privacy
                            const parts = status.data.backup_folder.split(/[/\\]/);
                            const folderName = parts[parts.length - 1];
                            backupFolderDisplay.textContent = `Current folder: ${folderName}`;
                        } else {
                            backupFolderDisplay.textContent = 'Default folder';
                        }
                    }
                }
            } catch (error) {
                console.error('Error updating backup folder display:', error);
            }
        }

        // Helper function to update backup status display
        async function updateBackupStatusDisplay() {
            try {
                await waitForPywebviewApi();
                const status = await window.pywebview.api.get_backup_status();
                if (status.status === 'success') {
                    const backupStatusDisplay = document.getElementById('backupStatusDisplay');
                    if (backupStatusDisplay) {
                        if (status.data.last_backup_date) {
                            backupStatusDisplay.textContent = `Last backup: ${status.data.last_backup_date}`;
                        } else {
                            backupStatusDisplay.textContent = 'No backups found';
                        }
                    }
                }
            } catch (error) {
                console.error('Error updating backup status display:', error);
            }
        }

        // Initialize backup displays and ensure correct initial state
        updateBackupFolderDisplay();
        updateBackupStatusDisplay();
        
        // Ensure backup sections visibility is correct on initial load
        const initialBackupEnabled = backupEnabledToggle.checked;
        updateBackupButtonStates(initialBackupEnabled);

        // Apply back icon
        if (backIconResult.status === 'success') {
            const backIcon = document.getElementById('backIcon');
            if (backIcon) {
                backIcon.src = 'data:image/png;base64,' + backIconResult.data;
            }
        } else {
            console.error('Error loading back icon:', backIconResult.message);
            const backBtn = document.getElementById('backToMainBtn');
            if (backBtn) backBtn.innerHTML = '←';
        }

        // Apply about icon
        if (aboutIconResult.status === 'success') {
            cachedAboutIcon = aboutIconResult.data; // Update cache if used elsewhere
            const aboutIcon = document.getElementById('aboutIcon');
            if (aboutIcon) {
                aboutIcon.src = 'data:image/png;base64,' + aboutIconResult.data;
            }
        } else {
            console.error('Error loading about icon:', aboutIconResult.message);
            showAboutEmojiPlaceholder();
        }

    } catch (error) {
        console.error('Error loading settings page data:', error);
        // Handle errors appropriately, maybe show a notification
        showNotification('Failed to load settings', 'error');
    }
    // --- End loading settings and icons concurrently ---
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
    // Instead of hiding completely, we'll just visually hide the main page
    // This preserves DOM elements including loaded icons
    const mainPage = document.getElementById('mainPage');
    if (mainPage.style.display === 'block') {
        // Only apply transition if it's currently visible
        mainPage.classList.remove('fade-in');
        mainPage.classList.add('fade-out');
        
        setTimeout(() => {
            mainPage.style.display = 'none';
            showLoginPageContent(authType);
        }, 300);
    } else {
        // If main page wasn't visible, just show login immediately
        mainPage.style.display = 'none';
        showLoginPageContent(authType);
    }
}

// Helper function to display login page content
function showLoginPageContent(authType) {
    // Hide all other pages
    document.getElementById('settingsPage').style.display = 'none';
    document.getElementById('addTokenPage').style.display = 'none';
    document.getElementById('aboutPage').style.display = 'none';
    document.getElementById('importTokensPage').style.display = 'none';
    document.getElementById('appProtectionPage').style.display = 'none';
    document.getElementById('googleAuthImportPage').style.display = 'none';
    document.getElementById('importProgressPage').style.display = 'none';
    
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

document.addEventListener('DOMContentLoaded', () => {
    // ... other event listeners ...

    // ... other event listeners ...
});
