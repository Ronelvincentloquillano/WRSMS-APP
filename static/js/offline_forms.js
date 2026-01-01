// offline_forms.js

const DB_NAME = 'WrsmOfflineDB';
const STORE_NAME = 'offline_requests';
const DB_VERSION = 1;

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

        const requestRecord = {
            url: url,
            method: method,
            data: data,
            timestamp: Date.now(),
            display_name: document.title // To show user what is pending
        };

        store.add(requestRecord);
        
        return new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve(true);
            tx.onerror = () => reject(tx.error);
        });
    } catch (e) {
        console.error("Error saving offline request", e);
        throw e;
    }
};

const syncOfflineRequests = async () => {
    if (!navigator.onLine) return;

    try {
        const db = await openDB();
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.getAll();

        request.onsuccess = async () => {
            const items = request.result;
            if (items.length === 0) return;

            console.log(`Attempting to sync ${items.length} items...`);
            showToast(`Syncing ${items.length} offline records...`, 'info');

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
                        headers: {
                            'X-CSRFToken': csrftoken,
                            'Content-Type': 'application/x-www-form-urlencoded' // Standard form post
                        },
                        body: body
                    });

                    if (response.ok) {
                        // Success: Delete from DB
                        const deleteTx = db.transaction(STORE_NAME, 'readwrite');
                        deleteTx.objectStore(STORE_NAME).delete(item.id);
                        console.log(`Synced item ${item.id}`);
                    } else {
                        console.error(`Failed to sync item ${item.id}`, response.statusText);
                        // Optional: Handle 400 validation errors differently?
                    }
                } catch (err) {
                    console.error("Network error during sync", err);
                }
            }
            
            // Check remaining
            const checkTx = db.transaction(STORE_NAME, 'readonly');
            const checkReq = checkTx.objectStore(STORE_NAME).count();
            checkReq.onsuccess = () => {
                if (checkReq.result === 0) {
                    showToast('All offline records synced successfully!', 'success');
                } else {
                    showToast(`${checkReq.result} records failed to sync.`, 'warning');
                }
            };
        };
    } catch (e) {
        console.error("Error during sync process", e);
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

// Interceptor Setup
function setupOfflineForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault(); // Always intercept to handle Network First strategy
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn ? submitBtn.textContent : 'Submit';

        if (submitBtn) {
             submitBtn.disabled = true;
             submitBtn.textContent = 'Submitting...';
             // Visual feedback for user
             submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }

        const formData = new FormData(form);
        const url = form.action || window.location.href;
        const method = form.method || 'POST';

        // Helper to reset button
        const resetButton = () => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalBtnText;
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        };

        // 1. Check explicit offline status first
        if (!navigator.onLine) {
             await handleOfflineSave(url, method, formData, form);
             resetButton();
             return;
        }

        // 2. Try Network
        try {
            const response = await fetch(url, {
                method: method,
                body: formData,
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
                // Server Error (5xx) -> Fallback to Offline
                if (response.status >= 500) {
                     console.warn('Server error 5xx, saving offline.');
                     await handleOfflineSave(url, method, formData, form);
                } else {
                     // 400 Bad Request (Validation Error)
                     // Render the response to show errors
                     const text = await response.text();
                     document.open();
                     document.write(text);
                     document.close();
                }
            }
        } catch (error) {
            // 3. Network Error (Fetch failed completely) -> Save Offline
            console.log('Network request failed, saving offline:', error);
            await handleOfflineSave(url, method, formData, form);
        } finally {
             // In case of document.write, this finally block might not run on the old document, 
             // but if we are staying on page (offline save), it will.
             if (document.body.contains(form)) {
                 resetButton();
             }
        }
    });
}

async function handleOfflineSave(url, method, formData, form) {
    try {
        await saveOfflineRequest(url, method, formData);
        showToast('Offline! Record saved locally. Will sync when online.', 'warning');
        form.reset();
        
        // Optional: We might want to redirect the user to the list page 
        // to mimic success, or stay on page.
        // For add_sales, staying on page to add another is good.
    } catch (error) {
        showToast('Error saving offline record.', 'error');
        console.error(error);
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
    setupOfflineForm('add_payment_form');
    
    // Prime the Offline Master Data Cache
    if (navigator.onLine) {
        primeOfflineCache();
    }
    window.addEventListener('online', primeOfflineCache);
});

// Helper to fetch and cache master data
async function primeOfflineCache() {
    try {
        console.log('Priming offline master data cache...');
        const response = await fetch('/api/offline-master-data/');
        if (response.ok) {
            console.log('Offline master data cached successfully.');
        } else {
            console.warn('Failed to cache offline master data:', response.status);
        }
    } catch (e) {
        console.error('Error priming offline cache:', e);
    }
}
