$(document).ready(function () {
  const $bflv = $("#id_balance_from_last_visit");
  const $dc = $("#id_delivered_container");
  const $rec = $("#id_returned_empty_container");
  const $nb = $("#id_new_balance");

  $dc.on("click", function () {
    if ($(this).val() == 0) {
      $(this).val('');
    }
  });
  $rec.on("click", function () {
    if ($(this).val() == 0) {
      $(this).val('');
    }
  });

  // Calculate total amount
  $(
    "#id_balance_from_last_visit, \
      #id_delivered_container, #id_returned_empty_container, \
      #id_new_balance"
  ).on("keyup", function () {
    // Convert values to numbers
    var bflv = parseFloat($("#id_balance_from_last_visit").val()) || 0;
    var dc = parseFloat($("#id_delivered_container").val()) || 0;
    var rec = parseFloat($("#id_returned_empty_container").val()) || 0;
    var new_balance = bflv + dc - rec;

    $("#id_new_balance").val(new_balance);
  });

  $($rec).on("input", function () {
    var bflv = parseFloat($("#id_balance_from_last_visit").val()) || 0;
    var dc = parseFloat($("#id_delivered_container").val()) || 0;
    var bflv_rec = bflv + dc;
    console.log("combined balance: ",bflv_rec);
    if (bflv_rec < parseFloat($(this).val())) {
      alert(
        "Returned Empty Container cannot be greater than the sum of Balance from Last Visit and Delivered Container!"
      );
      $rec.val("");
    }
  });

  const $customerSelect = $("#id_customer");

  $customerSelect.on("change", function () {
    const customerId = $(this).val();

    if (customerId) {
      $.getJSON(`/ajax/get-container-balance/?id_customer=${customerId}`)
        .done(function (data) {
          if (data.error) {
            alert("Error. Customer ID not found!");
          } else {
            if (data.bflv === null || data.bflv === undefined) {
              $bflv.val("");
              $bflv.prop("readonly", false);
            } else {
              $bflv.val(data.bflv);
              $bflv.prop("readonly", true);
            }
          }
        })
        .fail(function (jqXHR, textStatus, errorThrown) {
          console.error("Error fetching customer data:", errorThrown);
        });
    } else {
      $bflv.val("");
      $bflv.prop("readonly", false);
    }
  });

  // --- Offline Update Support ---
  if (window.location.pathname.includes('/update-container-record/')) {
       // Extract PK
       const parts = window.location.pathname.split('/').filter(p => p);
       const pk = parts[parts.length - 1]; // Last non-empty segment
       
       // If offline (or if the page content seems empty/generic), try to populate
       // We can check if fields are empty to decide, or just always try if offline
       if (!navigator.onLine) {
           populateFormOffline(pk);
       }
  }

  async function populateFormOffline(pk) {
      try {
           const response = await fetch('/api/offline-master-data/');
           if (!response.ok) return;
           const data = await response.json();
           
           let record = null;
           let customerId = null;
           
           // Search all customer histories
           for (const cid in data.container_history) {
               const history = data.container_history[cid];
               const found = history.find(item => String(item.pk) === String(pk));
               if (found) {
                   record = found;
                   customerId = cid;
                   break;
               }
           }
           
           if (record) {
               if (record.timestamp) {
                   const dateObj = new Date(record.timestamp);
                   const offsetMs = dateObj.getTimezoneOffset() * 60 * 1000;
                   const localIso = new Date(dateObj.getTime() - offsetMs).toISOString().slice(0, 16);
                   $('#id_created_date').val(localIso);
               }
               
               $('#id_customer').val(customerId);
               $('#id_balance_from_last_visit').val(record.balance_from_last_visit);
               $('#id_delivered_container').val(record.delivered_container);
               $('#id_returned_empty_container').val(record.returned_empty_container);
               $('#id_new_balance').val(record.new_balance);
               $('#id_note').val(record.note);
               
               $('h2').text('Update Container Management');
               document.title = 'Update Container Management';
               $('form').attr('id', 'update_container_management_form');
           }
      } catch (e) {
          console.error('Error populating offline form', e);
      }
  }
});