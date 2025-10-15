// Track whether tokens have been loaded
let tokensLoaded = false;

// Load tokens from the API (only do this once at startup or when needed)
async function loadTokens() {
    try {
        if (!apiReady || !window.pywebview || !window.pywebview.api) {
            console.error("API not available for loading tokens");
            return;
        }

        // Skip loading if tokens are already loaded and we have tokens in memory
        if (tokensLoaded && tokens && tokens.length > 0) {
            console.log('Using already loaded tokens, skipping API call');
            // Just re-render tokens using existing data
            await renderTokens();
            return tokens;
        }
        
        console.log('Loading all tokens from backend...');
        const result = await window.pywebview.api.get_tokens();
        console.log('API get_tokens result:', result);
        tokens = result;
        
        // Set the flag indicating tokens have been loaded
        tokensLoaded = true;
        
        // Clear next codes cache when loading all tokens
        Object.keys(nextCodes).forEach(key => delete nextCodes[key]);
        
        // Prefetch next codes for all tokens
        const nextCodePromises = tokens.map(async token => {
            try {
                const nextCodeResult = await window.pywebview.api.get_next_code(token.id);
                if (nextCodeResult.status === 'success' && nextCodeResult.code) {
                    nextCodes[token.id] = nextCodeResult.code;
                }
            } catch (error) {
                console.error(`Failed to prefetch next code for token ${token.id}:`, error);
            }
        });
        
        // Wait for all next codes to be prefetched
        await Promise.all(nextCodePromises);
        
        await renderTokens();
        
        // Start update interval if not already started
        if (!updateInterval) {
            updateInterval = setInterval(updateVisuals, 1000);
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

// Force reload tokens (used when tokens have been modified)
async function forceReloadTokens() {
    // Reset the loaded flag to force a reload
    tokensLoaded = false;
    return await loadTokens();
}

// Update only visual elements (progress bar and timer) every second
function updateVisuals() {
    // Skip if no tokens
    if (!tokens || tokens.length === 0) return;
    
    // Track expired tokens for batch refresh
    let expiredTokens = [];
    
    // Update each token's remaining time
    tokens.forEach(token => {
        if (token.timeRemaining > 0) {
            token.timeRemaining -= 1;
            
            // Always update the display for tokens with positive time
            updateTokenDisplay(token);
            
            // If time is about to expire (0 seconds left), add to expired tokens
            if (token.timeRemaining <= 0) {
                expiredTokens.push(token);
            } 
            // If the token is close to expiring (5 seconds), make sure we have the next code ready
            else if (token.timeRemaining === 5) {
                // Clear any cached next code to ensure we get a fresh one
                delete nextCodes[token.id];
                // Pre-fetch the next code
                fetchAndUpdateNextCode(token.id);
            }
        } else if (token.timeRemaining <= 0 && !expiredTokens.includes(token)) {
            // Add any already expired tokens that haven't been refreshed yet
            expiredTokens.push(token);
        }
    });
    
    // If we have expired tokens, trigger a refresh
    if (expiredTokens.length > 0) {
        // If more than 50% of tokens are expiring at once, there's likely a synchronization
        // where all tokens refresh at the same time - this is when CPU spikes occur
        if (expiredTokens.length > Math.max(1, tokens.length * 0.5)) {
            console.log(`Batch refreshing ${expiredTokens.length} tokens (${Math.round(expiredTokens.length/tokens.length*100)}% of total)`);
        }
        refreshTokens();
    }
}

// Store next codes for each token
const nextCodes = {};

// Last batch refresh timestamp to prevent frequent API calls
let lastBatchRefreshTime = 0;
const MIN_BATCH_REFRESH_INTERVAL = 500; // Minimum milliseconds between refreshes

// Update tokens from API only when needed
async function refreshTokens() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            return;
        }

        // Find tokens with expired timers
        const expiredTokens = tokens.filter(token => token.timeRemaining <= 0);
        
        // If there are no expired tokens, nothing to do
        if (expiredTokens.length === 0) {
            return;
        }
        
        // Throttle API calls to prevent excessive refreshes
        const now = Date.now();
        if (now - lastBatchRefreshTime < MIN_BATCH_REFRESH_INTERVAL) {
            console.log('Skipping refresh, too soon after last refresh');
            // Schedule another check in a short time
            setTimeout(refreshTokens, MIN_BATCH_REFRESH_INTERVAL);
            return;
        }
        
        // Update refresh timestamp
        lastBatchRefreshTime = now;
        
        // Extract token IDs for batch refresh
        const tokenIds = expiredTokens.map(token => token.id);
        console.log(`Refreshing ${tokenIds.length} tokens in batch`);
        
        // Use the new batch API endpoint
        const batchResult = await window.pywebview.api.batch_get_token_codes(tokenIds);
        
        if (batchResult.status === 'success') {
            // Process batch results
            for (const tokenId in batchResult.results) {
                const result = batchResult.results[tokenId];
                if (result.status === 'success') {
                    // Find the token in our array and update it
                    const tokenIndex = tokens.findIndex(t => t.id === result.id);
                    if (tokenIndex !== -1) {
                        // Important: Clear the nextCodes cache for this token when a code refreshes
                        // because the current code becomes the old "next code"
                        delete nextCodes[tokenId];
                        
                        tokens[tokenIndex].code = result.code;
                        tokens[tokenIndex].timeRemaining = result.timeRemaining;
                        
                        // Store the next code from the batch result
                        if (result.nextCode) {
                            nextCodes[tokenId] = result.nextCode;
                        } else {
                            // If nextCode isn't provided in batch result, fetch it separately
                            fetchAndUpdateNextCode(tokenId);
                        }
                    }
                } else {
                    console.error(`Error refreshing token ${tokenId}:`, result.message);
                }
            }
            
            // Check if we have a search filter active
            const isSearchActive = searchTerm && searchTerm.length > 0;
            
            // Only update existing tokens, full render if token collection changed
            if (!isSearchActive) {
                // Just update the dynamic content for all tokens
                tokens.forEach(updateTokenDisplay);
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
        } else {
            console.error('Error in batch token refresh:', batchResult.message);
            
            // Fallback to old method if batch fails
            fallbackRefreshTokens(expiredTokens);
        }
    } catch (error) {
        console.error('Error updating tokens:', error);
        
        // Try fallback method if the new batch method failed
        if (tokens && tokens.length > 0) {
            const expiredTokens = tokens.filter(token => token.timeRemaining <= 0);
            if (expiredTokens.length > 0) {
                fallbackRefreshTokens(expiredTokens);
            }
        }
    }
}

// Helper function to fetch and update next code
async function fetchAndUpdateNextCode(tokenId) {
    try {
        const nextCodeResult = await window.pywebview.api.get_next_code(tokenId);
        if (nextCodeResult.status === 'success' && nextCodeResult.code) {
            nextCodes[tokenId] = nextCodeResult.code;
        }
    } catch (error) {
        console.error(`Failed to fetch next code for token ${tokenId}:`, error);
    }
}

// Legacy token refresh method as fallback
async function fallbackRefreshTokens(expiredTokens) {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            return;
        }
        
        // Use Promise.all to refresh all expired tokens in parallel
        const refreshPromises = expiredTokens.map(async token => {
            const result = await window.pywebview.api.get_fresh_token_code(token.id);
            if (result.status === 'success') {
                // Find the token in our array and update it
                const tokenIndex = tokens.findIndex(t => t.id === result.id);
                if (tokenIndex !== -1) {
                    // Clear the nextCodes cache for this token when a code refreshes
                    delete nextCodes[token.id];
                    
                    tokens[tokenIndex].code = result.code;
                    tokens[tokenIndex].timeRemaining = result.timeRemaining;
                    
                    // Also prefetch the next code for this token while we're at it
                    const nextCodeResult = await window.pywebview.api.get_next_code(token.id);
                    if (nextCodeResult.status === 'success' && nextCodeResult.code) {
                        nextCodes[token.id] = nextCodeResult.code;
                    }
                }
                return true;
            } else {
                console.error(`Error refreshing token ${token.id}:`, result.message);
                return false;
            }
        });
        
        await Promise.all(refreshPromises);
        
        // Update UI
        tokens.forEach(updateTokenDisplay);
    } catch (error) {
        console.error('Error in fallback token refresh:', error);
    }
}

// Rename the old updateTokens function to the new refreshTokens function name
// for backward compatibility with any code that might be calling it directly
const updateTokens = refreshTokens;

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

        let nextCodeContainer = codesContainer.querySelector('.next-code-container');
        
        // We'll only check for next code preview when time remaining is 5 seconds or less
        if (timeRemaining <= 5) {
            // Get the next code preview setting
            const nextCodePreviewEnabled = await window.pywebview.api.get_setting('next_code_preview_enabled');

            // Only show next code preview if enabled
            if (nextCodePreviewEnabled) {
                let nextCode;
                
                // Check if we already have the next code for this token
                // OR fetch a new one if it's very close to expiration (more accurate)
                if (nextCodes[token.id] && timeRemaining > 2) {
                    nextCode = nextCodes[token.id];
                } else {
                    // When very close to expiration, always fetch the latest next code
                    const nextCodeResult = await window.pywebview.api.get_next_code(token.id);
                    if (nextCodeResult.status === 'success' && nextCodeResult.code) {
                        nextCode = nextCodeResult.code;
                        // Store for future use
                        nextCodes[token.id] = nextCode;
                    }
                }
                
                // If we have a next code, display it
                if (nextCode) {
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
                    nextCodeSpan.textContent = formatCode(nextCode);
                }
            } else if (nextCodeContainer) {
                // Remove the next code container if preview is disabled
                nextCodeContainer.classList.remove('show');
                // Wait for animation to complete before removing
                setTimeout(() => {
                    if (nextCodeContainer && nextCodeContainer.parentNode) {
                        nextCodeContainer.remove();
                    }
                }, 300);
            }
        } else if (nextCodeContainer) {
            // Remove the next code container if time remaining is more than 5 seconds
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
            
            let codeToCopy = token.code;
            
            // Only check for next code if the timer is almost expired
            if (token.timeRemaining <= 5) {
                const nextCodePreviewEnabled = await window.pywebview.api.get_setting('next_code_preview_enabled');
                if (nextCodePreviewEnabled) {
                    // Use cached next code if available
                    if (nextCodes[token.id]) {
                        codeToCopy = nextCodes[token.id];
                    } else {
                        // Only fetch if not cached
                        const nextCode = await window.pywebview.api.get_next_code(token.id);
                        if (nextCode && nextCode.code) {
                            codeToCopy = nextCode.code;
                            // Cache for future use
                            nextCodes[token.id] = nextCode.code;
                        }
                    }
                }
            }
            
            await navigator.clipboard.writeText(codeToCopy);
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
                // Force reload tokens since one was deleted
                await forceReloadTokens();
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
            // Force reload tokens since we added a new one
            await forceReloadTokens();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error adding token: ' + error, 'error');
    }
}

// Handle QR code file upload
async function handleQrFileUpload(event) {
    const input = event.target;
    const file = input && input.files ? input.files[0] : null;

    // Reset file input early so the same file can be re-selected if needed
    if (input) {
        input.value = '';
    }

    if (!file) return;

    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available");
            showNotification('Error: API not available', 'error');
            return;
        }
        
        let result;

        if (file.path) {
            // Native path is available (desktop environment)
            result = await window.pywebview.api.scan_qr_from_file(file.path);
        } else {
            // Browser environment – read file contents and send as data URL
            const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(reader.error || new Error('Failed to read file'));
                reader.readAsDataURL(file);
            });

            result = await window.pywebview.api.scan_qr_code(dataUrl);
        }

        if (result.status === 'success') {
            let tokenData = result.data;

            if (typeof tokenData === 'string' && tokenData.startsWith('otpauth-migration://')) {
                // Handle Google Authenticator migration QR codes via dedicated importer
                const importResult = await window.pywebview.api.import_tokens_from_google_auth_qr(tokenData);
                showNotification(importResult.message, importResult.status === 'success' ? 'success' : 'error');
                if (importResult.status === 'success') {
                    showMainPage();
                    await forceReloadTokens();
                }
                return;
            }

            if (Array.isArray(tokenData)) {
                const [issuer, secret, name] = tokenData;
                tokenData = {
                    issuer: issuer || 'Unknown',
                    name: name || 'Unknown',
                    secret: secret || ''
                };
            }

            if (!tokenData || !tokenData.secret) {
                showNotification('QR code did not contain a valid secret.', 'error');
                return;
            }

            const addResult = await window.pywebview.api.add_token(tokenData);
            
            if (addResult.status === 'success') {
                showNotification(addResult.message, 'success');
                showMainPage();
                // Force reload tokens since we added a new one
                await forceReloadTokens();
            } else {
                showNotification(addResult.message, 'error');
            }
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error processing QR code: ' + error, 'error');
    }
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
            
            // Update the token in our local array
            const tokenIndex = tokens.findIndex(t => t.id === tokenId);
            if (tokenIndex !== -1) {
                tokens[tokenIndex].issuer = issuer || 'Unknown';
                tokens[tokenIndex].name = name || 'Unknown';
                // Re-render the tokens to show changes
                await renderTokens();
            } else {
                // If token not found in local array, force reload all tokens
                await forceReloadTokens();
            }
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
            // Force reload tokens since we added a new one
            await forceReloadTokens();
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
