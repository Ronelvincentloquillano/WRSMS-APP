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
    
    console.log("Add Sales Script Loaded. URLs:", {urlCustomer, urlOrdertype, urlProduct});

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

        // Logic Scope: Standard Refill (18-22L covers 5gal/20L variants)
        const size = parseFloat(productData.jug_size_in_liters);
        const pType = (productData.product_type || "").toUpperCase();
        const is20LRefill = (pType === 'REFILL' && size >= 18.0 && size <= 22.0); 
        
        console.log("Debug Recalc:", {
            product: productData.product_name,
            type: pType,
            size: size,
            is20LRefill: is20LRefill,
            orderType: orderTypeData.order_type,
            otPrice: orderTypeData.ot_unit_price,
            defStationPrice: orderTypeData.default_unit_price,
            hasCustomer: !!$customerSelect.val()
        });

        
        if (is20LRefill) {
            const orderTypeName = (orderTypeData.order_type || "").toLowerCase().trim();
            const hasCustomer = !!$customerSelect.val() || !!$("#customer").length; 
            const defaultDeliveryRate = parseFloat(orderTypeData.default_delivery_rate) || 0;
            const customerDiscount = parseFloat(customerData.discount_rate) || 0;

            if (orderTypeName.includes('delivery')) {
                if (hasCustomer) {
                    // Customer + Delivery
                    if (customerDiscount > 0) {
                        finalPrice = customerDiscount;
                    } else {
                        // Customer + Delivery + No Discount Code
                        finalPrice = defaultDeliveryRate;
                    }
                } else {
                    // No Customer + Delivery
                    finalPrice = defaultDeliveryRate;
                }
            }
            // For Pickup or any other non-delivery type, we don't override.
            // It will use finalPrice = productData.unit_price.
        }

        $unitPriceInput.val(finalPrice);
        
        // Recalc total
        let qty = parseFloat($qtyInput.val()) || 0;
        $totalInput.val((qty * finalPrice).toFixed(2));
        if (typeof updatePaymentDisplay === 'function') updatePaymentDisplay();
    }

    function recalculateAllRows() {
        let totalForms = parseInt($('#id_sales_items-TOTAL_FORMS').val());
        for (let i = 0; i < totalForms; i++) {
            recalculateRowPrice(i);
        }
        if (typeof updatePaymentDisplay === 'function') updatePaymentDisplay();
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
          })
          .fail(function(jqXHR, textStatus, errorThrown) {
              console.error("Customer Fetch Failed:", textStatus, errorThrown);
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
          })
          .fail(function(jqXHR, textStatus, errorThrown) {
              console.error("OrderType Fetch Failed:", textStatus, errorThrown);
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
        if (typeof updatePaymentDisplay === 'function') updatePaymentDisplay();
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
            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                console.error("Product Fetch Failed:", textStatus, errorThrown);
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
           if (typeof updatePaymentDisplay === 'function') updatePaymentDisplay();
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
      if (typeof updatePaymentDisplay === 'function') updatePaymentDisplay();
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
              })
              .fail(function(jqXHR, textStatus, errorThrown) {
                  console.error("Init Customer Fetch Failed:", textStatus, errorThrown, "URL:", urlCustomer);
              });
        }
    } else {
        // Standard Add Sales Mode
        if ($ordertypeSelect.val()) {
            $ordertypeSelect.trigger('change');
        }
    }

    // --- Payment: Cash / GCash (QR shows only after exact amount match) ---
    let gcashQrLastRenderedAmount = null;
    let gcashQrGenToken = 0;

    function clearGcashQrCanvas() {
        const canvas = document.getElementById('gcash-qr-canvas');
        if (canvas && canvas.getContext) {
            const ctx = canvas.getContext('2d');
            const w = canvas.width || 180;
            const h = canvas.height || 180;
            ctx.clearRect(0, 0, w, h);
        }
    }

    function getPaymentTypeText() {
        const $radio = $('input[name="payment_type"]:checked');
        if ($radio.length) return $radio.closest('label').text().trim();
        const $sel = $('select[name="payment_type"]');
        if ($sel.length) return $sel.find('option:selected').text();
        return '';
    }

    function paymentLabelIsGcash(label) {
        const compact = (label || '').toLowerCase().replace(/[\s_-]+/g, '');
        return compact.includes('gcash');
    }

    function paymentLabelIsCashOnly(label) {
        const compact = (label || '').toLowerCase().replace(/[\s_-]+/g, '');
        return compact.includes('cash') && !compact.includes('gcash');
    }

    function parseMoney(value) {
        if (value === null || value === undefined) return null;
        const normalized = String(value).replace(/,/g, '').trim();
        if (!normalized) return null;
        const n = parseFloat(normalized);
        return Number.isFinite(n) ? n : null;
    }

    function getPaymentTypeSelection() {
        const result = {
            value: null,
            label: '',
            isGcash: false,
            isCashOnly: false,
        };

        function classify(valueText, labelText) {
            const valueCompact = (valueText || '').toLowerCase().replace(/[\s_-]+/g, '');
            const labelCompact = (labelText || '').toLowerCase().replace(/[\s_-]+/g, '');
            const combined = valueCompact + ' ' + labelCompact;
            const isGcash = combined.includes('gcash');
            const isCashOnly = combined.includes('cash') && !combined.includes('gcash');
            return { isGcash: isGcash, isCashOnly: isCashOnly };
        }

        const $radios = $('input[name="payment_type"]');
        if ($radios.length) {
            const $checked = $radios.filter(':checked').first();
            if (!$checked.length) return result;

            result.value = $checked.val();
            const labelText = $checked.closest('label').text().trim();
            result.label = labelText;
            const radioClass = classify(result.value, labelText);
            result.isGcash = radioClass.isGcash;
            result.isCashOnly = radioClass.isCashOnly;
            return result;
        }

        const $sel = $('select[name="payment_type"]');
        if ($sel.length) {
            result.value = $sel.val();
            const labelText = $sel.find('option:selected').text();
            result.label = labelText;
            const selectClass = classify(result.value, labelText);
            result.isGcash = selectClass.isGcash;
            result.isCashOnly = selectClass.isCashOnly;
        }
        return result;
    }

    function gcashConfirmMatchesSale(grandTotal) {
        const entered = parseMoney($('#gcash-confirm-amount').val());
        if (entered === null || grandTotal <= 0) return false;
        return Math.round(entered * 100) === Math.round(grandTotal * 100);
    }

    function getGcashEntryState(grandTotal) {
        const entered = parseMoney($('#gcash-confirm-amount').val());
        if (entered === null || entered <= 0 || grandTotal <= 0) {
            return { ready: false, exact: false, entered: entered };
        }
        return {
            ready: true,
            exact: Math.round(entered * 100) === Math.round(grandTotal * 100),
            entered: entered,
        };
    }

    function getGrandTotal() {
        let total = 0;
        const $formset = $('#formset-container');
        // Use form field suffix matching instead of hardcoded IDs so this works
        // across add-sales variants and future formset prefix changes.
        const $totalInputs = $formset.find('input[name$="-total"], input[id$="-total"]');
        $totalInputs.each(function () {
            const val = parseMoney($(this).val());
            total += (val === null ? 0 : val);
        });
        if (total <= 0) {
            // Fallback: derive line totals from qty * unit_price when total fields
            // are not being auto-populated in some environments.
            const $rows = $formset.find('.form-row');
            $rows.each(function () {
                const qty = parseMoney($(this).find('input[name$="-quantity"], input[id$="-quantity"]').first().val());
                const unitPrice = parseMoney($(this).find('input[name$="-unit_price"], input[id$="-unit_price"]').first().val());
                if (qty !== null && unitPrice !== null) {
                    total += qty * unitPrice;
                }
            });
        }
        if (total <= 0) {
            const displayTotal = parseMoney($('#display-grand-total').text());
            if (displayTotal !== null) {
                total = displayTotal;
            }
        }
        return total;
    }

    function hasItemTypeSelected() {
        let hasSelectedProduct = false;
        $('#formset-container .form-row').each(function () {
            const $row = $(this);
            const isDeleted = $row.find('input[name$="-DELETE"]').is(':checked');
            if (isDeleted) return;
            const productValue = $row.find('select[name$="-product"], select[id$="-product"]').first().val();
            if (productValue) {
                hasSelectedProduct = true;
            }
        });
        return hasSelectedProduct;
    }

    function togglePaymentSections(selectedText) {
        const selection = getPaymentTypeSelection();
        const t = (selectedText || selection.label || '').toLowerCase().trim();
        const $cash = $('#payment-cash-section');
        const $gcash = $('#payment-gcash-section');
        const isPaid = $('#is_paid').is(':checked');
        $cash.addClass('hidden');
        // Keep GCash section visible by default; only gate cash-specific block.
        $gcash.removeClass('hidden');
        if (!isPaid) return;
        if (selection.isCashOnly || t.includes('cash')) {
            $cash.removeClass('hidden');
        }
    }

    function syncGcashQr(grandTotal, selectedText) {
        const selection = getPaymentTypeSelection();
        const isPaid = $('#is_paid').is(':checked');
        const $reveal = $('#gcash-qr-reveal');
        const $wrapper = $('#gcash-qr-wrapper');
        const $stationImg = $('#gcash-station-qr-img');
        const $fallback = $('#gcash-qr-fallback');
        const $hint = $('#gcash-confirm-hint');
        const canvas = document.getElementById('gcash-qr-canvas');
        const hasStationImg = $stationImg.length > 0;

        function hideQr() {
            gcashQrLastRenderedAmount = null;
            if ($reveal.length) $reveal.addClass('hidden');
            if ($wrapper.length) $wrapper.addClass('hidden');
            clearGcashQrCanvas();
        }

        // Requested flow:
        // show QR as soon as staff selects GCash and confirms customer is paid.
        const shouldShowQr = isPaid && selection.isGcash;

        if (!shouldShowQr) {
            hideQr();
            if ($hint.length) {
                let hintText = 'Select GCash and mark customer as paid to show QR.';
                if (!isPaid) {
                    hintText = 'Mark "Customer paid now" first to enable GCash QR.';
                } else if (!selection.isGcash) {
                    hintText = 'Select GCash as payment method to show QR.';
                }
                $hint
                    .removeClass('text-emerald-600')
                    .addClass('text-slate-500')
                    .text(hintText);
            }
            return;
        }

        if ($reveal.length) $reveal.removeClass('hidden');
        if ($hint.length) {
            $hint
                .removeClass('text-slate-500')
                .addClass('text-emerald-600')
                .text('GCash selected. QR ready to scan.');
        }

        if (hasStationImg) {
            if ($wrapper.length) $wrapper.addClass('hidden');
            return;
        }

        if (!$wrapper.length || !canvas) return;
        if (typeof QRCode === 'undefined') {
            console.warn('GCash QR: QRCode library not loaded.');
            return;
        }

        if ($fallback.length) $fallback.removeClass('hidden');

        const amountBase = grandTotal > 0 ? grandTotal : 0;
        const amountKey = Math.round(amountBase * 100) / 100;
        if (gcashQrLastRenderedAmount !== null && Math.abs(gcashQrLastRenderedAmount - amountKey) < 0.0001 && !$wrapper.hasClass('hidden')) {
            $wrapper.removeClass('hidden');
            return;
        }

        const myToken = ++gcashQrGenToken;
        const payload = 'GCASH|Amount: PHP ' + amountKey.toFixed(2) + '|Scan to pay';
        QRCode.toCanvas(canvas, payload, { width: 180, margin: 1 }, function (err) {
            if (myToken !== gcashQrGenToken) return;
            if (err) {
                console.warn('QR generate error', err);
                return;
            }
            gcashQrLastRenderedAmount = amountKey;
            $wrapper.removeClass('hidden');
        });
    }

    function updateAmountGivenRequired() {
        const paid = $('#is_paid').is(':checked');
        const selection = getPaymentTypeSelection();
        const selectedText = selection.label || getPaymentTypeText();
        const t = selectedText.toLowerCase();
        const cashOnly = selection.isCashOnly || (t.includes('cash') && !paymentLabelIsGcash(selectedText));
        $('#id_amount_given').prop('required', !!(paid && cashOnly));
    }

    function syncPaidPanelVisibility() {
        const $wrap = $('#payment_details_wrap');
        const $isPaid = $('#is_paid');
        if (!$wrap.length || !$isPaid.length) return;
        const isPaid = $isPaid.is(':checked');
        if (isPaid) $wrap.removeClass('hidden');
        else $wrap.addClass('hidden');
        $('input[name="payment_type"], select[name="payment_type"], #id_amount_given').prop('disabled', false);
        if (!isPaid) {
            $('#payment-cash-section, #payment-gcash-section, #gcash-qr-reveal, #gcash-qr-wrapper').addClass('hidden');
        }
        updateAmountGivenRequired();
    }

    function updatePaymentDisplay() {
        const grandTotal = getGrandTotal();
        const selection = getPaymentTypeSelection();
        const selectedText = selection.label || getPaymentTypeText();
        const t = (selectedText || '').toLowerCase().trim();

        $('#display-grand-total').text(grandTotal.toFixed(2));
        $('#display-gcash-amount').text(grandTotal.toFixed(2));

        if (selection.isCashOnly || (t.includes('cash') && !paymentLabelIsGcash(selectedText))) {
            const amountGiven = parseFloat($('#id_amount_given').val()) || 0;
            const change = amountGiven - grandTotal;
            const $changeWrap = $('#display-change-wrap');
            const $changeVal = $('#display-change');
            if (amountGiven > 0) {
                $changeVal.text(change.toFixed(2));
                $changeWrap.removeClass('hidden');
                if (change < 0) $changeVal.removeClass('text-green-700').addClass('text-red-600');
                else $changeVal.removeClass('text-red-600').addClass('text-green-700');
            } else {
                $changeWrap.addClass('hidden');
            }
        } else {
            $('#display-change-wrap').addClass('hidden');
        }

        syncGcashQr(grandTotal, selectedText);
    }

    $(document).on('input change click', 'input[name="payment_type"], select[name="payment_type"]', function () {
        gcashQrLastRenderedAmount = null;
        togglePaymentSections(getPaymentTypeText());
        updateAmountGivenRequired();
        updatePaymentDisplay();
    });

    $(document).on('input', '#id_amount_given', updatePaymentDisplay);
    $(document).on('input change', '#formset-container input[name$="-total"], #formset-container input[id$="-total"]', function () {
        gcashQrLastRenderedAmount = null;
        updatePaymentDisplay();
    });
    $(document).on('input change', '#formset-container input[name$="-quantity"], #formset-container input[id$="-quantity"], #formset-container input[name$="-unit_price"], #formset-container input[id$="-unit_price"]', function () {
        gcashQrLastRenderedAmount = null;
        updatePaymentDisplay();
    });
    $('#is_paid').on('change', function () {
        syncPaidPanelVisibility();
        togglePaymentSections(getPaymentTypeText());
        updatePaymentDisplay();
    });

    syncPaidPanelVisibility();
    togglePaymentSections(getPaymentTypeText());
    updatePaymentDisplay();
});
