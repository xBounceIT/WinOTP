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
document.addEventListener('DOMContentLoaded', function() {
    const minimizeToTrayToggle = document.getElementById('minimizeToTrayToggle');
    if (minimizeToTrayToggle) {
        minimizeToTrayToggle.addEventListener('change', async function(e) {
            try {
                const result = await window.pywebview.api.set_minimize_to_tray(e.target.checked);
                if (result.status === 'success') {
                    showNotification(result.message, 'success');
                } else {
                    showNotification(result.message, 'error');
                    e.target.checked = !e.target.checked;
                }
            } catch (error) {
                console.error('Error setting minimize to tray:', error);
                showNotification('Failed to update minimize to tray setting', 'error');
                e.target.checked = !e.target.checked;
            }
        });
    }
});

// Update checker toggle event handler
document.addEventListener('DOMContentLoaded', function() {
    const updateCheckerToggle = document.getElementById('updateCheckerToggle');
    if (updateCheckerToggle) {
        updateCheckerToggle.addEventListener('change', async function(e) {
            try {
                const result = await window.pywebview.api.set_update_check_enabled(e.target.checked);
                if (result.status === 'success') {
                    showNotification(result.message, 'success');
                } else {
                    showNotification(result.message, 'error');
                    e.target.checked = !e.target.checked;
                }
            } catch (error) {
                console.error('Error setting update checker:', error);
                showNotification('Failed to update the update checker setting', 'error');
                e.target.checked = !e.target.checked;
            }
        });
    }
});

// Next code preview toggle event handler
document.addEventListener('DOMContentLoaded', function() {
    const nextCodePreviewToggle = document.getElementById('nextCodePreviewToggle');
    if (nextCodePreviewToggle) {
        nextCodePreviewToggle.addEventListener('change', async function(e) {
            try {
                const result = await window.pywebview.api.set_next_code_preview(e.target.checked);
                if (result.status === 'success') {
                    showNotification(result.message, 'success');
                } else {
                    showNotification(result.message, 'error');
                    e.target.checked = !e.target.checked;
                }
            } catch (error) {
                console.error('Error setting next code preview:', error);
                showNotification('Failed to update setting', 'error');
                e.target.checked = !e.target.checked;
            }
        });
    }
}); 