// Test script to check offline requests in IndexedDB
// Run this in browser console to see pending offline requests

async function checkOfflineRequests() {
    const DB_NAME = 'WrsmOfflineDB';
    const STORE_NAME = 'offline_requests';
    
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, 1);
        
        request.onsuccess = (event) => {
            const db = event.target.result;
            const tx = db.transaction(STORE_NAME, 'readonly');
            const store = tx.objectStore(STORE_NAME);
            const getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = () => {
                const items = getAllRequest.result;
                console.log(`Found ${items.length} pending offline requests:`);
                items.forEach((item, index) => {
                    console.log(`\n[${index + 1}] ${item.display_name || 'Unknown'}`);
                    console.log(`  URL: ${item.url}`);
                    console.log(`  Method: ${item.method}`);
                    console.log(`  Saved: ${new Date(item.timestamp).toLocaleString()}`);
                    console.log(`  Data:`, item.data);
                });
                resolve(items);
            };
            
            getAllRequest.onerror = () => reject(getAllRequest.error);
        };
        
        request.onerror = () => reject(request.error);
    });
}

// Function to manually trigger sync (for testing)
async function manualSync() {
    console.log('Manually triggering sync...');
    if (typeof syncOfflineRequests === 'function') {
        await syncOfflineRequests();
        console.log('Sync triggered');
    } else {
        console.error('syncOfflineRequests function not found. Make sure offline_forms.js is loaded.');
    }
}

// Export functions to window for easy console access
window.checkOfflineRequests = checkOfflineRequests;
window.manualSync = manualSync;

console.log('Offline testing helpers loaded!');
console.log('Use checkOfflineRequests() to see pending requests');
console.log('Use manualSync() to manually trigger sync');

