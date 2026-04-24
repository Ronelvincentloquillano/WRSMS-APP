// offline_forms.js

const DB_NAME = 'WrsmOfflineDB';
const STORE_NAME = 'offline_requests';
const DB_VERSION = 1;
let syncInProgress = false;

function generateOfflineRequestId() {
    if (window.crypto && window.crypto.randomUUID) {
        return window.crypto.randomUUID();
    }
    return 'offline-' + Date.now() + '-' + Math.random().toString(16).slice(2);
}

function stableStringify(value) {
    if (Array.isArray(value)) {
        return '[' + value.map(stableStringify).join(',') + ']';
    }
    if (value && typeof value === 'object') {
        return '{' + Object.keys(value).sort().map((k) => JSON.stringify(k) + ':' + stableStringify(value[k])).join(',') + '}';
    }
    return JSON.stringify(value);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const openDB = () => {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
            }
        };
        request.onsuccess = (event) => {
            resolve(event.target.result);
        };
        request.onerror = (event) => {
            reject('Database error: ' + event.target.errorCode);
        };
    });
};

const saveOfflineRequest = async (url, method, formData) => {
    try {
        const db = await openDB();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);

        // Convert FormData to plain object
        const data = {};
        formData.forEach((value, key) => {
            // Django formsets use unique keys (form-0-field), so simple assignment works for most.
            // If strictly needed, we can handle duplicate keys here.
            data[key] = value;
        });
        if (!data.offline_request_id) {
            data.offline_request_id = generateOfflineRequestId();
        }

        const requestRecord = {
            url: url,
            method: method,
            data: data,
            timestamp: Date.now(),
            display_name: document.title // To show user what is pending
        };

        // Prevent accidental duplicate queueing from rapid double-submit/retry.
        const allReq = store.getAll();
        const existingItems = await new Promise((resolve) => {
            allReq.onsuccess = () => resolve(allReq.result || []);
            allReq.onerror = () => resolve([]);
        });
        const newSignature = stableStringify({
            url: requestRecord.url,
            method: requestRecord.method,
            data: requestRecord.data,
        });
        const duplicate = existingItems.some((item) => {
            const oldSignature = stableStringify({
                url: item.url,
                method: item.method,
                data: item.data,
            });
            const withinWindow = Math.abs((requestRecord.timestamp || 0) - (item.timestamp || 0)) < 15000;
            return withinWindow && oldSignature === newSignature;
        });
        if (duplicate) {
            return { saved: false, duplicate: true };
        }

        store.add(requestRecord);
        
        return new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve({ saved: true, duplicate: false });
            tx.onerror = () => reject(tx.error);
        });
    } catch (e) {
        console.error("Error saving offline request", e);
        throw e;
    }
};

const syncOfflineRequests = async () => {
    if (!navigator.onLine) return;
    if (syncInProgress) {
        console.log('Offline sync already running. Skipping duplicate trigger.');
        return;
    }
    syncInProgress = true;

    try {
        const db = await openDB();
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.getAll();

        request.onsuccess = async () => {
            const items = request.result;
            if (items.length === 0) return;

            console.log(`Attempting to sync ${items.length} items...`);
            // Don't show "Syncing X offline records..." on auto sync — only show result at the end

            for (const item of items) {
                try {
                    // Refresh CSRF Token from cookie
                    const csrftoken = getCookie('csrftoken');
                    
                    // Reconstruct FormData (or URLSearchParams)
                    const body = new URLSearchParams();
                    for (const key in item.data) {
                        if (key === 'csrfmiddlewaretoken') {
                            body.append(key, csrftoken); // Update token
                        } else {
                            body.append(key, item.data[key]);
                        }
                    }

                    const response = await fetch(item.url, {
                        method: item.method,
                        credentials: 'same-origin',
                        headers: {
                            'X-CSRFToken': csrftoken,
                            'Content-Type': 'application/x-www-form-urlencoded' // Standard form post
                        },
                        body: body,
                        redirect: 'follow'
                    });

                    // Success: 2xx, or redirect (302) meaning server processed and redirected
                    const success = response.ok || response.redirected || (response.status >= 200 && response.status < 400);
                    if (success) {
                        const deleteTx = db.transaction(STORE_NAME, 'readwrite');
                        deleteTx.objectStore(STORE_NAME).delete(item.id);
                        console.log(`Synced item ${item.id}`);
                    } else {
                        console.error(`Failed to sync item ${item.id}`, response.status, response.statusText);
                    }
                } catch (err) {
                    console.error("Network error during sync", err);
                }
            }
            
            // Check remaining
            const checkTx = db.transaction(STORE_NAME, 'readonly');
            const checkReq = checkTx.objectStore(STORE_NAME).count();
            checkReq.onsuccess = () => {
                // Dispatch event to notify lists to refresh
                document.dispatchEvent(new CustomEvent('offline-sync-completed', { 
                    detail: { remaining: checkReq.result } 
                }));

                if (checkReq.result === 0) {
                    showToast('All offline records synced successfully!', 'success');
                    const oldToast = document.getElementById('offline-warning-toast');
                    if (oldToast) oldToast.remove();
                } else {
                    // Show warning with Retry and Discard so user can clear stuck records
                    showToastWithRetryAndDiscard(
                        `${checkReq.result} records pending sync.`,
                        () => syncOfflineRequests()
                    );
                }
            };
        };
    } catch (e) {
        console.error("Error during sync process", e);
    } finally {
        syncInProgress = false;
    }
};

// Global helper to clear queue (skipConfirm = true when already confirmed by caller)
window.clearOfflineQueue = async (skipConfirm = false) => {
    if (!skipConfirm && !confirm("Are you sure you want to discard all unsynced offline records? This cannot be undone.")) return;

    try {
        const db = await openDB();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const req = store.clear();
        
        req.onsuccess = () => {
            showToast('Offline queue cleared.', 'success');
            // Remove the stuck toast if present
            const oldToast = document.getElementById('offline-warning-toast');
            if (oldToast) oldToast.remove();
        };
        req.onerror = () => {
            showToast('Failed to clear queue.', 'error');
        };
    } catch (e) {
        console.error("Error clearing queue", e);
    }
};

// Toast Notification Helper
function showToast(message, type='info') {
    // Create or reuse a toast container
    let container = document.getElementById('offline-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'offline-toast-container';
        container.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    
    // Default Tailwind mappings
    const bgColors = {
        'info': 'bg-blue-600',
        'success': 'bg-green-600',
        'warning': 'bg-orange-500', 
        'error': 'bg-red-600'
    };
    
    toast.className = `${bgColors[type] || 'bg-gray-800'} text-white px-6 py-3 rounded shadow-lg transition-opacity duration-500 font-bold`;
    
    // Specific override for "offline" (warning) to ensure orange background and black text
    if (type === 'warning') {
        toast.style.backgroundColor = '#f97316'; // Orange
        toast.style.color = '#000000'; // Black
    }

    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// Toast with Action Button (for stuck records)
function showToastWithAction(message, type, actionText, actionCallback) {
    let container = document.getElementById('offline-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'offline-toast-container';
        container.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(container);
    }
    
    const oldToast = document.getElementById('offline-warning-toast');
    if (oldToast) oldToast.remove();

    const toast = document.createElement('div');
    toast.id = 'offline-warning-toast';
    toast.style.backgroundColor = '#f97316'; // Orange
    toast.style.color = '#000000';
    toast.className = `px-6 py-3 rounded shadow-lg font-bold flex flex-col gap-2`;
    
    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;
    toast.appendChild(msgSpan);
    
    const btn = document.createElement('button');
    btn.textContent = actionText;
    btn.className = 'bg-black text-white px-3 py-1 rounded text-sm hover:bg-gray-800 self-end transition-all';
    btn.onclick = () => {
        if (btn.disabled) return;
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Syncing...';
        btn.classList.add('opacity-50', 'cursor-not-allowed');
        actionCallback();
    };
    toast.appendChild(btn);

    container.appendChild(toast);
}

// Toast with Retry + Discard for pending sync (so user can clear stuck records)
function showToastWithRetryAndDiscard(message, retryCallback) {
    let container = document.getElementById('offline-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'offline-toast-container';
        container.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(container);
    }

    const oldToast = document.getElementById('offline-warning-toast');
    if (oldToast) oldToast.remove();

    const toast = document.createElement('div');
    toast.id = 'offline-warning-toast';
    toast.style.backgroundColor = '#f97316';
    toast.style.color = '#000000';
    toast.className = 'px-6 py-3 rounded shadow-lg font-bold flex flex-col gap-2';

    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;
    toast.appendChild(msgSpan);

    const btnRow = document.createElement('div');
    btnRow.className = 'flex gap-2 self-end';

    const retryBtn = document.createElement('button');
    retryBtn.textContent = 'Retry';
    retryBtn.className = 'bg-black text-white px-3 py-1 rounded text-sm hover:bg-gray-800 transition-all';
    retryBtn.onclick = () => {
        if (retryBtn.disabled) return;
        retryBtn.disabled = true;
        retryBtn.textContent = 'Syncing...';
        retryBtn.classList.add('opacity-50', 'cursor-not-allowed');
        retryCallback();
    };

    const discardBtn = document.createElement('button');
    discardBtn.textContent = 'Discard';
    discardBtn.className = 'bg-gray-700 text-white px-3 py-1 rounded text-sm hover:bg-gray-600 transition-all';
    discardBtn.onclick = () => {
        if (!confirm('Discard all unsynced records? They cannot be recovered.')) return;
        window.clearOfflineQueue(true);
        toast.remove();
        document.dispatchEvent(new CustomEvent('offline-sync-completed', { detail: { remaining: 0 } }));
    };

    btnRow.appendChild(retryBtn);
    btnRow.appendChild(discardBtn);
    toast.appendChild(btnRow);
    container.appendChild(toast);
}

// Interceptor Setup
function setupOfflineForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn ? submitBtn.textContent : 'Submit';

        const resetButton = () => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalBtnText;
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        };

        const formData = new FormData(form);
        const url = form.action || window.location.href;
        const method = form.method || 'POST';

        // Offline: queue and block normal submit
        if (!navigator.onLine) {
            e.preventDefault();
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Submitting...';
                submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
            await handleOfflineSave(url, method, formData, form, true);
            resetButton();
            return;
        }

        // Online + native submit: let the browser POST (handles 302 redirects and cookies reliably)
        if (form.hasAttribute('data-native-submit-online')) {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Submitting...';
                submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
            return;
        }

        e.preventDefault();

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';
            submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }

        // Network (fetch) path for forms that stay on SPA-style handling
        try {
            const response = await fetch(url, {
                method: method,
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            if (response.ok || response.redirected) {
                if (response.redirected) {
                    window.location.href = response.url;
                } else {
                    // If returns 200 OK (no redirect), it usually means validation errors (re-rendering form)
                    // or a success message in JSON (if API).
                    // For Django Template Views, it returns HTML.
                    const text = await response.text();
                    
                    // Naive check: does it look like JSON?
                    try {
                        const json = JSON.parse(text);
                        // If JSON success
                        if (json.success) {
                            showToast('Saved successfully!', 'success');
                            form.reset();
                            resetButton();
                            return; 
                        }
                    } catch (e) {
                        // Not JSON, assume HTML
                    }

                    // Replace document to show validation errors or success page
                    document.open();
                    document.write(text);
                    document.close();
                }
            } else {
                // 503 from service worker/network fallback should still be queued offline.
                // This covers cases where navigator.onLine may still report true.
                if (response.status === 503) {
                    console.warn('503 received; saving request to offline queue.');
                    await handleOfflineSave(url, method, formData, form, true);
                    resetButton();
                    return;
                }
                // Other server errors: keep existing behavior.
                if (response.status >= 500) {
                     console.warn('Server error 5xx.');
                     showToast('Server error. Please try again.', 'error');
                     resetButton();
                     return;
                }
                // 400 Bad Request (Validation Error) - render response to show errors
                const text = await response.text();
                document.open();
                document.write(text);
                document.close();
            }
        } catch (error) {
            // Treat fetch/network failures as offline-capable for POST-style form submits.
            // navigator.onLine can be true while the request path is still unreachable.
            const normalizedMethod = String(method || 'POST').toUpperCase();
            const isMutation = normalizedMethod !== 'GET' && normalizedMethod !== 'HEAD';
            const errorText = String((error && error.message) || '');
            const isNetworkFailure =
                !navigator.onLine ||
                (error && error.name === 'TypeError') ||
                /Failed to fetch|NetworkError|Load failed/i.test(errorText);

            if (isMutation && isNetworkFailure) {
                console.warn('Request failed; saving to offline queue.', error);
                await handleOfflineSave(url, method, formData, form, !navigator.onLine);
                resetButton();
                return;
            }

            console.warn('Network request failed (online).', error);
            showToast('Network error. Please check your connection and try again.', 'error');
            resetButton();
            return;
        } finally {
             // In case of document.write, this finally block might not run on the old document, 
             // but if we are staying on page (offline save), it will.
             if (document.body.contains(form)) {
                 resetButton();
             }
        }
    });
}

async function handleOfflineSave(url, method, formData, form, isActuallyOffline) {
    try {
        const saveResult = await saveOfflineRequest(url, method, formData);
        if (saveResult && saveResult.duplicate) {
            showToast('Already saved offline. Waiting to sync when online.', 'warning');
            return;
        }
        if (isActuallyOffline) {
            showToast('Offline! Record saved locally. Will sync when online.', 'warning');
        } else {
            showToast('Server unavailable. Record saved locally and will sync when the server is back.', 'warning');
        }
        form.reset();
        
        // Auto-update datetime inputs to 'now' after reset to prevent stale timestamps
        // on subsequent submissions (fixing the "stuck time" issue).
        const now = new Date();
        // Adjust for timezone offset to match datetime-local requirement (YYYY-MM-DDTHH:MM)
        const offsetMs = now.getTimezoneOffset() * 60 * 1000;
        const localIso = new Date(now.getTime() - offsetMs).toISOString().slice(0, 16);
        
        form.querySelectorAll('input[type="datetime-local"], input[name="created_date"]').forEach(input => {
            input.value = localIso;
        });
        
        // If this is the Add Order form, leave the form page immediately (UX: "mawawala agad yung form")
        try {
            const u = (typeof url === 'string') ? url : '';
            if (u.includes('add-order')) {
                window.location.href = '/sales-and-orders/';
                return;
            }
        } catch (e) {
            // ignore
        }
    } catch (error) {
        showToast('Error saving offline record.', 'error');
        console.error(error);
    }
}

async function countPendingOfflineRequests(urlIncludes) {
    try {
        const db = await openDB();
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const all = await new Promise((resolve, reject) => {
            const req = store.getAll();
            req.onsuccess = () => resolve(req.result || []);
            req.onerror = () => reject(req.error);
        });
        return all.filter(item => (item.url || '').includes(urlIncludes)).length;
    } catch (e) {
        return 0;
    }
}

async function applyAddOrderLockFromOfflineQueue() {
    const pendingAddOrders = await countPendingOfflineRequests('add-order');
    const shouldLock = pendingAddOrders > 0;
    document.querySelectorAll('[data-add-order-link]').forEach(el => {
        if (shouldLock) el.classList.add('hidden');
    });
    document.querySelectorAll('[data-add-order-locked]').forEach(el => {
        if (shouldLock) el.classList.remove('hidden');
    });

    // If user is on Add Order page but there is a pending offline order, redirect away
    if (shouldLock && window.location.pathname.includes('add-order')) {
        window.location.href = '/sales-and-orders/';
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Sync on load
    if (navigator.onLine) {
        syncOfflineRequests();
    }

    // Sync when network returns
    window.addEventListener('online', syncOfflineRequests);

    // Setup forms if they exist on the current page
    setupOfflineForm('add_sales_form');
    setupOfflineForm('add_order_form');
    setupOfflineForm('add_customer_form');
    setupOfflineForm('add_container_management_form');
    setupOfflineForm('update_container_management_form');
    setupOfflineForm('delete_container_management_form');
    setupOfflineForm('add_payment_form');
    
    // Prime the Offline Master Data Cache
    if (navigator.onLine) {
        primeOfflineCache();
    }
    window.addEventListener('online', primeOfflineCache);

    // If there is a pending offline Add Order request, lock Add Order buttons and exit Add Order form
    applyAddOrderLockFromOfflineQueue();

    // FIX: Refresh 'created_date' fields on load to prevent stale server-side timestamps
    // from cached pages (SW or Back/Forward cache).
    // Only apply on "Add/Create" pages, avoid "Update/Edit" pages.
    const path = window.location.pathname;
    if (!path.includes('update') && !path.includes('edit')) {
        const now = new Date();
        const offsetMs = now.getTimezoneOffset() * 60 * 1000;
        const localIso = new Date(now.getTime() - offsetMs).toISOString().slice(0, 16);
        
        document.querySelectorAll('input[type="datetime-local"], input[name="created_date"]').forEach(input => {
            // Only update if it looks like a default/stale value (optional check, 
            // but forcing 'now' on create pages is usually desired behavior).
            input.value = localIso;
        });
    }
});

// Re-apply locks after sync finishes
document.addEventListener('offline-sync-completed', () => {
    applyAddOrderLockFromOfflineQueue();
});

// Helper to fetch and cache master data
async function primeOfflineCache() {
    try {
        console.log('Priming offline master data cache...');
        const response = await fetch('/api/offline-master-data/', { credentials: 'same-origin' });
        if (response.ok) {
            console.log('Offline master data cached successfully.');
        } else {
            console.warn('Failed to cache offline master data:', response.status);
        }
    } catch (e) {
        console.error('Error priming offline cache:', e);
    }
}
