/**
 * WinOTP - Main JavaScript File
 * Handles common functionality across the application
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add hand cursor to all buttons
    document.querySelectorAll('.btn').forEach(function(button) {
        button.style.cursor = 'pointer';
    });
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Handle back navigation
    const backButtons = document.querySelectorAll('[data-action="back"]');
    backButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            window.history.back();
        });
    });
    
    // Add copy to clipboard functionality
    function copyToClipboard(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }
    
    // Make this function available globally
    window.copyToClipboard = copyToClipboard;
    
    // Format TOTP codes with a space in the middle
    window.formatCode = function(code) {
        if (code && code.length === 6) {
            return code.substring(0, 3) + ' ' + code.substring(3);
        }
        return code;
    };
    
    // Add animation to buttons when clicked
    document.querySelectorAll('.btn').forEach(function(button) {
        button.addEventListener('click', function() {
            this.classList.add('btn-active');
            setTimeout(() => {
                this.classList.remove('btn-active');
            }, 200);
        });
    });
}); 