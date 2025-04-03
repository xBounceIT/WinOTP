// Load tokens from the API
async function loadTokens() {
    try {
        if (!apiReady || !window.pywebview || !window.pywebview.api) {
            console.error("API not available for loading tokens");
            return;
        }
        
        const result = await window.pywebview.api.get_tokens();
        console.log('API get_tokens result:', result);
        tokens = result;
        await renderTokens();
        
        // Start update interval if not already started
        if (!updateInterval) {
            updateInterval = setInterval(updateTokens, 1000);
        }
        
        // Load icons if not already loaded
        if (!cachedPlusIcon) loadPlusIcon();
        if (!cachedSortAscIcon || !cachedSortDescIcon) loadSortIcon();
        if (!cachedSettingsIcon) loadSettingsIcon();
        if (!cachedAboutIcon) loadAboutIcon();
        if (!cachedCopyIcon) loadCopyIcon();
        if (!cachedCrossIcon) loadCrossIcon();
        if (!cachedEditIcon) loadEditIcon();
        
        return result;
    } catch (error) {
        console.error('Error loading tokens:', error);
        return [];
    }
}

// Update tokens (refresh codes and time remaining)
async function updateTokens() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            return;
        }

        const result = await window.pywebview.api.get_tokens();
        console.log('API get_tokens result:', result);
        let newTokens = [];
        
        // Check if result is an array (direct token list) or an object with status
        if (Array.isArray(result)) {
            newTokens = result;
        } else if (result && Array.isArray(result.data)) {
            newTokens = result.data;
        } else {
            console.error("Unexpected response format from get_tokens:", result);
            return;
        }
        
        // Check if we have a search filter active
        const isSearchActive = searchTerm && searchTerm.length > 0;
        
        // Store current token data
        tokens = newTokens;
        
        // Only update existing tokens, full render if tokens changed
        if (!isSearchActive) {
            const currentTokenIds = new Set(newTokens.map(t => t.id));
            const displayedTokenIds = new Set(Array.from(document.querySelectorAll('.token-card'))
                .map(card => card.id.replace('token-', '')));
            
            // Check if we need a full re-render
            if (currentTokenIds.size !== displayedTokenIds.size || 
                !Array.from(currentTokenIds).every(id => displayedTokenIds.has(id))) {
                await renderTokens();
            } else {
                // Just update the dynamic content
                tokens.forEach(updateTokenDisplay);
            }
        } else {
            // When search is active, only update the currently displayed tokens
            // to avoid flickering and maintain search results
            const displayedTokenCards = document.querySelectorAll('.token-card');
            const displayedTokenIds = Array.from(displayedTokenCards).map(card => card.id.replace('token-', ''));
            
            displayedTokenIds.forEach(id => {
                const token = tokens.find(t => t.id === id);
                if (token) {
                    updateTokenDisplay(token);
                }
            });
        }
    } catch (error) {
        console.error('Error updating tokens:', error);
    }
}

// Update token display
async function updateTokenDisplay(token) {
    const codeElement = document.getElementById(`code-${token.id}`);
    const progressElement = document.getElementById(`progress-${token.id}`);
    const timerElement = document.getElementById(`timer-${token.id}`);
    
    if (codeElement && progressElement && timerElement) {
        // First time setup if needed
        if (!codeElement.querySelector('.codes-container')) {
            const copyButton = codeElement.querySelector('.copy-button');
            codeElement.innerHTML = '';
            
            const codesContainer = document.createElement('div');
            codesContainer.className = 'codes-container';
            
            // Create the current code line with copy button
            const codeLine = document.createElement('div');
            codeLine.className = 'code-line';
            
            const currentCodeSpan = document.createElement('span');
            currentCodeSpan.className = 'current-code';
            codeLine.appendChild(currentCodeSpan);
            
            if (copyButton) {
                codeLine.appendChild(copyButton);
            }
            
            codesContainer.appendChild(codeLine);
            codeElement.appendChild(codesContainer);
        }

        const codesContainer = codeElement.querySelector('.codes-container');
        const currentCodeSpan = codesContainer.querySelector('.current-code');
        currentCodeSpan.textContent = formatCode(token.code);
        
        // Update progress bar and timer
        const timeRemaining = token.timeRemaining;
        const progressPercentage = (timeRemaining / 30) * 100;
        
        progressElement.style.width = `${progressPercentage}%`;
        progressElement.className = `token-progress-bar${timeRemaining <= 5 ? ' warning' : ''}`;
        timerElement.textContent = `${Math.ceil(timeRemaining)}s`;

        // Handle next code preview
        const nextCodePreviewEnabled = await window.pywebview.api.get_setting('next_code_preview_enabled');
        let nextCodeContainer = codesContainer.querySelector('.next-code-container');

        // Only show next code preview if enabled and time remaining is between 0.1 and 5 seconds
        if (nextCodePreviewEnabled && timeRemaining <= 5 && timeRemaining > 0.1) {
            const nextCode = await window.pywebview.api.get_next_code(token.id);
            if (nextCode && nextCode.code) {
                if (!nextCodeContainer) {
                    nextCodeContainer = document.createElement('div');
                    nextCodeContainer.className = 'next-code-container';
                    
                    const nextCodeSpan = document.createElement('span');
                    nextCodeSpan.className = 'next-code';
                    nextCodeContainer.appendChild(nextCodeSpan);
                    
                    codesContainer.appendChild(nextCodeContainer);
                    // Force reflow before adding show class
                    void nextCodeContainer.offsetHeight;
                    nextCodeContainer.classList.add('show');
                }
                
                const nextCodeSpan = nextCodeContainer.querySelector('.next-code');
                nextCodeSpan.textContent = formatCode(nextCode.code);
            }
        } else if (nextCodeContainer) {
            nextCodeContainer.classList.remove('show');
            // Wait for animation to complete before removing
            setTimeout(() => {
                if (nextCodeContainer && nextCodeContainer.parentNode) {
                    nextCodeContainer.remove();
                }
            }, 300);
        }
    }
}

// Render tokens to the DOM
async function renderTokens() {
    const tokenList = document.getElementById('tokenList');
    
    // Store the current progress, copy button and next code preview states before clearing
    const animationStates = {};
    const existingTokenCards = document.querySelectorAll('.token-card');
    
    existingTokenCards.forEach(card => {
        const tokenId = card.id.replace('token-', '');
        const progressBar = document.getElementById(`progress-${tokenId}`);
        const nextCodeContainer = card.querySelector('.next-code-container');
        const copyButton = card.querySelector('.copy-button');
        
        animationStates[tokenId] = {
            progressWidth: progressBar ? progressBar.style.width : null,
            progressClass: progressBar ? progressBar.className : null,
            nextCodeVisible: nextCodeContainer ? nextCodeContainer.classList.contains('show') : false,
            nextCodeHtml: nextCodeContainer ? nextCodeContainer.innerHTML : null,
            copyButtonClass: copyButton ? copyButton.className : null,
            copyButtonHtml: copyButton ? copyButton.innerHTML : null
        };
    });
    
    tokenList.innerHTML = '';

    // Filter and sort tokens
    let filteredTokens = tokens.filter(token => 
        token.issuer.toLowerCase().includes(searchTerm) || 
        token.name.toLowerCase().includes(searchTerm)
    );

    filteredTokens.sort((a, b) => {
        const compareResult = a.issuer.localeCompare(b.issuer);
        return sortAscending ? compareResult : -compareResult;
    });

    // Check if there are no tokens to display
    if (filteredTokens.length === 0) {
        // If no search term, show welcome message
        if (!searchTerm) {
            const welcomeMessage = document.createElement('div');
            welcomeMessage.className = 'welcome-message';
            welcomeMessage.innerHTML = `
                <div class="welcome-content">
                    <h2>Welcome to WinOTP</h2>
                    <p>You don't have any tokens yet. Add your first token to get started.</p>
                    <p>Click the + button in the top right corner to add a token.</p>
                    <button class="btn" onclick="document.getElementById('addTokenBtn').click()">Add Token</button>
                </div>
            `;
            tokenList.appendChild(welcomeMessage);
        } else {
            // If search term exists but no results, show no results message
            const noResults = document.createElement('div');
            noResults.className = 'welcome-message';
            noResults.innerHTML = `
                <div class="welcome-content">
                    <h2>No Results Found</h2>
                    <p>No tokens match your search criteria.</p>
                    <button class="btn" onclick="document.getElementById('searchInput').value = ''; searchTerm = ''; renderTokens();">Clear Search</button>
                </div>
            `;
            tokenList.appendChild(noResults);
        }
        return;
    }

    filteredTokens.forEach(token => {
        const tokenCard = document.createElement('div');
        tokenCard.className = 'token-card';
        tokenCard.id = `token-${token.id}`;
        
        tokenCard.innerHTML = `
            <div class="token-header">
                <div class="token-info">
                    <div class="token-issuer">${escapeHtml(token.issuer)}</div>
                    <div class="token-name">${escapeHtml(token.name)}</div>
                </div>
                <div class="token-actions">
                    <button class="btn btn-icon" onclick="toggleEditMode('${token.id}')">
                        ${cachedEditIcon ? `<img src="data:image/png;base64,${cachedEditIcon}" alt="Edit token" width="20" height="20">` : '✏️'}
                    </button>
                    <button class="btn btn-icon" onclick="deleteToken('${token.id}')">
                        ${cachedCrossIcon ? `<img src="data:image/png;base64,${cachedCrossIcon}" alt="Delete token" width="20" height="20">` : '🗑️'}
                    </button>
                </div>
            </div>
            <div class="token-edit-form" id="edit-form-${token.id}" style="display: none;">
                <div class="form-group">
                    <label for="editTokenIssuer-${token.id}">Issuer:</label>
                    <input type="text" id="editTokenIssuer-${token.id}" value="${escapeHtml(token.issuer)}" />
                </div>
                <div class="form-group">
                    <label for="editTokenName-${token.id}">Account Name:</label>
                    <input type="text" id="editTokenName-${token.id}" value="${escapeHtml(token.name)}" />
                </div>
                <div class="form-actions">
                    <button class="btn" onclick="saveTokenEdit('${token.id}')">Save</button>
                    <button class="btn btn-secondary" onclick="toggleEditMode('${token.id}')">Cancel</button>
                </div>
            </div>
            <div class="token-code" id="code-${token.id}">
                <div class="codes-container">
                    <div class="code-line">
                        <span class="current-code">${formatCode(token.code)}</span>
                        <button class="copy-button" onclick="copyCode('${token.id}')">
                            ${cachedCopyIcon ? `<img src="data:image/png;base64,${cachedCopyIcon}" alt="Copy" width="16" height="16">` : '📋'}
                        </button>
                    </div>
                </div>
            </div>
            <div class="token-footer">
                <div class="token-progress-container">
                    <div class="token-progress-bar" id="progress-${token.id}" style="width: ${(token.timeRemaining / 30) * 100}%"></div>
                </div>
                <div class="time-remaining" id="timer-${token.id}">${Math.ceil(token.timeRemaining)}s</div>
            </div>
        `;
        
        tokenList.appendChild(tokenCard);
        
        // Restore animation states if available
        if (animationStates[token.id]) {
            const state = animationStates[token.id];
            const progressBar = document.getElementById(`progress-${token.id}`);
            const codeElement = document.getElementById(`code-${token.id}`);
            const codesContainer = codeElement.querySelector('.codes-container');
            const copyButton = codeElement.querySelector('.copy-button');
            
            // Restore progress bar state
            if (progressBar && state.progressWidth) {
                progressBar.style.width = state.progressWidth;
                if (state.progressClass) {
                    progressBar.className = state.progressClass;
                }
            }
            
            // Restore copy button state
            if (copyButton && state.copyButtonClass) {
                copyButton.className = state.copyButtonClass;
                if (state.copyButtonHtml) {
                    copyButton.innerHTML = state.copyButtonHtml;
                }
            }
            
            // Restore next code container if it was visible
            if (state.nextCodeVisible && state.nextCodeHtml && codesContainer) {
                const nextCodeContainer = document.createElement('div');
                nextCodeContainer.className = 'next-code-container';
                nextCodeContainer.innerHTML = state.nextCodeHtml;
                codesContainer.appendChild(nextCodeContainer);
                
                // Force reflow before adding show class
                void nextCodeContainer.offsetHeight;
                nextCodeContainer.classList.add('show');
            }
        }
    });
}

// Format TOTP code with spaces for readability
function formatCode(code) {
    if (code.length === 6) {
        return code.substring(0, 3) + ' ' + code.substring(3);
    }
    return code;
}

// Copy code to clipboard
async function copyCode(tokenId) {
    const token = tokens.find(t => t.id === tokenId);
    if (token) {
        try {
            const copyButton = document.querySelector(`#code-${tokenId} .copy-button`);
            const copyText = document.createElement('span');
            copyText.className = 'copy-text';
            copyText.textContent = 'COPIED';
            
            // Remove any existing copy-text element
            const existingCopyText = copyButton.querySelector('.copy-text');
            if (existingCopyText) {
                copyButton.removeChild(existingCopyText);
            }
            
            copyButton.appendChild(copyText);
            await navigator.clipboard.writeText(token.code);
            copyButton.classList.add('copied');
            
            setTimeout(() => {
                copyButton.classList.remove('copied');
                setTimeout(() => {
                    copyText.remove();
                }, 300); // Wait for the fade out animation
            }, 2000);
        } catch (error) {
            showNotification('Failed to copy code', 'error');
        }
    }
}

// Delete token
async function deleteToken(tokenId) {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        // Show native Windows confirmation dialog
        const confirmed = await window.pywebview.api.show_confirmation_dialog('Are you sure you want to delete this token?', 'Delete Token');
        
        if (confirmed) {
            const result = await window.pywebview.api.delete_token(tokenId);
            if (result.status === 'success') {
                showNotification(result.message, 'success');
                loadTokens();
            } else {
                showNotification(result.message, 'error');
            }
        }
    } catch (error) {
        showNotification('Error deleting token: ' + error, 'error');
    }
}

// Save manually entered token
async function saveManualToken() {
    const issuer = document.getElementById('tokenIssuer').value.trim();
    const name = document.getElementById('tokenName').value.trim();
    const secret = document.getElementById('tokenSecret').value.trim();

    if (!secret) {
        showNotification('Secret key is required', 'error');
        return;
    }

    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        const result = await window.pywebview.api.add_token({
            issuer: issuer || 'Unknown',
            name: name || 'Unknown',
            secret: secret
        });

        if (result.status === 'success') {
            showNotification(result.message, 'success');
            showMainPage();
            clearTokenForm();
            loadTokens();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error adding token: ' + error, 'error');
    }
}

// Handle QR code file upload
async function handleQrFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        // Call API to scan QR code from file
        const result = await window.pywebview.api.scan_qr_from_file(file.path);
        if (result.status === 'success') {
            const tokenData = result.data;
            const addResult = await window.pywebview.api.add_token(tokenData);
            
            if (addResult.status === 'success') {
                showNotification(addResult.message, 'success');
                showMainPage();
                loadTokens();
            } else {
                showNotification(addResult.message, 'error');
            }
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error processing QR code: ' + error, 'error');
    }
    
    // Reset file input
    event.target.value = '';
}

// Toggle sort order
async function toggleSortOrder() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        const result = await window.pywebview.api.toggle_sort_order();
        if (result.status === 'success') {
            sortAscending = result.ascending;
            loadSortIcon();
            loadTokens();
        }
    } catch (error) {
        showNotification('Error toggling sort order: ' + error, 'error');
    }
}

// Toggle edit mode for a token
function toggleEditMode(tokenId) {
    const editForm = document.getElementById(`edit-form-${tokenId}`);
    const isVisible = editForm.style.display === 'block';
    
    // Hide all edit forms
    document.querySelectorAll('.token-edit-form').forEach(form => {
        form.style.display = 'none';
    });
    
    // Toggle the current form
    if (!isVisible) {
        editForm.style.display = 'block';
    }
}

// Save token edit
async function saveTokenEdit(tokenId) {
    const issuer = document.getElementById(`editTokenIssuer-${tokenId}`).value.trim();
    const name = document.getElementById(`editTokenName-${tokenId}`).value.trim();
    
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        const result = await window.pywebview.api.update_token(tokenId, {
            issuer: issuer || 'Unknown',
            name: name || 'Unknown'
        });
        
        if (result.status === 'success') {
            showNotification(result.message, 'success');
            toggleEditMode(tokenId); // Hide edit form
            loadTokens(); // Reload tokens to show changes
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error updating token: ' + error, 'error');
    }
}

// Save token from URI
async function saveUriToken() {
    const uri = document.getElementById('tokenUri').value.trim();
    const saveButton = document.getElementById('saveUriTokenBtn');

    // Ensure button is enabled at the start
    saveButton.disabled = false;
    saveButton.style.pointerEvents = 'auto';

    // Client-side validation
    if (!uri) {
        showNotification('URI is required', 'error');
        return;
    }

    if (!uri.startsWith('otpauth://')) {
        showNotification('Invalid OTP Auth URI format', 'error');
        return;
    }

    // Validate URI format and secret
    const validationResult = validateOtpUri(uri);
    if (!validationResult.valid) {
        showNotification(validationResult.message, 'error');
        return;
    }

    if (!window.pywebview || !window.pywebview.api) {
        console.error("pywebview API not available");
        showNotification('Error: API not available', 'error');
        return;
    }
    
    try {
        // Only disable the button during the actual API call
        saveButton.disabled = true;
        saveButton.style.pointerEvents = 'none';
        
        // API call
        const result = await window.pywebview.api.add_token_from_uri(uri);

        if (result.status === 'success') {
            showNotification(result.message, 'success');
            showMainPage();
            clearTokenForm();
            loadTokens();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error adding token from URI:', error);
        showNotification('Error adding token: ' + error, 'error');
    } finally {
        // Re-enable the button after API call
        saveButton.disabled = false;
        saveButton.style.pointerEvents = 'auto';
        
        // Force a style update
        saveButton.style.backgroundColor = '';
        saveButton.style.cursor = 'pointer';
    }
}

// Validate OTP Auth URI format and secret
function validateOtpUri(uri) {
    // Basic format check
    if (!uri.startsWith('otpauth://totp/')) {
        return { valid: false, message: 'URI must start with otpauth://totp/' };
    }

    // Extract secret from URI
    const secretMatch = uri.match(/secret=([^&]+)/);
    if (!secretMatch) {
        return { valid: false, message: 'Secret parameter is missing in URI' };
    }

    const secret = secretMatch[1];
    
    // Check if secret is valid base32 (A-Z and 2-7)
    // Remove any padding characters
    const cleanSecret = secret.replace(/=/g, '');
    
    // Check if the string only contains valid base32 characters
    if (!/^[A-Z2-7]+$/.test(cleanSecret)) {
        return { 
            valid: false, 
            message: 'Secret is not a valid base32 string. Only characters A-Z and 2-7 are allowed.' 
        };
    }
    
    // Most TOTP secrets should be at least 16 chars
    if (cleanSecret.length < 16) {
        return { 
            valid: false, 
            message: 'Secret is too short. It should be at least 16 characters long.' 
        };
    }

    return { valid: true };
} 