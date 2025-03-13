/**
 * WinOTP Service Worker
 * 
 * This service worker provides offline capabilities and improved caching
 * for the WinOTP application.
 */

// Cache version - increment when resources change
const CACHE_VERSION = '1.0.0';
const STATIC_CACHE_NAME = `winotp-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE_NAME = `winotp-dynamic-${CACHE_VERSION}`;

// Resources to cache on install
const STATIC_RESOURCES = [
    '/',
    '/settings',
    '/add_token',
    '/static/css/bootstrap.min.css',
    '/static/css/style.css',
    '/static/css/icons.css',
    '/static/css/optimize.css',
    '/static/js/jquery-3.6.0.min.js',
    '/static/js/bootstrap.bundle.min.js',
    '/static/js/app.js',
    '/static/js/cache-manager.js',
    '/static/icons/search.png',
    '/static/icons/sort_asc.png',
    '/static/icons/sort_desc.png',
    '/static/icons/settings.png',
    '/static/icons/plus.png',
    '/static/icons/back_arrow.png',
    '/static/icons/copy.png',
    '/static/icons/app.png',
    '/static/icons/delete.png',
    '/static/icons/edit.png',
    '/static/icons/qr-code.png'
];

// URLs that should never be cached
const NEVER_CACHE_URLS = [
    '/api/tokens',
    '/api/ntp_status',
    '/api/ntp_sync'
];

// Install event - cache static resources
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then(cache => {
                console.log('Caching static resources');
                return cache.addAll(STATIC_RESOURCES);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(name => {
                            return (name.startsWith('winotp-static-') && name !== STATIC_CACHE_NAME) ||
                                   (name.startsWith('winotp-dynamic-') && name !== DYNAMIC_CACHE_NAME);
                        })
                        .map(name => {
                            console.log('Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache, then network
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Skip URLs that should never be cached
    if (NEVER_CACHE_URLS.some(u => url.pathname.includes(u))) {
        return;
    }
    
    // Skip cross-origin requests
    if (url.origin !== self.location.origin) {
        return;
    }
    
    // Cache strategy based on request type
    if (url.pathname.startsWith('/static/')) {
        // Cache-first strategy for static resources
        event.respondWith(cacheFirstStrategy(event.request));
    } else if (url.pathname.startsWith('/api/')) {
        // Network-first strategy for API requests
        event.respondWith(networkFirstStrategy(event.request));
    } else {
        // Stale-while-revalidate for HTML pages
        event.respondWith(staleWhileRevalidateStrategy(event.request));
    }
});

// Cache-first strategy
async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        // Return cached response and update cache in background
        updateCacheInBackground(request);
        return cachedResponse;
    }
    
    // If not in cache, fetch from network and cache
    return fetchAndCache(request, STATIC_CACHE_NAME);
}

// Network-first strategy
async function networkFirstStrategy(request) {
    try {
        // Try network first
        const response = await fetch(request);
        
        // Cache successful responses
        if (response.ok && response.status !== 204) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        // If network fails, try cache
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // If not in cache, return error response
        return new Response('Network error occurred', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
                'Content-Type': 'text/plain'
            })
        });
    }
}

// Stale-while-revalidate strategy
async function staleWhileRevalidateStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    // Update cache in background regardless of cache hit
    const fetchPromise = fetchAndCache(request, DYNAMIC_CACHE_NAME);
    
    // Return cached response if available, otherwise wait for network
    return cachedResponse || fetchPromise;
}

// Fetch and cache helper
async function fetchAndCache(request, cacheName) {
    try {
        const response = await fetch(request);
        
        // Only cache successful responses
        if (response.ok && response.status !== 204) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        console.error('Fetch failed:', error);
        throw error;
    }
}

// Update cache in background
async function updateCacheInBackground(request) {
    try {
        const response = await fetch(request);
        
        // Only update cache if response is OK
        if (response.ok && response.status !== 204) {
            const cache = await caches.open(STATIC_CACHE_NAME);
            await cache.put(request, response);
        }
    } catch (error) {
        console.error('Error updating cache in background:', error);
    }
} 