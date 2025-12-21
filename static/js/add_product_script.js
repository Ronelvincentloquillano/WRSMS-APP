$(document).ready(function () {
  const $productType = $('#id_product_type');
  const $quantity = $('#id_quantity');
  const $productName = $('#id_product_name');
  const $jugSize = $('#id_jug_size');
  const $jugType = $('#id_jug_type');

  function toggleFields() {
    const type = $productType.val();

    const isRefill = type === "REFILL";
    const isSeal = type === "SEAL";
    const isDelivery = type === "DELIVERY CHARGE";
    const isSpare = type === "SPARE PART";

    $quantity.prop('disabled', isRefill || isDelivery);
    $jugSize.prop('disabled', isSeal || isDelivery || isSpare);
    $jugType.prop('disabled', isDelivery || isSpare);
  }

  function updateProductName() {
    if ($productType.val() !== "REFILL") {
      $productName.val('');
      return;
    }

    const size = $jugSize.val();
    const type = $jugType.val();

    if (size && type) {
      const product = [
        $("#id_product_type option:selected").text(),
        $("#id_jug_size option:selected").text(),
        $("#id_jug_type option:selected").text()
      ].join(" - ");

      $productName.val(product);
    } else {
      $productName.val('');
    }
  }

  // Bind events
  $productType.on('change', toggleFields);
  $jugSize.on('change', updateProductName);
  $jugType.on('change', updateProductName);
});
