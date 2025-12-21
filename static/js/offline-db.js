let db;

// Open IndexedDB
const request = indexedDB.open("SmartDynamicRefillingDB", 1);

request.onupgradeneeded = function (event) {
  db = event.target.result;

  // Create an object store if it doesn't exist
  if (!db.objectStoreNames.contains("orders")) {
    db.createObjectStore("orders", { autoIncrement: true });
  }
};

request.onsuccess = function (event) {
  db = event.target.result;
};

request.onerror = function (event) {
  console.error("IndexedDB error:", event.target.errorCode);
};

// Save order locally when offline
function saveOrderOffline(order) {
  const tx = db.transaction(["orders"], "readwrite");
  const store = tx.objectStore("orders");
  store.add(order);
  console.log("Order saved offline:", order);
}

// Fetch unsynced orders
function getOfflineOrders() {
  return new Promise((resolve) => {
    const tx = db.transaction(["orders"], "readonly");
    const store = tx.objectStore("orders");
    const orders = [];
    store.openCursor().onsuccess = function (event) {
      const cursor = event.target.result;
      if (cursor) {
        orders.push({ id: cursor.key, ...cursor.value });
        cursor.continue();
      } else {
        resolve(orders);
      }
    };
  });
}

// Clear synced orders
function clearOrder(id) {
  const tx = db.transaction(["orders"], "readwrite");
  const store = tx.objectStore("orders");
  store.delete(id);
}
