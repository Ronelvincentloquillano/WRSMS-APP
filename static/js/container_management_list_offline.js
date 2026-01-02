// container_management_list_offline.js

const loadOfflineRecords = async () => {
    const tableBody = document.getElementById('tableBody');
    if (!tableBody) return;

    // Remove existing offline rows
    tableBody.querySelectorAll('.offline-row, .offline-note-row').forEach(el => el.remove());

    // Load Master Data (for Customer Names)
    let masterData = {};
    try {
        const response = await fetch('/api/offline-master-data/');
        if (response.ok) {
            masterData = await response.json();
        }
    } catch (e) {
        console.warn('Could not load master data for offline display', e);
    }

    const getCustomerName = (id) => {
        if (!id) return 'Unknown Customer';
        return masterData.customers && masterData.customers[id] ? masterData.customers[id].name : `Customer #${id}`;
    };

    // Open DB
    const DB_NAME = 'WrsmOfflineDB';
    const STORE_NAME = 'offline_requests';
    const DB_VERSION = 1;

    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onsuccess = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) return;

        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const getAllReq = store.getAll();

        getAllReq.onsuccess = () => {
            const items = getAllReq.result;
            
            // Filter for container records
            const offlineRecords = items.filter(item => 
                item.url.includes('add-container') || 
                item.url.includes('add_container') 
            );

            if (offlineRecords.length > 0) {
                // Sort by timestamp ascending so that 'prepend' puts the newest on top
                offlineRecords.sort((a, b) => a.timestamp - b.timestamp);
                renderOfflineRecords(offlineRecords, tableBody, getCustomerName);
            }
        };
    };
};

document.addEventListener('DOMContentLoaded', loadOfflineRecords);

// Listen for sync completion to refresh list
document.addEventListener('offline-sync-completed', (e) => {
    if (e.detail.remaining === 0) {
        window.location.reload();
    } else {
        loadOfflineRecords();
    }
});

function renderOfflineRecords(records, tableBody, getCustomerName) {
    // We want to PREPEND these rows to the top of the table body.
    
    records.forEach(record => {
        const data = record.data;
        
        // Extract Fields
        const createdDate = data['created_date'] ? data['created_date'].replace('T', ' ') : 'Just Now';
        const customerId = data['customer'];
        const customerName = getCustomerName(customerId);
        const bflv = data['balance_from_last_visit'] || 0;
        const dc = data['delivered_container'] || 0;
        const rec = data['returned_empty_container'] || 0;
        const nb = data['new_balance'] || 0;
        const note = data['note'] || '';
        
        // Check filter
        const customerFilter = document.getElementById('customer');
        const selectedCustomer = customerFilter ? customerFilter.value : '';
        
        // Filter Logic:
        // Show if:
        // 1. No filter selected (selectedCustomer is empty)
        // 2. Filter matches Customer Name
        // 3. Customer Name is unresolved (starts with "Customer #") - Safety fallback to ensure visibility
        let shouldShow = true;
        if (selectedCustomer) {
            if (customerName.startsWith('Customer #')) {
                shouldShow = true; // Fallback: Show it because we can't be sure
            } else if (selectedCustomer !== customerName) {
                shouldShow = false;
            }
        }

        if (!shouldShow) return;

        // Row HTML
        const rowHtml = `
            <tr class="bg-orange-100 border-l-4 border-orange-500 cursor-pointer hover:bg-orange-200 transition-colors row-clickable offline-row">
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2 text-center">
                    <input type="radio" disabled title="Offline record" class="w-5 h-5 text-gray-400 border-gray-300 cursor-not-allowed">
                </td>
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2 font-medium">
                    ${createdDate} <span class="text-xs text-orange-700 block">(Offline)</span>
                </td>
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2">${customerName}</td>
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2 text-center">${bflv}</td>
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2 text-center">${dc}</td>
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2 text-center">${rec}</td>
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2 text-center font-bold">${nb}</td>
                <td class="hidden">${note}</td>
                <td class="hidden">Me (Offline)</td>
            </tr>
            ${note ? `
            <tr class="bg-orange-50 offline-note-row">
                <td class="border border-gray-300 dark:border-gray-600 px-2 py-2"></td>
                <td colspan="6" class="rounded-b-lg border border-gray-300 dark:border-gray-600 px-2 py-2 italic text-sm text-orange-800 font-medium">
                Note: ${note}
                </td>
            </tr>` : ''}
        `;

        // Use Template for robust parsing
        const template = document.createElement('template');
        template.innerHTML = rowHtml.trim();
        
        // Prepend rows (reverse order from template to keep structure)
        const rows = Array.from(template.content.querySelectorAll('tr'));
        
        // We iterate reversely to prepend "Note" then "Main Row" so "Main Row" ends up on top
        rows.reverse().forEach(child => {
            tableBody.prepend(child);
            
            // Re-bind click event for modal manually for these fresh rows
            if (child.classList.contains('row-clickable')) {
                 child.addEventListener('click', function(e) {
                      if (e.target.type === 'radio') return;

                      const cells = this.querySelectorAll('td');
                      const getText = (i) => cells[i] ? cells[i].innerText : '';
                      
                      const dateText = getText(1).replace('(Offline)', '').trim();
                      
                      const setModalText = (id, text) => {
                          const el = document.getElementById(id);
                          if(el) el.innerText = text;
                      };

                      setModalText('modalCreatedDate', dateText);
                      setModalText('modalCustomer', getText(2));
                      setModalText('modalBFLV', getText(3));
                      setModalText('modalDC', getText(4));
                      setModalText('modalREC', getText(5));
                      setModalText('modalNB', getText(6));
                      setModalText('modalNote', getText(7));
                      setModalText('modalCreatedBy', getText(8));
                      
                      const modal = document.getElementById('recordModal');
                      if(modal) {
                          modal.classList.remove('hidden');
                          modal.classList.add('flex');
                      }
                 });
            }
        });
    });
}