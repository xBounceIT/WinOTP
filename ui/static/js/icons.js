// Icon caching variables
let cachedCopyIcon = ''; // Cache for the copy icon
let cachedPlusIcon = ''; // Cache for the plus icon
let cachedSortAscIcon = ''; // Cache for the sort ascending icon
let cachedSortDescIcon = ''; // Cache for the sort descending icon
let cachedSettingsIcon = ''; // Cache for the settings icon
let cachedCrossIcon = null; // Cache for the cross icon
let cachedAboutIcon = ''; // Cache for the about icon
let cachedEditIcon = null; // Cache for the edit icon

// Service icon cache
const cachedServiceIcons = {}; // Cache for service icons

// Function to load all essential icons at once
async function loadAllIcons() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for loading icons");
            return;
        }
        

        
        // Load all icons in parallel using Promise.all
        await Promise.all([
            loadPlusIcon(),
            loadSettingsIcon(),
            loadSortIcon(),
            loadCopyIcon(),
            loadCrossIcon(),
            loadEditIcon()
        ]);
        

    } catch (error) {
        console.error('Error loading all icons:', error);
    }
}

// Function to load the plus icon
async function loadPlusIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for plus icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('plus.png');

        
        if (result.status === 'success') {
            cachedPlusIcon = result.data;
            const plusBtn = document.getElementById('addTokenBtn');
            if (plusBtn) {
                // Clear any existing content (emoji spans)
                plusBtn.innerHTML = '';
                
                // Add or update the image
                let plusIconImg = document.getElementById('plusIcon');
                if (!plusIconImg) {
                    plusIconImg = document.createElement('img');
                    plusIconImg.id = 'plusIcon';
                    plusIconImg.alt = 'Add Token';
                    plusIconImg.width = 20;
                    plusIconImg.height = 20;
                }
                plusIconImg.src = 'data:image/png;base64,' + cachedPlusIcon;
                plusIconImg.style.display = 'inline';
                plusBtn.appendChild(plusIconImg);

            }
        } else {
            console.error('Error loading plus icon:', result.message);
            showEmojiPlaceholder();
        }
    } catch (error) {
        console.error('Exception loading plus icon:', error);
        showEmojiPlaceholder();
    }
}

// Helper function to show emoji placeholder
function showEmojiPlaceholder() {
    const plusBtn = document.getElementById('addTokenBtn');
    if (plusBtn) {
        // Clear any existing content
        plusBtn.innerHTML = '';
        const emojiSpan = document.createElement('span');
        emojiSpan.textContent = '➕';
        plusBtn.appendChild(emojiSpan);
    }
}

// Load the appropriate sort icon based on current sort order
async function loadSortIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for sort icon");
            return;
        }
        
        // Load both sort icons if not already cached
        if (!cachedSortAscIcon) {
            const ascResult = await window.pywebview.api.get_icon_base64('sort_asc.png');
            if (ascResult.status === 'success') {
                cachedSortAscIcon = ascResult.data;
            }
        }
        if (!cachedSortDescIcon) {
            const descResult = await window.pywebview.api.get_icon_base64('sort_desc.png');
            if (descResult.status === 'success') {
                cachedSortDescIcon = descResult.data;
            }
        }
        
        const sortBtn = document.getElementById('toggleSortBtn');
        if (sortBtn) {
            // Clear any existing content
            sortBtn.innerHTML = '';
            
            // Add or update the image
            let sortIconImg = document.getElementById('sortIcon');
            if (!sortIconImg) {
                sortIconImg = document.createElement('img');
                sortIconImg.id = 'sortIcon';
                sortIconImg.alt = 'Sort Order';
                sortIconImg.width = 20;
                sortIconImg.height = 20;
            }
            sortIconImg.src = 'data:image/png;base64,' + (sortAscending ? cachedSortAscIcon : cachedSortDescIcon);
            sortIconImg.style.display = 'inline';
            sortBtn.appendChild(sortIconImg);

        }
    } catch (error) {
        console.error('Exception loading sort icon:', error);
        // Fallback to emoji if icon loading fails
        const sortBtn = document.getElementById('toggleSortBtn');
        sortBtn.innerHTML = sortAscending ? '↑' : '↓';
    }
}

// Load the settings icon
async function loadSettingsIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for settings icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('settings.png');

        
        if (result.status === 'success') {
            cachedSettingsIcon = result.data;
            const settingsBtn = document.getElementById('settingsBtn');
            if (settingsBtn) {
                // Clear any existing content (emoji)
                settingsBtn.innerHTML = '';
                
                // Add or update the image
                let settingsIconImg = document.createElement('img');
                settingsIconImg.id = 'settingsIcon';
                settingsIconImg.alt = 'Settings';
                settingsIconImg.width = 20;
                settingsIconImg.height = 20;
                settingsIconImg.src = 'data:image/png;base64,' + cachedSettingsIcon;
                settingsIconImg.style.display = 'inline';
                settingsBtn.appendChild(settingsIconImg);

            }
        } else {
            console.error('Error loading settings icon:', result.message);
            showSettingsEmojiPlaceholder();
        }
    } catch (error) {
        console.error('Exception loading settings icon:', error);
        showSettingsEmojiPlaceholder();
    }
}

// Helper function to show settings emoji placeholder
function showSettingsEmojiPlaceholder() {
    const settingsBtn = document.getElementById('settingsBtn');
    if (settingsBtn) {
        settingsBtn.innerHTML = '⚙️';
    }
}

// Load the about icon
async function loadAboutIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for about icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('question.png');

        
        if (result.status === 'success') {
            cachedAboutIcon = result.data;
            // Update the about icon in settings page
            const aboutIcon = document.getElementById('aboutIcon');
            if (aboutIcon) {
                aboutIcon.src = 'data:image/png;base64,' + cachedAboutIcon;
            }
        } else {
            console.error('Error loading about icon:', result.message);
            showAboutEmojiPlaceholder();
        }
    } catch (error) {
        console.error('Exception loading about icon:', error);
        showAboutEmojiPlaceholder();
    }
}

// Helper function to show about emoji placeholder
function showAboutEmojiPlaceholder() {
    const aboutBtn = document.getElementById('aboutBtnSettings');
    if (aboutBtn) {
        aboutBtn.innerHTML = '?';
    }
}

// Load copy icon
async function loadCopyIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for copy icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('copy.png');

        
        if (result.status === 'success') {
            cachedCopyIcon = result.data;
            // Icon will be used when rendering tokens
        } else {
            console.error('Error loading copy icon:', result.message);
        }
    } catch (error) {
        console.error('Exception loading copy icon:', error);
    }
}

// Load cross icon
async function loadCrossIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for cross icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('cross.png');

        
        if (result.status === 'success') {
            cachedCrossIcon = result.data;
            // Icon will be used when rendering tokens
        } else {
            console.error('Error loading cross icon:', result.message);
        }
    } catch (error) {
        console.error('Exception loading cross icon:', error);
    }
}

// Load edit icon
async function loadEditIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for edit icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('edit.png');

        
        if (result.status === 'success') {
            cachedEditIcon = result.data;
            // Icon will be used when rendering tokens
        } else {
            console.error('Error loading edit icon:', result.message);
        }
    } catch (error) {
        console.error('Exception loading edit icon:', error);
    }
}

// Load back icon
async function loadBackIcon() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for back icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('back_arrow.png');
        console.log("Back icon load result:", result);
        
        if (result.status === 'success') {
            const backIcon = document.getElementById('backIcon');
            if (backIcon) {
                backIcon.src = 'data:image/png;base64,' + result.data;
            }
        } else {
            console.error('Error loading back icon:', result.message);
            // Fallback to emoji
            const backBtn = document.getElementById('backToMainBtn');
            if (backBtn) {
                backBtn.innerHTML = '←';
            }
        }
    } catch (error) {
        console.error('Exception loading back icon:', error);
        // Fallback to emoji
        const backBtn = document.getElementById('backToMainBtn');
        if (backBtn) {
            backBtn.innerHTML = '←';
        }
    }
}

// Load back icon for add token page
async function loadBackIconForAddToken() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for back icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('back_arrow.png');
        console.log("Back icon load result:", result);
        
        if (result.status === 'success') {
            const backIcon = document.getElementById('backFromAddTokenIcon');
            if (backIcon) {
                backIcon.src = 'data:image/png;base64,' + result.data;
            }
        } else {
            console.error('Error loading back icon:', result.message);
            // Fallback to emoji
            const backBtn = document.getElementById('backFromAddTokenBtn');
            if (backBtn) {
                backBtn.innerHTML = '←';
            }
        }
    } catch (error) {
        console.error('Exception loading back icon:', error);
        // Fallback to emoji
        const backBtn = document.getElementById('backFromAddTokenBtn');
        if (backBtn) {
            backBtn.innerHTML = '←';
        }
    }
}

// Load back icon for about page
async function loadBackIconForAbout() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for back icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('back_arrow.png');
        console.log("Back icon load result:", result);
        
        if (result.status === 'success') {
            const backIcon = document.getElementById('backFromAboutIcon');
            if (backIcon) {
                backIcon.src = 'data:image/png;base64,' + result.data;
            }
        } else {
            console.error('Error loading back icon:', result.message);
            // Fallback to emoji
            const backBtn = document.getElementById('backFromAboutBtn');
            if (backBtn) {
                backBtn.innerHTML = '←';
            }
        }
    } catch (error) {
        console.error('Exception loading back icon:', error);
        // Fallback to emoji
        const backBtn = document.getElementById('backFromAboutBtn');
        if (backBtn) {
            backBtn.innerHTML = '←';
        }
    }
}

// Load back icon for import page
async function loadBackIconForImport() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for back icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('back_arrow.png');

        
        if (result.status === 'success') {
            const backIcon = document.getElementById('backFromImportIcon');
            if (backIcon) {
                backIcon.src = 'data:image/png;base64,' + result.data;
            }
        } else {
            console.error('Error loading back icon for import page:', result.message);
            // Fallback to emoji
            const backBtn = document.getElementById('backFromImportBtn');
            if (backBtn) {
                backBtn.innerHTML = '←';
            }
        }
    } catch (error) {
        console.error('Exception loading back icon for import page:', error);
        // Fallback to emoji
        const backBtn = document.getElementById('backFromImportBtn');
        if (backBtn) {
            backBtn.innerHTML = '←';
        }
    }
}

// Load back icon for protection page
async function loadBackIconForProtection() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for back icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('back_arrow.png');

        
        if (result.status === 'success') {
            const backIcon = document.getElementById('backFromProtectionIcon');
            if (backIcon) {
                backIcon.src = 'data:image/png;base64,' + result.data;
            }
        } else {
            console.error('Error loading back icon for protection page:', result.message);
            // Fallback to emoji
            const backBtn = document.getElementById('backFromProtectionBtn');
            if (backBtn) {
                backBtn.innerHTML = '←';
            }
        }
    } catch (error) {
        console.error('Exception loading back icon for protection page:', error);
        // Fallback to emoji
        const backBtn = document.getElementById('backFromProtectionBtn');
        if (backBtn) {
            backBtn.innerHTML = '←';
        }
    }
}

// Load back icon for Google Auth import page
async function loadBackIconForGoogleAuth() {
    try {
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for back icon");
            return;
        }
        
        const result = await window.pywebview.api.get_icon_base64('back_arrow.png');

        
        if (result.status === 'success') {
            const backIcon = document.getElementById('backFromGoogleAuthIcon');
            if (backIcon) {
                backIcon.src = 'data:image/png;base64,' + result.data;
            }
        } else {
            console.error('Error loading back icon for Google Auth import page:', result.message);
            // Fallback to emoji
            const backBtn = document.getElementById('backFromGoogleAuthBtn');
            if (backBtn) {
                backBtn.innerHTML = '←';
            }
        }
    } catch (error) {
        console.error('Exception loading back icon for Google Auth import page:', error);
        // Fallback to emoji
        const backBtn = document.getElementById('backFromGoogleAuthBtn');
        if (backBtn) {
            backBtn.innerHTML = '←';
        }
    }
}

// Load service icon for a specific issuer
async function loadServiceIcon(issuer) {
    if (!issuer) return null;
    
    // Check cache first
    if (cachedServiceIcons[issuer]) {
        return cachedServiceIcons[issuer];
    }
    
    try {
        // Import the service icon mapper functions
        if (typeof getServiceIconFilename === 'undefined') {
            console.error('Service icon mapper not loaded');
            return null;
        }
        
        // Get the icon filename for this issuer
        const iconFilename = getServiceIconFilename(issuer);
        
        if (!iconFilename) {
            // No icon mapping found, return null to use letter fallback
            cachedServiceIcons[issuer] = null;
            return null;
        }
        
        // Try to load the icon via pywebview API
        if (!window.pywebview || !window.pywebview.api) {
            console.error("pywebview API not available for service icon");
            return null;
        }
        
        // Use the API to get the service icon
        const result = await window.pywebview.api.get_icon_base64(`services/${iconFilename}`);
        
        if (result.status === 'success') {
            const iconData = `data:image/png;base64,${result.data}`;
            cachedServiceIcons[issuer] = iconData;
            return iconData;
        } else {
            // Icon file not found, cache null
            cachedServiceIcons[issuer] = null;
            return null;
        }
    } catch (error) {
        console.error(`Error loading service icon for ${issuer}:`, error);
        cachedServiceIcons[issuer] = null;
        return null;
    }
}

// Create service icon HTML element
function createServiceIconElement(issuer, iconData) {
    const iconDiv = document.createElement('div');
    iconDiv.className = 'service-icon';
    
    // Force all 32x32 circular styling on the container
    iconDiv.style.width = '32px';
    iconDiv.style.height = '32px';
    iconDiv.style.minWidth = '32px';
    iconDiv.style.maxWidth = '32px';
    iconDiv.style.minHeight = '32px';
    iconDiv.style.maxHeight = '32px';
    iconDiv.style.borderRadius = '50%';
    iconDiv.style.overflow = 'hidden';
    iconDiv.style.boxSizing = 'border-box';
    iconDiv.style.display = 'flex';
    iconDiv.style.alignItems = 'center';
    iconDiv.style.justifyContent = 'center';
    
    if (iconData) {
        // Use the loaded icon image
        const img = document.createElement('img');
        img.src = iconData;
        img.alt = issuer;
        // Force strict size constraints on the image element
        img.style.width = '32px';
        img.style.height = '32px';
        img.style.maxWidth = '32px';
        img.style.maxHeight = '32px';
        img.style.minWidth = '32px';
        img.style.minHeight = '32px';
        img.style.objectFit = 'cover';
        img.style.display = 'block';
        img.style.borderRadius = '50%';
        img.onerror = function() {
            // If image fails to load, switch to letter fallback
            this.style.display = 'none';
            const letterSpan = document.createElement('span');
            letterSpan.className = 'letter-fallback';
            letterSpan.textContent = getIssuerFirstLetter(issuer);
            letterSpan.style.fontSize = '14px';
            letterSpan.style.fontWeight = '700';
            letterSpan.style.textTransform = 'uppercase';
            letterSpan.style.lineHeight = '32px';
            letterSpan.style.width = '100%';
            letterSpan.style.height = '100%';
            letterSpan.style.display = 'flex';
            letterSpan.style.alignItems = 'center';
            letterSpan.style.justifyContent = 'center';
            letterSpan.style.textAlign = 'center';
            iconDiv.appendChild(letterSpan);
            // Set the circular background color for the fallback
            iconDiv.style.backgroundColor = getColorFromIssuer(issuer);
        };
        iconDiv.appendChild(img);
    } else {
        // Use letter fallback - force all circular styling
        const letterSpan = document.createElement('span');
        letterSpan.className = 'letter-fallback';
        letterSpan.textContent = getIssuerFirstLetter(issuer);
        // Force letter styling
        letterSpan.style.fontSize = '14px';
        letterSpan.style.fontWeight = '700';
        letterSpan.style.textTransform = 'uppercase';
        letterSpan.style.lineHeight = '32px';
        letterSpan.style.width = '100%';
        letterSpan.style.height = '100%';
        letterSpan.style.display = 'flex';
        letterSpan.style.alignItems = 'center';
        letterSpan.style.justifyContent = 'center';
        letterSpan.style.textAlign = 'center';
        letterSpan.style.margin = '0';
        letterSpan.style.padding = '0';
        iconDiv.appendChild(letterSpan);
        
        // Set background color based on issuer for circular icon
        iconDiv.style.backgroundColor = getColorFromIssuer(issuer);
    }
    
    // Add loaded class for animation
    setTimeout(() => iconDiv.classList.add('loaded'), 10);
    
    return iconDiv;
}
