// sales_list_offline.js

const loadOfflineSales = async () => {
    // Only run if we are on the sales list page
    const container = document.getElementById('sales-list-container');
    if (!container) return;

    // Remove existing offline cards to prevent duplicates on refresh
    container.querySelectorAll('.offline-sales-card').forEach(el => el.remove());

    // Load Master Data (from SW Cache if offline)
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

    const getProductName = (id) => {
        if (!id) return 'Unknown Product';
        return masterData.products && masterData.products[id] ? masterData.products[id].product_name : `Product #${id}`;
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
            
            // Filter for sales
            // URL might end with /add-sales/
            const offlineSales = items.filter(item => item.url.includes('add-sales'));

            if (offlineSales.length > 0) {
                // Sort by timestamp ascending so the newest ends up on top after prepend/insert
                offlineSales.sort((a, b) => a.timestamp - b.timestamp);
                renderOfflineSales(offlineSales, container, getCustomerName, getProductName);
            } else {
                // If no offline items left, show the "No sales records" if there are no online ones either
                const onlineCards = container.querySelectorAll('.bg-white.text-slate-700.shadow');
                const noRec = container.querySelector('.text-center.bg-white.shadow');
                if (onlineCards.length === 0 && noRec) {
                    noRec.style.display = 'block';
                }
            }
        };
    };
};

document.addEventListener('DOMContentLoaded', loadOfflineSales);

// Listen for sync completion to refresh list
document.addEventListener('offline-sync-completed', (e) => {
    console.log('Sync completed event received, refreshing list...', e.detail);
    
    // If all records synced, we might want to reload the whole page to get real data from server
    if (e.detail.remaining === 0) {
        window.location.reload();
    } else {
        // Just refresh the offline part
        loadOfflineSales();
    }
});

function renderOfflineSales(sales, container, getCustomerName, getProductName) {
    // Find the insertion point: We want to append to the list of cards.
    // The container has a header row (Add/Edit/Delete buttons) then cards.
    // We can just append to the container.

    sales.forEach(sale => {
        const data = sale.data;
        
        // Extract basic info
        const customerId = data['customer'];
        const customerName = getCustomerName(customerId);
        // Use user-provided date if available (e.g. retroactive sales), else submission time
        const createdDate = data['created_date'] 
            ? new Date(data['created_date']).toLocaleString() 
            : new Date(sale.timestamp).toLocaleString();
        const orderType = "Offline Submission"; 
        
        // Extract Items
        // Formset items are flattened: sales_items-0-product, sales_items-0-quantity, etc.
        const totalForms = parseInt(data['sales_items-TOTAL_FORMS'] || 0);
        let itemsHtml = '';
        let totalQty = 0;
        let subTotal = 0.0;

        for (let i = 0; i < totalForms; i++) {
            // Check if deleted
            if (data[`sales_items-${i}-DELETE`] === 'on') continue;

            const prodId = data[`sales_items-${i}-product`];
            if (!prodId) continue;

            const prodName = getProductName(prodId);
            const qty = parseFloat(data[`sales_items-${i}-quantity`] || 0);
            const unitPrice = parseFloat(data[`sales_items-${i}-unit_price`] || 0);
            const total = parseFloat(data[`sales_items-${i}-total`] || 0);
            const note = data[`sales_items-${i}-note`] || '';

            totalQty += qty;
            subTotal += total;

            itemsHtml += `
              <tr>
                <td colspan="2" class="px-3 py-2 border-b">
                  ${prodName}${note ? ` (${note})` : ''}
                </td>
                <td class="px-3 py-2 border-b">${qty}</td>
                <td class="px-3 py-2 border-b">${unitPrice.toFixed(2)}</td>
                <td class="px-3 py-2 border-b">${total.toFixed(2)}</td>
              </tr>
            `;
        }

        const cardHtml = `
      <div class="offline-sales-card bg-orange-50 border-2 border-orange-300 text-slate-700 shadow rounded-md mt-6 w-full max-w-3xl relative">
        <div class="absolute top-0 right-0 bg-orange-500 text-white text-xs font-bold px-2 py-1 rounded-bl-md">
            OFFLINE - PENDING SYNC
        </div>
        
        <!-- Card Header -->
        <div class="border-b border-orange-200 p-4">
          <div class="flex items-center gap-2">
            <!-- Disabled selector for offline items -->
            <input type="radio" disabled class="w-5 h-5 text-gray-400 bg-gray-100 border-gray-300 cursor-not-allowed">
            <h4 class="text-xl font-semibold m-0 text-slate-800">
                ${customerName}
            </h4>
          </div>

          <div class="mt-1 text-gray-600">
            <div class="flex flex-row justify-between items-center">
              <div>
                <h6>
                  <span class="font-bold">Pending</span> | ${createdDate} | ${orderType}
                </h6>
              </div>
            </div>
            <div class="flex items-center gap-5 mt-1">
               <span class="inline-block px-2 py-1 bg-gray-400 text-white text-xs rounded">Sync Required</span>
            </div>
          </div>
          
          ${data.note ? `<p class="text-gray-700 text-lg mt-2 italic">Note: ${data.note}</p>` : ''}
        </div>

        <!-- Card Body -->
        <div class="p-4 overflow-x-auto">
          <table class="min-w-full border border-orange-200 text-sm">
            <thead class="bg-orange-100">
              <tr>
                <th colspan="5" class="px-3 py-2 border-b border-orange-200 font-semibold">ORDERED PRODUCTS</th>
              </tr>
              <tr>
                <th colspan="2" class="px-3 py-2 border-b border-orange-200 text-left">Product</th>
                <th class="px-3 py-2 border-b border-orange-200">Qty</th>
                <th class="px-3 py-2 border-b border-orange-200">Unit price</th>
                <th class="px-3 py-2 border-b border-orange-200">Total</th>
              </tr>
            </thead>

            <tbody>
              ${itemsHtml}

              <tr class="font-bold bg-orange-100">
                <td colspan="2" class="px-3 py-2 text-right border-b border-orange-200">Total QTY:</td>
                <td class="px-3 py-2 border-b border-orange-200">${totalQty}</td>
                <td class="px-3 py-2 text-right border-b border-orange-200">Subtotal:</td>
                <td class="px-3 py-2 border-b border-orange-200">
                  ${subTotal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </td>
              </tr>
            </tbody>
          </table>
          <div class="mt-2">
            <h6 class="font-light text-xs text-orange-800">
              Added offline. Will sync automatically when online.
            </h6>
          </div>
        </div>
      </div>
        `;

        // Create element
        const div = document.createElement('div');
        div.innerHTML = cardHtml.trim(); // wrapper
        
        // Use insertAdjacentElement to put it at the top of the list (after header)
        // The container has flex-col.
        // We want to put it *before* the first real sales card or at the beginning.
        // The container has: 
        // 1. Controls (Add/Edit/Delete) -> .flex.flex-col.md:flex-row...
        // 2. Sales List cards ...
        
        // Let's find the first sales card.
        const firstCard = container.querySelector('.bg-white.text-slate-700.shadow');
        if (firstCard) {
            container.insertBefore(div.firstChild, firstCard);
        } else {
            // No online sales, or just the "No sales record found" div
            const noRec = container.querySelector('.text-center.bg-white.shadow');
            if (noRec) {
                noRec.style.display = 'none'; // Hide "No records" if we have offline ones
            }
            container.appendChild(div.firstChild);
        }
    });
}
