$(document).ready(function () {
    // Global State
    let customerData = {};
    let orderTypeData = {};

    // Selectors
    const $form = $("#add_sales_form");
    const $customerSelect = $("#id_customer");
    const $ordertypeSelect = $("#id_order_type");
    
    // AJAX URLs
    const urlCustomer = $form.data("url-customer");
    const urlOrdertype = $form.data("url-ordertype");
    const urlProduct = $form.data("url-product");
    
    // Customer Info UI
    const $promo_code = $("#id_promo_code");
    const $promo_description = $("#id_promo_description");
    const $discount_code = $("#id_discount_code");
    const $discount_description = $("#id_discount_description");
    const $discount_rate = $("#id_discount_rate");
    const $customer_info = $("#customer-info");
    const $orderTypeDisplay = $("#order_type");
    const $otUnitPriceDisplay = $("#ot_unit_price");
    const $sysDefaultOtDisplay = $("#sys_default_ot");

    function clearCustomerInfo() {
      $promo_code.text('');
      $promo_description.text('');
      $discount_code.text('');
      $discount_description.text('');
      $discount_rate.text('');
      customerData = {};
    }

    function recalculateRowPrice(i) {
        const $productSelect = $(`#id_sales_items-${i}-product`);
        const $unitPriceInput = $(`#id_sales_items-${i}-unit_price`);
        const $qtyInput = $(`#id_sales_items-${i}-quantity`);
        const $totalInput = $(`#id_sales_items-${i}-total`);
        const $freeButton = $(`.free-button[data-id="free${i}"]`);

        // Check if free
        if ($freeButton.hasClass('bg-yellow-200')) {
            $unitPriceInput.val(0);
            let qty = parseFloat($qtyInput.val()) || 0;
            $totalInput.val(0);
            return;
        }

        const productData = $productSelect.data('product-info'); 
        if (!productData) return;

        let finalPrice = parseFloat(productData.unit_price) || 0;

        // Logic Scope: 20L Jug
        const is20LRefill = (parseFloat(productData.jug_size_in_liters) === 20.0 && productData.product_type === 'REFILL');
        
        if (is20LRefill) {
            const orderTypeName = (orderTypeData.order_type || "").toLowerCase().trim();
            const hasCustomer = !!$customerSelect.val() || !!$("#customer").length; // Check both select and fixed div
            const defaultDeliveryRate = parseFloat(orderTypeData.default_delivery_rate) || 0;
            const otUnitPrice = parseFloat(orderTypeData.ot_unit_price) || 0;
            const customerDiscount = parseFloat(customerData.discount_rate) || 0;

            if (orderTypeName === 'delivery') {
                if (hasCustomer) {
                    // If customer selected + delivery
                    if (customerDiscount > 0) {
                        finalPrice = customerDiscount;
                    } else {
                        // Empty discount code -> Station Default Delivery Rate
                        finalPrice = defaultDeliveryRate;
                    }
                } else {
                    // No customer + delivery -> Station Default Delivery Rate
                    finalPrice = defaultDeliveryRate;
                }
            } else if (orderTypeName === 'pickup') {
                if (!hasCustomer) {
                    // No customer + pickup -> Station Default Pickup Rate (Assuming OT Unit Price)
                    finalPrice = otUnitPrice;
                }
                // If customer selected + pickup, fallback to default product price or specific logic?
                // Prompt didn't specify. Defaulting to product base price (initial finalPrice).
            }
        }

        $unitPriceInput.val(finalPrice);
        
        // Recalc total
        let qty = parseFloat($qtyInput.val()) || 0;
        $totalInput.val((qty * finalPrice).toFixed(2));
    }

    function recalculateAllRows() {
        let totalForms = parseInt($('#id_sales_items-TOTAL_FORMS').val());
        for (let i = 0; i < totalForms; i++) {
            recalculateRowPrice(i);
        }
    }

    // Customer Change Handler
    $customerSelect.on("change", function () {
      const customerId = $(this).val();
      clearCustomerInfo();

      if (customerId) {
        $.getJSON(`${urlCustomer}?id_customer=${customerId}`)
          .done(function (data) {
            $orderTypeDisplay.text(data.default_ot || '');
            
            // Store Data
            customerData = data;

            if (data.discount_rate != null) {
              $customer_info.show();
              $promo_code.text(data.promo_code || '');
              $promo_description.text(data.promo_description || '');
              $discount_code.text(data.discount_code || '');
              $discount_description.text(data.discount_description || '');
              $discount_rate.text(data.discount_rate || '');
              
              // Update Order Type dropdown if customer has default
              if (data.default_order_type) {
                  $ordertypeSelect.val(data.default_order_type).trigger('change');
              }
            } else {
              $customer_info.hide();
            }
            recalculateAllRows();
          });
      } else {
        $customer_info.hide();
        // Reset order type to station default if available in previous data? 
        // Or just let it be.
        recalculateAllRows();
      }
    });

    // Order Type Change Handler
    $ordertypeSelect.on("change", function () {
      const ordertypeID = $(this).val();

      if (ordertypeID) {
        $.getJSON(`${urlOrdertype}?id_order_type=${ordertypeID}`)
          .done(function (data) {
            orderTypeData = data;
            $otUnitPriceDisplay.text(data.ot_unit_price || '');
            $sysDefaultOtDisplay.text(data.sys_default_ot || '');
            $orderTypeDisplay.text(data.order_type || '');
            
            recalculateAllRows();
          });
      } else {
        orderTypeData = {};
        $otUnitPriceDisplay.text('');
        $sysDefaultOtDisplay.text('');
        recalculateAllRows();
      }
    });

    // Formset Handling
    function bindEventsToForm(i) {
      let $qty = $(`#id_sales_items-${i}-quantity`);
      let $unit_price = $(`#id_sales_items-${i}-unit_price`);
      let $total = $(`#id_sales_items-${i}-total`);
      let $product = $(`#id_sales_items-${i}-product`);

      function calculateTotal() {
        var qty = parseFloat($qty.val()) || 0;
        var unit_price = parseFloat($unit_price.val()) || 0;
        $total.val((qty * unit_price).toFixed(2));
      }

      $qty.on('input', calculateTotal);
      $unit_price.on('input', calculateTotal);

      $product.on("change", function () {
        const productID = $(this).val();
        $qty.val(''); // Clear quantity
        
        if (productID) {
          $.getJSON(`${urlProduct}?id_product=${productID}`)
            .done(function (data) {
              // Attach data to element for global access
              $product.data('product-info', data);
              recalculateRowPrice(i);
            });
        } else {
          $product.removeData('product-info');
          $unit_price.val('');
          calculateTotal();
        }
      });

      let $freeButton = $(`.free-button[data-id="free${i}"]`);
      $freeButton.off('click').on('click', function () {
        $(this).toggleClass('bg-yellow-200');
        const isFree = $(this).hasClass('bg-yellow-200');
        
        if (isFree) {
            $qty.val(1);
            $unit_price.val(0);
            $unit_price.attr("readonly", true);
            $total.attr("readonly", true);
        } else {
            $unit_price.attr("readonly", false);
            $total.attr("readonly", false);
            recalculateRowPrice(i); // Revert to logic price
        }
        calculateTotal();
      });

      // Remove button handler
      let $row = $product.closest('.form-row');
      let $deleteBtn = $row.find('.remove-form');
      $deleteBtn.off('click').on('click', function() {
           let $deleteInput = $row.find('input[name$="-DELETE"]');
           if ($deleteInput.length) {
               $deleteInput.prop('checked', true);
           }
           $row.hide();
      });
    }

    // Initial Bind
    let totalFormsInput = $('#id_sales_items-TOTAL_FORMS');
    let initialForms = parseInt(totalFormsInput.val());
    for (let i = 0; i < initialForms; i++) {
      bindEventsToForm(i);
    }

    // Add Form
    $('#add-form').click(function () {
      let formCount = parseInt(totalFormsInput.val());
      let $lastForm = $('#formset-container .form-row:last');
      let $newForm = $lastForm.clone(false);
      
      $newForm.show();

      $newForm.find(':input').each(function () {
        let name = $(this).attr('name');
        if (name) {
          let newName = name.replace(/-\d+-/, `-${formCount}-`);
          let newId = 'id_' + newName;
          $(this).attr({ 'name': newName, 'id': newId }).val('');
          if ($(this).attr('type') === 'checkbox') $(this).prop('checked', false);
        }
      });

      $newForm.find('label').each(function () {
        let newFor = $(this).attr('for')?.replace(/-\d+-/, `-${formCount}-`);
        if (newFor) $(this).attr('for', newFor);
      });

      $newForm.find('.free-button').each(function () {
        $(this).attr('data-id', `free${formCount}`).removeClass('bg-yellow-200');
      });
      
      $newForm.find('[readonly]').attr('readonly', false); // Reset readonly

      $('#formset-container').append($newForm);
      totalFormsInput.val(formCount + 1);

      bindEventsToForm(formCount);
    });

    // Initialization
    const fixedCustomerDiv = $("#customer");
    if (fixedCustomerDiv.length) {
        // Add Sales From Order Mode
        const customerId = fixedCustomerDiv.data("customer-id");
        
        if (customerId) {
            $.getJSON(`${urlCustomer}?id_customer=${customerId}`)
              .done(function (data) {
                $orderTypeDisplay.text(data.default_ot || '');
                customerData = data;

                if (data.discount_rate != null) {
                  $customer_info.show();
                  $promo_code.text(data.promo_code || '');
                  $promo_description.text(data.promo_description || '');
                  $discount_code.text(data.discount_code || '');
                  $discount_description.text(data.discount_description || '');
                  $discount_rate.text(data.discount_rate || '');
                } else {
                  $customer_info.hide();
                }
                
                // Trigger Order Type init
                const currentOtVal = $ordertypeSelect.val();
                if (currentOtVal) {
                    $ordertypeSelect.trigger('change');
                }
              });
        }
    } else {
        // Standard Add Sales Mode
        if ($ordertypeSelect.val()) {
            $ordertypeSelect.trigger('change');
        }
    }
});
