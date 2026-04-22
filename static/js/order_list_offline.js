// order_list_offline.js

const loadOfflineOrders = async () => {
    // Only run if we are on the orders list page
    const container = document.getElementById('orders-list-container');
    if (!container) return;

    // Remove existing offline cards
    container.querySelectorAll('.offline-order-card').forEach(el => el.remove());

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

    const getOrderTypeName = (id) => {
        if (!id) return 'Unknown Type';
        // OrderType lookup
        return masterData.order_types && masterData.order_types[id] ? masterData.order_types[id].order_type : `Type #${id}`;
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
            
            // Filter for orders
            const offlineOrders = items.filter(item => item.url.includes('add-order'));

            if (offlineOrders.length > 0) {
                // Sort by timestamp ascending so the newest ends up on top after prepend/insert
                offlineOrders.sort((a, b) => a.timestamp - b.timestamp);
                renderOfflineOrders(offlineOrders, container, getCustomerName, getOrderTypeName);
            }
        };
    };
};

document.addEventListener('DOMContentLoaded', loadOfflineOrders);

// Listen for sync completion to refresh list
document.addEventListener('offline-sync-completed', (e) => {
    if (e.detail.remaining === 0) {
        // If on Sales & Orders, reload with Sales tab so new sale is visible
        if (window.location.pathname.indexOf('sales-and-orders') !== -1) {
            window.location.href = window.location.pathname + '?tab=sales';
        } else {
            window.location.reload();
        }
    } else {
        loadOfflineOrders();
    }
});

function renderOfflineOrders(orders, container, getCustomerName, getOrderTypeName) {
    orders.forEach(order => {
        const data = order.data;
        
        // Extract basic info
        const customerId = data['customer'];
        const customerName = getCustomerName(customerId);
        const orderTypeId = data['order_type'];
        const orderTypeName = getOrderTypeName(orderTypeId);
        const quantity = data['quantity'] || '?';
        const createdDate = data['created_date'] ? new Date(data['created_date']).toLocaleString() : new Date(order.timestamp).toLocaleString();
        const status = data['status'] || 'Pending';
        const isPaid = data['is_paid'] === 'on';
        const paidAmount = data['paid_amount'] || '';
        const paymentNote = data['payment_note'] || '';
        const note = data['note'] || '';
        
        // Badge Colors (matching template logic roughly)
        let badgeClass = 'bg-gray-400 text-slate-700';
        if (status === 'Pending') badgeClass = 'bg-red-500 text-white';
        else if (status === 'In Progress') badgeClass = 'bg-orange-300 text-black';
        else if (status === 'Completed') badgeClass = 'bg-green-500 text-black';

        // Payment Badge
        let paymentBadge = '';
        if (isPaid) {
            paymentBadge = '<span class="px-2 py-1 rounded text-white bg-green-600 text-xs">paid</span>';
        } else {
            paymentBadge = '<span class="px-2 py-1 rounded text-white bg-red-600 text-xs">unpaid</span>';
        }

        const cardHtml = `
      <div class="offline-order-card bg-orange-50 border-2 border-orange-300 text-slate-700 shadow rounded-md mt-6 w-full max-w-3xl relative">
        <div class="absolute top-0 right-0 bg-orange-500 text-white text-xs font-bold px-2 py-1 rounded-bl-md">
            OFFLINE - PENDING SYNC
        </div>

        <div class="flex justify-between items-center p-2 bg-orange-200 rounded-t-lg text-sm border-b border-orange-300">
          <div class="flex flex-col text-left text-slate-800">
            <p>
              Order#: <span class="font-medium text-md italic">Pending</span>
              | <span>${createdDate}</span>
            </p>
            <p class="font-medium text-lg">${customerName}</p>
          </div>
          <div>
            <!-- Status Badge -->
            <button class="inline-flex w-full justify-center gap-x-1.5 rounded-md px-3 py-2 text-sm font-semibold ${badgeClass} cursor-not-allowed opacity-80" disabled>
              ${status}
            </button>
          </div>
        </div>
        
        <!-- Card Body -->
        <div class="overflow-x-auto p-4">
          <table class="min-w-full text-sm">
            <thead class="bg-orange-100">
              <tr class="text-left">
                <th class="px-3 py-2 border-b border-orange-200 text-left">Qty</th>
                <th class="px-3 py-2 border-b border-orange-200 text-left">Order type</th>
                <th class="px-3 py-2 border-b border-orange-200 text-left">Payment</th>
                <th class="px-3 py-2 border-b border-orange-200 text-left">Posted by</th>
              </tr>
            </thead>
            <tbody>
              <tr class="text-left">
                <td class="px-3 py-2 border-b border-orange-200">${quantity}</td>
                <td class="px-3 py-2 border-b border-orange-200">${orderTypeName}</td>
                <td class="px-3 py-2 border-b border-orange-200">
                  ${paymentBadge}
                </td>
                <td class="px-3 py-2 border-b border-orange-200 italic">Me (Offline)</td>
              </tr>
              ${isPaid && paidAmount ? `
              <tr class="text-left">
                <th class="px-3 py-2 border-b border-orange-200">Paid amount:</th>
                <td class="px-3 py-2 border-b border-orange-200">${paidAmount}</td>
              </tr>` : ''}
              ${paymentNote ? `
              <tr class="text-left">
                <th class="px-3 py-2 border-b border-orange-200">Payment note:</th>
                <td class="px-3 py-2 border-b border-orange-200">${paymentNote}</td>
              </tr>` : ''}
              ${note ? `
              <tr class="text-left">
                <th class="px-3 py-2 border-b border-orange-200">Note:</th>
                <td class="px-3 py-2 border-b border-orange-200">${note}</td>
              </tr>` : ''}
            </tbody>
          </table>
          <div class="mt-2 text-right">
            <h6 class="font-light text-xs text-orange-800">
              Will sync automatically when online.
            </h6>
          </div>
        </div>
      </div>
        `;

        // Create element
        const div = document.createElement('div');
        div.innerHTML = cardHtml.trim();
        
        // Insert at the top of the list
        // The container contains loop of orders.
        // We can prepend.
        if (container.firstChild) {
            container.insertBefore(div.firstChild, container.firstChild);
        } else {
            container.appendChild(div.firstChild);
        }
    });
}
