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
    var type = spec.type;
    try {
      if (type === "chart") mountChart(node, spec, node.querySelector(".mount"), {});
      else if (type === "stats") initStats(node, spec);
      else if (type === "scrolly") initScrolly(node, spec);
      else if (type === "timeline") initTimeline(node, spec);
      else if (type === "stepper") initStepper(node, spec);
      else if (type === "compare") initCompare(node, spec);
      else if (type === "matrix") initMatrix(node, spec);
      else if (type === "roadmap") initRoadmap(node, spec);
      else if (type === "team") initTeam(node, spec);
      else if (type === "model") initModel(node, spec);
      else if (type === "plate") initPlate(node, spec);
      else if (type === "tilemap") initTilemap(node, spec);
      else if (type === "flow") initFlow(node, spec);
      else if (type === "diagram") initDiagram(node, spec);
      else if (type === "quiz") initQuiz(node, spec);
      else if (type === "checklist") initChecklist(node, spec);
      else if (type === "widget") initWidget(node, spec);
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
    plates.forEach(function (f) { f(vh, now || performance.now()); });
  }
  function request() { if (!ticking) { ticking = true; requestAnimationFrame(frameLoop); } }
  window.addEventListener("scroll", request, { passive: true });
  window.addEventListener("resize", request);
  frameLoop(performance.now());
  if (!reduceMotion) {
    (function loop(t) { plates.forEach(function (f) { f(window.innerHeight || 800, t); }); requestAnimationFrame(loop); })(performance.now());
  }
