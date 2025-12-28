$(document).ready(function () {
    // Customer selection
    const $customerSelect = $("#id_customer");
    const $promo_code = $("#id_promo_code");
    const $promo_description = $("#id_promo_description");
    const $discount_code = $("#id_discount_code");
    const $discount_description = $("#id_discount_description");
    const $discount_rate = $("#id_discount_rate");
    const $customer_info = $("#customer-info");
    const $unit_price = $("#id_unit_price");
    const $id_order_type = $("#id_order_type");
    const $default_order_type = $("#id_default_order_type");
    const $station_default_order_type = $("#id_station_default_order_type");

    function clearCustomerInfo() {
      $promo_code.text('');
      $promo_description.text('');
      $discount_code.text('');
      $discount_description.text('');
      $discount_rate.text('');
      $unit_price.text('');
    }

    $customerSelect.on("change", function () {
      const customerId = $(this).val();

      clearCustomerInfo();

      if (customerId) {
        $.getJSON(`/ajax/get-customer-data/?id_customer=${customerId}`)
          .done(function (data) {
            $("#order_type").text(data.default_ot || '');
            if (data.error) {
              clearCustomerInfo();
              $customer_info.hide();
            } else if (data.discount_rate != null) {
              $customer_info.show();
              $promo_code.text(data.promo_code || '');
              $promo_description.text(data.promo_description || '');
              $discount_code.text(data.discount_code || '');
              $discount_description.text(data.discount_description || '');
              $discount_rate.text(data.discount_rate || '');
              $id_order_type.val(data.default_order_type);
            } else {
              clearCustomerInfo();
              $customer_info.hide();
              console.log(data.promo_code);
            }
          })
          .fail(function (jqXHR, textStatus, errorThrown) {
            console.error("Error fetching customer data:", errorThrown);
            clearCustomerInfo();
            $customer_info.hide();
          });
      } else {
        clearCustomerInfo();
        $customer_info.hide();
        $id_order_type.val(data.station_default_order_type);
      }
    });

    // Order type selection
    const $ordertypeSelect = $("#id_order_type");
    const $ot_unit_price = $("#ot_unit_price");
    const $sys_default_ot = $("#sys_default_ot");
    const $orderType = $("#order_type");

    $ordertypeSelect.on("change", function () {
      const ordertypeID = $(this).val();

      if (ordertypeID) {
        $.getJSON(`/ajax/get-ordertype-data/?id_order_type=${ordertypeID}`)
          .done(function (data) {
            $ot_unit_price.text(data.ot_unit_price || '');
            $unit_price.val(data.ot_unit_price || '');
            $sys_default_ot.text(data.sys_default_ot || '');
            $orderType.text(data.order_type || '');
          })
          .fail(function (jqXHR, textStatus, errorThrown) {
            console.error("Error fetching ordertype data:", errorThrown);
          });
      } else {
        $ot_unit_price.text('');
        $sys_default_ot.text('');
        console.log("else");
      }
    });
  });

  $(document).ready(function () {
    function bindEventsToForm(i) {
      let $qty = $(`#id_sales_items-${i}-quantity`);
      let $unit_price = $(`#id_sales_items-${i}-unit_price`);
      let $total = $(`#id_sales_items-${i}-total`);

      function calculateTotal() {
        var qty = parseFloat($qty.val()) || 0;
        var unit_price = parseFloat($unit_price.val()) || 0;
        $total.val((qty * unit_price).toFixed(2));
      }

      $qty.on('input', calculateTotal);
      $unit_price.on('input', calculateTotal);

      // Product selection
      const $product = $(`#id_sales_items-${i}-product`);
      $product.on("change", function () {
        const productID = $(this).val();
        const discountRate = $('#id_discount_rate');
        const otUnitPrice = $("#ot_unit_price").text();
        const orderType = $("#order_type").text();
        const sysOrderType = $("#sys_default_ot").text();

        // Clear quantity whenever product changes
        $qty.val('');
        calculateTotal();

        if (productID) {
          $.getJSON(`/ajax/get-product-data/?id_product=${productID}`)
            .done(function (data) {
              // Apply discount logic for 20 liters REFILL products
              if (discountRate.text() !== '' && orderType !== sysOrderType && data.jug_size_in_liters === 20 && data.product_type === 'REFILL') {
                $unit_price.val(discountRate.text());
              } else {
                $unit_price.val(data.unit_price || '');
              }
            })
            .fail(function (jqXHR, textStatus, errorThrown) {
              console.error("Error fetching product data:", errorThrown);
            });
        } else {
          $unit_price.val('');
        }
      });

      let $freeButton = $(`.free-button[data-id="free${i}"]`);
      $freeButton.on('click', function () {
        $(this).toggleClass('bg-yellow-200');
        if (!$(this).hasClass('bg-yellow-200')) {
          $(`#id_sales_items-${i}-product`).trigger('change');
        } else {
          $qty.val(1);
        }
        $unit_price.val(0);
        calculateTotal();
        if (!$(this).hasClass('bg-yellow-200')) {
          $(`#id_sales_items-${i}-unit_price`).attr("readonly",false);
          $(`#id_sales_items-${i}-total`).attr("readonly",false);
        } else {
          $(`#id_sales_items-${i}-unit_price`).attr("readonly",true);
          $(`#id_sales_items-${i}-total`).attr("readonly",true);
        }
      });

      // Remove button handler
      let $row = $(`#id_sales_items-${i}-product`).closest('.form-row');
      let $deleteBtn = $row.find('.remove-form');
      $deleteBtn.off('click').on('click', function() {
           let $deleteInput = $row.find('input[name$="-DELETE"]');
           if ($deleteInput.length) {
               $deleteInput.prop('checked', true);
           }
           $row.hide();
      });

    }

    // Initial bind
    let totalFormsInput = $('#id_sales_items-TOTAL_FORMS');
    let initialForms = parseInt(totalFormsInput.val());
    for (let i = 0; i < initialForms; i++) {
      bindEventsToForm(i);
    }

    // Add new form on button click
    $('#add-form').click(function () {
      let formCount = parseInt(totalFormsInput.val());
      let $lastForm = $('#formset-container .form-row:last');
      let $newForm = $lastForm.clone(false); // clone without events
      
      $newForm.show(); // Ensure visibility if last form was hidden

      // Update all input fields
      $newForm.find(':input').each(function () {
        let name = $(this).attr('name');
        if (name) {
          let newName = name.replace(/-\d+-/, `-${formCount}-`);
          let newId = 'id_' + newName;
          $(this).attr({ 'name': newName, 'id': newId }).val('');
          if ($(this).attr('type') === 'checkbox') {
             $(this).prop('checked', false);
          }
        }
      });

      // Update any labels (important for accessibility)
      $newForm.find('label').each(function () {
        let newFor = $(this).attr('for')?.replace(/-\d+-/, `-${formCount}-`);
        if (newFor) $(this).attr('for', newFor);
      });

      // Update Free button data-id
      $newForm.find('.free-button').each(function () {
        $(this).attr('data-id', `free${formCount}`);
      });

      $('#formset-container').append($newForm);
      totalFormsInput.val(formCount + 1);

      bindEventsToForm(formCount); // rebind calc for new form
    });

  });