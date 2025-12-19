// Service Icon Mapper for WinOTP
// Maps common service names to icon filenames

const SERVICE_ICON_MAP = {
    // Common services - lowercase keys for case-insensitive matching
    'amazon': 'amazon.png',
    'google': 'google.png',
    'microsoft': 'microsoft.png',
    'github': 'github.png',
    'facebook': 'facebook.png',
    'twitter': 'twitter.png',
    'instagram': 'instagram.png',
    'linkedin': 'linkedin.png',
    'spotify': 'spotify.png',
    'paypal': 'paypal.png',
    'discord': 'discord.png',
    'slack': 'slack.png',
    'twitch': 'twitch.png',
    'reddit': 'reddit.png',
    'telegram': 'telegram.png',
    'whatsapp': 'whatsapp.png',
    'apple': 'apple.png',
    'dropbox': 'dropbox.png',
    'evernote': 'evernote.png',
    'figma': 'figma.png',
    'gitlab': 'gitlab.png',
    'instagram': 'instagram.png',
    'jira': 'jira.png',
    'notion': 'notion.png',
    'okta': 'okta.png',
    'outlook': 'outlook.png',
    'proton': 'proton.png',
    'protonmail': 'proton.png',
    'salesforce': 'salesforce.png',
    'skype': 'skype.png',
    'teamviewer': 'teamviewer.png',
    'trello': 'trello.png',
    'tumblr': 'tumblr.png',
    'wordpress': 'wordpress.png',
    'yahoo': 'yahoo.png',
    'youtube': 'youtube.png',
    'zoom': 'zoom.png',
    // Security and Enterprise services
    'akamai': 'akamai.png',
    'bitdefender': 'bitdefender.png',
    'fortinet': 'fortinet.png',
    'reevo': 'reevo.png',
    'sophos': 'sophos.png',
    'stormshield': 'stormshield.png'
};

// Get icon filename for a service name
function getServiceIconFilename(issuer) {
    if (!issuer) return null;
    
    // Normalize the issuer name
    const normalized = issuer.toLowerCase().trim();
    
    // Check exact match first
    if (SERVICE_ICON_MAP[normalized]) {
        return SERVICE_ICON_MAP[normalized];
    }
    
    // Check for partial matches (e.g., "Amazon Web Services" -> "amazon")
    for (const [service, filename] of Object.entries(SERVICE_ICON_MAP)) {
        if (normalized.includes(service)) {
            return filename;
        }
    }
    
    // No icon found
    return null;
}

// Get first letter for fallback icon
function getIssuerFirstLetter(issuer) {
    if (!issuer || issuer.length === 0) return '?';
    return issuer.charAt(0).toUpperCase();
}

// Generate color from issuer name for consistent placeholder colors
function getColorFromIssuer(issuer) {
    if (!issuer) return '#0078d7';
    
    // Simple hash function to generate consistent colors
    let hash = 0;
    for (let i = 0; i < issuer.length; i++) {
        hash = issuer.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    // Generate HSL color with good contrast
    const hue = Math.abs(hash) % 360;
    const saturation = 60 + (Math.abs(hash) % 20); // 60-80%
    const lightness = 45 + (Math.abs(hash) % 10); // 45-55%
    
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

// Check if service icon exists
async function checkServiceIconExists(filename) {
    if (!filename) return false;
    
    try {
        const response = await fetch(`static/icons/services/${filename}`, { method: 'HEAD' });
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SERVICE_ICON_MAP,
        getServiceIconFilename,
        getIssuerFirstLetter,
        getColorFromIssuer,
        checkServiceIconExists
    };
}
