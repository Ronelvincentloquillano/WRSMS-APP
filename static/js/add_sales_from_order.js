$(document).ready(function () {
  const customer_id = $("#customer").data("customer-id");
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

  console.log("customer id:", customer_id);

  $.getJSON(`/wrsm/ajax/get-customer-data/?id_customer=${customer_id}`)
    .done(function (data) {
      $("#order_type").text(data.default_ot || "");
      if (data.error) {
        clearCustomerInfo();
        $customer_info.hide();
      } else if (data.discount_rate != null) {
        $promo_code.text(data.promo_code || "");
        $promo_description.text(data.promo_description || "");
        $discount_code.text(data.discount_code || "");
        $discount_description.text(data.discount_description || "");
        $discount_rate.text(data.discount_rate || "");
        $id_order_type.val(data.default_order_type);
      } else {
        clearCustomerInfo();
        console.log(data.promo_code);
      }
    })
    .fail(function (jqXHR, textStatus, errorThrown) {
      console.error("Error fetching customer data:", errorThrown);
      clearCustomerInfo();
    });
});
