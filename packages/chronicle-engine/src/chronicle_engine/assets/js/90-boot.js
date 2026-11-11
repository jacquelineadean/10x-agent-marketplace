  /* ----------------------------------------------------------------- theme */
  (function theme() {
    var btn = doc.querySelector(".theme-btn");
    if (!btn) return;
    try { var saved = localStorage.getItem("chronicle-theme"); if (saved) root.setAttribute("data-theme", saved); } catch (e) { /* storage blocked: keep the viewer's theme */ }
    btn.addEventListener("click", function () {
      var explicit = root.getAttribute("data-theme");
      var dark = explicit ? explicit === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
      var next = dark ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("chronicle-theme", next); } catch (e) { /* storage blocked: the choice lasts this visit */ }
    });
  })();

  /* ------------------------------------------------------------------ boot */
  doc.querySelectorAll("[data-fig]").forEach(function (node) {
    var spec = FIGS[node.getAttribute("data-fig")];
    if (!spec) return;
    var start = INIT[spec.type];
    try {
      if (start) start(node, spec);
    } catch (err) {
      var note = html("p", "fig-note", "This figure could not start: " + err.message, null);
      node.appendChild(note);
    }
  });
  var spanUpdate = initProgress();
  var ticking = false;
  function frameLoop(now) {
    ticking = false;
    var vh = window.innerHeight || 800;
    spanUpdate(vh);
    scrollers.forEach(function (f) { f(vh); });
    tickers.forEach(function (f) { f(vh, now || performance.now()); });
  }
  function request() { if (!ticking) { ticking = true; requestAnimationFrame(frameLoop); } }
  window.addEventListener("scroll", request, { passive: true });
  window.addEventListener("resize", request);
  frameLoop(performance.now());
  if (!reduceMotion) {
    (function loop(t) { tickers.forEach(function (f) { f(window.innerHeight || 800, t); }); requestAnimationFrame(loop); })(performance.now());
  }
