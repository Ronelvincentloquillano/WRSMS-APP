// static/serviceworker.js
const SW_VERSION = 'wrsm-v22';
console.log('[ServiceWorker] Initializing version:', SW_VERSION);

const CACHE_NAME = SW_VERSION;
const OFFLINE_URL = '/offline/';
const DATA_CACHE_NAME = 'wrsm-data-v1';
const OFFLINE_DATA_URL = '/api/offline-master-data/';

const ASSETS_TO_CACHE = [
    OFFLINE_URL,
    OFFLINE_DATA_URL,
    '/static/css/output.css',
    '/static/css/styles.css',
    '/static/js/main.js',
    '/static/js/offline_forms.js',
    '/static/img/SDR_thumbnail.png',
    '/static/img/SDR.png',
    '/static/manifest.json',
    '/', 
    '/dashboard/',
    '/sales/', 
    '/add-sales/',
    '/add-order/',
    '/add-customer/',
    '/add-container-inventory/',
    '/customers/',
    '/orders/',
    '/container-inventory-list/',
    // Ionicons
    '/static/ionicons/ionicons.esm.js',
    '/static/ionicons/p-7a41fcdf.entry.js',
    '/static/ionicons/p-BKJPfAGl.js',
    '/static/ionicons/p-DQuL1Twl.js',
    '/static/ionicons/p-Z3yp5Yym.js',
    '/static/ionicons/svg/link-outline.svg',
    '/static/ionicons/svg/cart-outline.svg',
    '/static/ionicons/svg/cash-outline.svg',
    '/static/ionicons/svg/people-outline.svg',
    '/static/ionicons/svg/card-outline.svg',
    '/static/ionicons/svg/sync-outline.svg',
    '/static/ionicons/svg/water-outline.svg',
    '/static/ionicons/svg/settings-outline.svg',
    '/static/ionicons/svg/home-outline.svg',
    '/static/ionicons/svg/add-circle-outline.svg',
    '/static/ionicons/svg/create-outline.svg',
    '/static/ionicons/svg/chevron-down-outline.svg',
    '/static/ionicons/svg/add-outline.svg',
    '/static/ionicons/svg/sync-circle-outline.svg',
    '/static/ionicons/svg/filter-circle-outline.svg',
];

// Helper: Fetch Master Data from Cache
async function getMasterData() {
    try {
        const cache = await caches.open(CACHE_NAME);
        const response = await cache.match(OFFLINE_DATA_URL);
        if (response) {
            return await response.json();
        }
    } catch (e) {
        console.error('[ServiceWorker] Error getting master data:', e);
    }
    return null;
}

// Install Event: Cache core assets with error handling
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Install', SW_VERSION);
    self.skipWaiting(); // Force activation
    
    event.waitUntil(
        caches.open(CACHE_NAME).then(async (cache) => {
            console.log('[ServiceWorker] Caching App Shell');
            
            // Try to cache each asset individually
            for (const asset of ASSETS_TO_CACHE) {
                try {
                    await cache.add(asset);
                } catch (error) {
                    console.warn(`[ServiceWorker] Failed to cache ${asset}:`, error);
                }
            }
        })
    );
});

// Activate Event: Clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activate');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME && cacheName !== DATA_CACHE_NAME) {
                        console.log('[ServiceWorker] Removing old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch Event: Network First strategy
self.addEventListener('fetch', (event) => {
    // Skip cross-origin requests
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }

    const requestUrl = new URL(event.request.url);

    // 1. AJAX Interception for Offline Mode
    if (requestUrl.pathname.includes('/ajax/')) {
        event.respondWith(
            fetch(event.request)
                .catch(async () => {
                    console.log('[ServiceWorker] Network failed, mocking AJAX response from cache');
                    const masterData = await getMasterData();
                    
                    if (!masterData) {
                        return new Response(JSON.stringify({ error: 'Offline data not available' }), {
                            headers: { 'Content-Type': 'application/json' }
                        });
                    }

                    const params = requestUrl.searchParams;
                    let responseBody = {};

                    if (requestUrl.pathname.includes('get-customer-data')) {
                        const id = params.get('id_customer');
                        const cData = masterData.customers[id];
                        if (cData) {
                            responseBody = {
                                ...cData,
                                station_default_order_type: masterData.station_settings.default_order_type_pk
                            };
                        } else {
                             responseBody = { error: 'Customer not found' };
                        }
                    } 
                    else if (requestUrl.pathname.includes('get-ordertype-data')) {
                        const id = params.get('id_order_type');
                        const otData = masterData.order_types[id];
                        if (otData) {
                            responseBody = {
                                ...otData,
                                sys_default_ot: masterData.station_settings.default_order_type_name
                            };
                        } else {
                            responseBody = { error: 'OrderType not found' };
                        }
                    }
                    else if (requestUrl.pathname.includes('get-product-data')) {
                        const id = params.get('id_product');
                        const pData = masterData.products[id];
                        if (pData) {
                            responseBody = { ...pData };
                        } else {
                            responseBody = { error: 'Product not found' };
                        }
                    }
                    else if (requestUrl.pathname.includes('get-jugsize-data')) {
                        const id = params.get('size');
                        const jData = masterData.jug_sizes[id];
                        if (jData) {
                            responseBody = { ...jData };
                        } else {
                            responseBody = { error: 'JugSize not found' };
                        }
                    } 
                    else if (requestUrl.pathname.includes('get-container-balance')) {
                        const id = params.get('id_customer');
                        const balance = masterData.container_balances[id];
                        console.log(`[ServiceWorker] Container Balance Lookup - ID: ${id}, Balance: ${balance}`);
                        
                        responseBody = { 
                            bflv: (balance !== undefined && balance !== null) ? balance : null 
                        }; 
                    }

                    return new Response(JSON.stringify(responseBody), {
                        headers: { 'Content-Type': 'application/json' }
                    });
                })
        );
        return;
    }

    // 2. Navigation Requests (HTML pages)
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    // Cache the fresh version
                    if (networkResponse && networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return networkResponse;
                })
                .catch(() => {
                    // Network failed, try cache
                    return caches.match(event.request)
                        .then((cachedResponse) => {
                            if (cachedResponse) {
                                return cachedResponse;
                            }
                            // Fallback to offline page
                            return caches.match(OFFLINE_URL);
                        });
                })
        );
        return;
    }

    // 3. Static Assets (JS, CSS, Images) + Master Data
    if (
        requestUrl.pathname.startsWith('/static/') ||
        requestUrl.pathname.startsWith('/media/') ||
        requestUrl.pathname === OFFLINE_DATA_URL
    ) {
        event.respondWith(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.match(event.request).then((cachedResponse) => {
                    // Strategy: Stale-While-Revalidate
                    const fetchPromise = fetch(event.request).then((networkResponse) => {
                        if (networkResponse && networkResponse.status === 200) {
                            cache.put(event.request, networkResponse.clone());
                        }
                        return networkResponse;
                    }).catch((err) => {
                        console.warn('[ServiceWorker] Fetch failed for asset', event.request.url);
                    });

                    if (cachedResponse) {
                        return cachedResponse; 
                    }
                    return fetchPromise;
                });
            })
        );
        return;
    }

    // 4. Default
    event.respondWith(
        fetch(event.request).catch(() => {
            // Optional
        })
    );
});