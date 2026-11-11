  /* -------------------------------------------------------------- animation */
  /* In a deck the deck steps the animation; elsewhere it loops with a pause button,
     since moving content longer than five seconds needs one (WCAG 2.2.2). */
  INIT.animation = function (node) {
    var svg = node.querySelector(".anim-svg svg");
    if (!svg || !svg.getAnimations || node.closest(".deck")) return;
    var btn = html("button", "anim-pause", word("pause", "Pause"), node);
    btn.type = "button";
    btn.setAttribute("aria-pressed", "false");
    btn.addEventListener("click", function () {
      var paused = btn.getAttribute("aria-pressed") === "true";
      svg.getAnimations({ subtree: true }).forEach(function (a) { if (paused) a.play(); else a.pause(); });
      btn.setAttribute("aria-pressed", paused ? "false" : "true");
      btn.textContent = paused ? word("pause", "Pause") : word("play", "Play");
    });
  };
