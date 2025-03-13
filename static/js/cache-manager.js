/**
 * Cache Manager - Handles client-side caching of static resources
 * 
 * This script uses the Cache API to store and retrieve static resources,
 * improving page load times for subsequent visits.
 */

// Cache version - increment when resources change
const CACHE_VERSION = '1.0.0';
const CACHE_NAME = `winotp-static-${CACHE_VERSION}`;

// Resources to cache
const CACHE_URLS = [
    '/static/css/bootstrap.min.css',
    '/static/css/style.css',
    '/static/css/icons.css',
    '/static/js/jquery-3.6.0.min.js',
    '/static/js/bootstrap.bundle.min.js',
    '/static/js/app.js',
    '/static/icons/search.png',
    '/static/icons/sort_asc.png',
    '/static/icons/sort_desc.png',
    '/static/icons/settings.png',
    '/static/icons/plus.png',
    '/static/icons/back_arrow.png',
    '/static/icons/copy.png',
    '/static/icons/app.png'
];

// Initialize cache
async function initCache() {
    // Check if Service Worker and Cache API are supported
    if (!('caches' in window)) {
        console.log('Cache API not supported');
        return;
    }

    try {
        // Open cache
        const cache = await caches.open(CACHE_NAME);
        
        // Add resources to cache
        await cache.addAll(CACHE_URLS);
        console.log('Static resources cached successfully');
        
        // Clean up old caches
        const cacheNames = await caches.keys();
        await Promise.all(
            cacheNames
                .filter(name => name.startsWith('winotp-static-') && name !== CACHE_NAME)
                .map(name => caches.delete(name))
        );
    } catch (error) {
        console.error('Error initializing cache:', error);
    }
}

// Fetch resource from cache first, then network
async function fetchWithCache(url) {
    // Check if Cache API is supported
    if (!('caches' in window)) {
        return fetch(url);
    }

    try {
        // Try to get from cache first
        const cache = await caches.open(CACHE_NAME);
        const cachedResponse = await cache.match(url);
        
        if (cachedResponse) {
            // Return cached response and update cache in background
            updateCacheInBackground(cache, url);
            return cachedResponse;
        }
        
        // If not in cache, fetch from network and cache
        const networkResponse = await fetch(url);
        
        // Only cache successful responses
        if (networkResponse.ok) {
            // Clone the response before caching it
            cache.put(url, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Error fetching with cache:', error);
        // Fall back to regular fetch
        return fetch(url);
    }
}

// Update cache in background
async function updateCacheInBackground(cache, url) {
    try {
        const networkResponse = await fetch(url);
        
        // Only update cache if response is OK
        if (networkResponse.ok) {
            await cache.put(url, networkResponse);
        }
    } catch (error) {
        console.error('Error updating cache in background:', error);
    }
}

// Initialize cache when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Don't cache on pages with TOTP codes
    if (!window.location.pathname.includes('/api/tokens')) {
        initCache();
    }
    
    // Add event listener for page navigation
    document.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            // Prefetch the page if it's an internal link
            const href = link.getAttribute('href');
            if (href && href.startsWith('/') && !href.includes('/api/')) {
                const prefetchLink = document.createElement('link');
                prefetchLink.rel = 'prefetch';
                prefetchLink.href = href;
                document.head.appendChild(prefetchLink);
            }
        });
    });
}); 