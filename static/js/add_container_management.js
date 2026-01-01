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
});