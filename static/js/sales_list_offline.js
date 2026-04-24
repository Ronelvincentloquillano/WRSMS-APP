// sales_list_offline.js
const OFFLINE_ROW_CLASS = 'offline-sales-row';
const OFFLINE_CARD_CLASS = 'offline-sales-card';

function formatMoney(v) {
    return (Number(v) || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDateLocal(value, fallbackTs) {
    const d = value ? new Date(value) : new Date(fallbackTs);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleDateString(undefined, { month: 'short', day: '2-digit', year: 'numeric' });
}

function parseOfflineSale(item, getCustomerName, getProductName) {
    const data = item.data || {};
    const customerId = data.customer;
    const customerName = customerId ? getCustomerName(customerId) : 'Walk-in';
    const dateText = formatDateLocal(data.created_date, item.timestamp);
    const orderType = data.order_type || '-';
    const note = data.note || '';

    const totalForms = parseInt(data['sales_items-TOTAL_FORMS'] || 0, 10);
    let totalQty = 0;
    let subtotal = 0;
    const itemParts = [];
    for (let i = 0; i < totalForms; i++) {
        if (data[`sales_items-${i}-DELETE`] === 'on') continue;
        const prodId = data[`sales_items-${i}-product`];
        if (!prodId) continue;
        const name = getProductName(prodId);
        const qty = parseFloat(data[`sales_items-${i}-quantity`] || 0) || 0;
        const lineTotal = parseFloat(data[`sales_items-${i}-total`] || 0) || 0;
        totalQty += qty;
        subtotal += lineTotal;
        itemParts.push(`${name} x${qty}`);
    }

    return {
        dateText,
        customerName,
        orderType,
        note,
        itemSummary: itemParts.join(', ') || '—',
        lineCount: itemParts.length,
        totalQty,
        subtotal,
    };
}

async function readPendingOfflineSales() {
    return new Promise((resolve) => {
        const request = indexedDB.open('WrsmOfflineDB', 1);
        request.onerror = () => resolve([]);
        request.onsuccess = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('offline_requests')) {
                resolve([]);
                return;
            }
            const tx = db.transaction('offline_requests', 'readonly');
            const store = tx.objectStore('offline_requests');
            const getAllReq = store.getAll();
            getAllReq.onerror = () => resolve([]);
            getAllReq.onsuccess = () => {
                const items = (getAllReq.result || []).filter((x) => String(x.url || '').includes('add-sales'));
                items.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
                resolve(items);
            };
        };
    });
}

async function loadOfflineSales() {
    const desktopTbody = document.querySelector('.hidden.md\\:block table tbody');
    const mobileGrid = document.querySelector('.mt-4.grid.gap-3.md\\:hidden');
    if (!desktopTbody && !mobileGrid) return;

    document.querySelectorAll(`.${OFFLINE_ROW_CLASS}, .${OFFLINE_CARD_CLASS}`).forEach((el) => el.remove());

    let masterData = {};
    try {
        const response = await fetch('/api/offline-master-data/');
        if (response.ok) masterData = await response.json();
    } catch (e) {
        console.warn('Could not load master data for offline display', e);
    }
    const getCustomerName = (id) => (masterData.customers && masterData.customers[id] ? masterData.customers[id].name : `Customer #${id}`);
    const getProductName = (id) => (masterData.products && masterData.products[id] ? masterData.products[id].product_name : `Product #${id}`);

    const pending = await readPendingOfflineSales();
    const noRec = document.querySelector('.mt-6.ux-card.rounded.p-5.text-center');
    if (!pending.length) {
        if (noRec && !document.querySelector('table tbody tr') && !mobileGrid?.children.length) {
            noRec.style.display = 'block';
        }
        return;
    }
    if (noRec) noRec.style.display = 'none';

    pending.forEach((entry) => {
        const sale = parseOfflineSale(entry, getCustomerName, getProductName);
        if (desktopTbody) {
            const row = document.createElement('tr');
            row.className = `${OFFLINE_ROW_CLASS} border-t border-orange-300 bg-orange-50 dark:bg-orange-900/20`;
            row.innerHTML = `
                <td class="px-3 py-2">${sale.dateText}</td>
                <td class="px-3 py-2">${sale.customerName}${sale.note ? `<div class="text-xs text-slate-500">${sale.note}</div>` : ''}</td>
                <td class="px-3 py-2">${sale.orderType}</td>
                <td class="px-3 py-2 max-w-md align-top">
                    <div class="text-sm text-slate-800 dark:text-slate-100">${sale.itemSummary}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">${sale.lineCount} line(s) · ${sale.totalQty} qty</div>
                </td>
                <td class="px-3 py-2">₱${formatMoney(sale.subtotal)}</td>
                <td class="px-3 py-2 font-semibold">₱${formatMoney(sale.subtotal)}</td>
                <td class="px-3 py-2"><span class="inline-flex items-center rounded-full bg-orange-100 text-orange-700 px-2 py-0.5 text-[11px] font-semibold">Offline - Pending Sync</span></td>
            `;
            desktopTbody.prepend(row);
        }
        if (mobileGrid) {
            const card = document.createElement('div');
            card.className = `${OFFLINE_CARD_CLASS} ux-card p-4 ring-1 ring-orange-300 bg-orange-50/80 dark:bg-orange-900/20`;
            card.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <div class="font-semibold">${sale.customerName}</div>
                        <div class="text-xs text-slate-500">${sale.dateText} | ${sale.orderType}</div>
                        <div class="mt-1"><span class="inline-flex items-center rounded-full bg-orange-100 text-orange-700 px-2 py-0.5 text-[11px] font-semibold">Offline - Pending Sync</span></div>
                    </div>
                </div>
                ${sale.note ? `<div class="text-sm mt-2 text-slate-600 dark:text-slate-300">${sale.note}</div>` : ''}
                <div class="mt-3 text-sm">
                    <div class="text-xs text-slate-500 dark:text-slate-400">Items</div>
                    <div class="text-slate-800 dark:text-slate-100 mt-0.5">${sale.itemSummary}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">${sale.lineCount} line(s) · ${sale.totalQty} qty</div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3 text-sm">
                    <div class="bg-slate-100 dark:bg-slate-600 rounded-lg p-3">
                        <div class="text-xs text-slate-500 dark:text-slate-400">Sub total</div>
                        <div class="font-semibold text-lg">₱${formatMoney(sale.subtotal)}</div>
                    </div>
                    <div class="bg-slate-100 dark:bg-slate-600 rounded-lg p-3">
                        <div class="text-xs text-slate-500 dark:text-slate-400">Total amount</div>
                        <div class="font-semibold text-lg">₱${formatMoney(sale.subtotal)}</div>
                    </div>
                </div>
            `;
            mobileGrid.prepend(card);
        }
    });
}

document.addEventListener('DOMContentLoaded', loadOfflineSales);
document.addEventListener('offline-sync-completed', (e) => {
    if (e.detail && e.detail.remaining === 0) {
        window.location.reload();
        return;
    }
    loadOfflineSales();
});
