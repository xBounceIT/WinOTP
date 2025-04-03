// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Check NTP synchronization status
async function checkNtpStatus() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            // Try again in 5 seconds
            setTimeout(checkNtpStatus, 5000);
            return;
        }
        
        const result = await window.pywebview.api.get_ntp_status();
        if (result.status === 'success') {
            const status = result.data;
            const statusIndicator = document.querySelector('#ntpStatus .status-indicator');
            const statusText = document.querySelector('#ntpStatus .status-text');
            
            if (status.synced) {
                statusIndicator.className = 'status-indicator synced';
                statusText.textContent = `Synced (${status.offset_ms.toFixed(2)}ms offset)`;
            } else if (status.syncing) {
                statusIndicator.className = 'status-indicator syncing';
                statusText.textContent = 'Synchronizing...';
            } else {
                statusIndicator.className = 'status-indicator error';
                statusText.textContent = 'Not synchronized';
            }
        }
    } catch (error) {
        console.error('Error checking NTP status:', error);
    }
    
    // Check again in 30 seconds
    setTimeout(checkNtpStatus, 30000);
}

// Close modals when clicking outside
window.addEventListener('click', function(event) {
    document.querySelectorAll('.modal').forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// Minimize to tray toggle event handler
// document.addEventListener('DOMContentLoaded', function() { // REMOVED
//     const minimizeToTrayToggle = document.getElementById('minimizeToTrayToggle');
//     if (minimizeToTrayToggle) {
//         minimizeToTrayToggle.addEventListener('change', async function(e) {
//             try {
//                 const result = await window.pywebview.api.set_minimize_to_tray(e.target.checked);
//                 if (result.status === 'success') {
//                     showNotification(result.message, 'success');
//                 } else {
//                     showNotification(result.message, 'error');
//                     e.target.checked = !e.target.checked;
//                 }
//             } catch (error) {
//                 console.error('Error setting minimize to tray:', error);
//                 showNotification('Failed to update minimize to tray setting', 'error');
//                 e.target.checked = !e.target.checked;
//             }
//         });
//     }
// }); // REMOVED

// Update checker toggle event handler
// document.addEventListener('DOMContentLoaded', function() { // REMOVED
//     const updateCheckerToggle = document.getElementById('updateCheckerToggle');
//     if (updateCheckerToggle) {
//         updateCheckerToggle.addEventListener('change', async function(e) {
//             try {
//                 const result = await window.pywebview.api.set_update_check_enabled(e.target.checked);
//                 if (result.status === 'success') {
//                     showNotification(result.message, 'success');
//                 } else {
//                     showNotification(result.message, 'error');
//                     e.target.checked = !e.target.checked;
//                 }
//             } catch (error) {
//                 console.error('Error setting update checker:', error);
//                 showNotification('Failed to update the update checker setting', 'error');
//                 e.target.checked = !e.target.checked;
//             }
//         });
//     }
// }); // REMOVED

// Next code preview toggle event handler
// document.addEventListener('DOMContentLoaded', function() { // REMOVED
//     const nextCodePreviewToggle = document.getElementById('nextCodePreviewToggle');
//     if (nextCodePreviewToggle) {
//         nextCodePreviewToggle.addEventListener('change', async function(e) {
//             try {
//                 const result = await window.pywebview.api.set_next_code_preview(e.target.checked);
//                 if (result.status === 'success') {
//                     showNotification(result.message, 'success');
//                 } else {
//                     showNotification(result.message, 'error');
//                     e.target.checked = !e.target.checked;
//                 }
//             } catch (error) {
//                 console.error('Error setting next code preview:', error);
//                 showNotification('Failed to update setting', 'error');
//                 e.target.checked = !e.target.checked;
//             }
//         });
//     }
// }); // REMOVED

// Function to hide all page containers
function hideAllPages() {
    document.querySelectorAll('.container').forEach(container => {
        container.style.display = 'none';
    });
}

// Show notification function
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// Function to load an icon for a specific element
async function loadIconForElement(elementId, iconName) {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for icon loading");
            return;
        }
        
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element with ID ${elementId} not found`);
            return;
        }
        
        // Get the icon path
        const iconPath = `static/icons/${iconName}`;
        element.src = iconPath;
        
    } catch (error) {
        console.error(`Error loading icon ${iconName} for element ${elementId}:`, error);
    }
}

// Timeout select event handler
// Wait for all pages to be loaded before attaching the listener
document.addEventListener('allPagesLoaded', function() {
    console.log("'allPagesLoaded' event received, attaching timeout listener."); // Debug log
    const timeoutSelect = document.getElementById('timeoutSelect');
    if (timeoutSelect) {
        timeoutSelect.addEventListener('change', async function(e) {
            try {
                const selectedValue = parseInt(e.target.value);
                console.log(`Timeout selection changed to ${selectedValue} minutes`);
                
                // Show a notification that we're updating
                showNotification('Updating timeout setting...', 'info');
                
                // Clear cache before setting timeout
                console.log('Clearing cache...');
                await window.pywebview.api.clear_cache();
                
                // Call the API to update the timeout
                console.log(`Calling set_protection_timeout with value: ${selectedValue}`);
                const result = await window.pywebview.api.set_protection_timeout(selectedValue);
                console.log('API result:', result);
                
                if (result.status === 'success') {
                    console.log('Timeout update successful');
                    showNotification('Re-authentication timeout updated', 'success');
                    
                    // Get the current status to verify the change
                    const status = await window.pywebview.api.get_auth_status();
                    console.log('Current auth status:', status);
                    
                    if (status.timeout_minutes !== selectedValue) {
                        console.warn(`Warning: Timeout value mismatch - set ${selectedValue} but got ${status.timeout_minutes}`);
                    }
                } else {
                    console.error('Timeout update failed:', result.message);
                    showNotification(result.message, 'error');
                    
                    // Revert to previous value
                    console.log('Reverting to previous value...');
                    const status = await window.pywebview.api.get_auth_status();
                    console.log('Current auth status for revert:', status);
                    
                    if (status.timeout_minutes !== undefined) {
                        console.log(`Reverting UI to ${status.timeout_minutes}`);
                        e.target.value = status.timeout_minutes.toString();
                    }
                }
            } catch (error) {
                console.error('Error setting protection timeout:', error);
                showNotification('Failed to update re-authentication timeout', 'error');
                
                // Revert to previous value
                try {
                    console.log('Attempting to revert after error...');
                    const status = await window.pywebview.api.get_auth_status();
                    console.log('Current auth status for error revert:', status);
                    
                    if (status.timeout_minutes !== undefined) {
                        console.log(`Reverting UI to ${status.timeout_minutes} after error`);
                        e.target.value = status.timeout_minutes.toString();
                    }
                } catch (revertError) {
                    console.error('Error during revert:', revertError);
                }
            }
        });
    } else {
        // If it's *still* not found, something else is wrong
        console.error('FATAL: Timeout select element (#timeoutSelect) not found even after allPagesLoaded event.');
    }
});