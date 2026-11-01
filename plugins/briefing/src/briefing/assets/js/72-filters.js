  /* ---------------------------------------------------------------- filters */
  /* A filter shows the precomputed copy of each sliced block that matches its option.
     Charts in a copy that was hidden redraw at their new width as they appear. */
  INIT.filters = function (node) {
    node.querySelectorAll("select[data-filter]").forEach(function (select) {
      var key = select.getAttribute("data-filter");
      function apply() {
        doc.querySelectorAll('.slice[data-slice="' + key + '"]').forEach(function (el) {
          el.hidden = el.getAttribute("data-option") !== select.value;
        });
      }
      select.addEventListener("change", apply);
      apply();
    });
  };
