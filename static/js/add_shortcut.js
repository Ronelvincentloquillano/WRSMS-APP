$(document).ready(function () {
  const $note = $("#id_note");
  const $quantity = $("#id_quantity");
  const $promptNote = $("#id_prompt_note");
  const $promptQuantity = $("#id_prompt_quantity");
  $promptNote.on("change", function () {
    if ($(this).is(":checked")) {
      // If the checkbox is checked, disable it
      $note.attr("disabled", true);
    } else {
      // If the checkbox is unchecked, enable it
      $note.attr("disabled", false);
    }
  });
  $promptQuantity.on("change", function () {
    if ($(this).is(":checked")) {
      // If the checkbox is checked, disable it
      $quantity.attr("readonly", true);
    } else {
      // If the checkbox is unchecked, enable it
      $quantity.attr("readonly", false);
    }
  });
});
