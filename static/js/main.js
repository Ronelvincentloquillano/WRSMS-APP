if ("serviceWorker" in navigator && "SyncManager" in window) {
  navigator.serviceWorker.ready.then(reg => {
    reg.sync.register("sync-writes");
  });
}

fetch("/api/containerinventory/")
  .then(res => res.json())
  .then(data => {
    saveInventory(data);
    renderInventory(data);
  })
  .catch(async () => {
    const offlineData = await getInventory();
    renderInventory(offlineData);
  });

if (!navigator.onLine) {
  await queueAction({
    type: "UPDATE",
    endpoint: "/api/containerinventory/",
    payload: formData
  });

  alert("Saved offline. Will sync when online.");
} else {
  // normal API POST / PUT
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    showUpdateToast();
  });
}

function showUpdateToast() {
  if (document.getElementById("sw-update-toast")) return;

  const toast = document.createElement("div");
  toast.id = "sw-update-toast";
  toast.className =
    "fixed bottom-4 left-1/2 -translate-x-1/2 bg-slate-900 text-white px-4 py-3 rounded shadow-lg z-[10002] flex items-center gap-3";

  toast.innerHTML = `
    <span>New version available</span>
    <button
      id="reload-app"
      class="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm"
    >
      Reload
    </button>
  `;

  document.body.appendChild(toast);

  document.getElementById("reload-app").onclick = () => {
    window.location.reload();
  };
}


console.log("Main JS loaded");

