  /* ---------------------------------------------------------------- notes */
  // Pen notes write themselves 1.5 s after their plate develops, which the plate marks by
  // adding "go" to its stage as the painting scrolls into view.
  function initNotes(node) {
    var stage = node.closest(".stage");
    if (!stage) return;
    if (reduceMotion) { stage.classList.add("noted"); return; }
    var armed = false;
    tickers.push(function () {
      if (armed || !stage.classList.contains("go")) return;
      armed = true;
      setTimeout(function () { stage.classList.add("noted"); }, 1500);
    });
  }
  INIT.notes = initNotes;
