  /* ------------------------------------------------------------------- deck */
  /* One step at a time: a click, an arrow key or a swipe shows the slide's next build or
     plays its animation's next step, and moves to the next slide when none is left. An
     animation steps by seeking its one clock to the step's start and playing to the next. */
  (function deck() {
    var main = doc.querySelector("main.deck");
    if (!main) return;
    var track = main.querySelector(".deck-track");
    var slides = Array.prototype.slice.call(main.querySelectorAll(".slide"));
    var counter = doc.querySelector(".deck-count");
    var gridBtn = doc.querySelector(".deck-grid");
    var notesBtn = doc.querySelector(".deck-notes");
    var panel = html("aside", "deck-notes-panel", null, doc.body);
    panel.hidden = true;
    var still = location.hash === "#still";
    if (still) main.classList.add("capture");
    var at = 0, done = slides.map(function () { return 0; }), timer = null;

    function stepsOf(slide) {
      var out = [];
      slide.querySelectorAll("[data-build], .anim-svg svg[data-steps]").forEach(function (el) {
        if (el.tagName.toLowerCase() !== "svg") { out.push({ el: el }); return; }
        var starts = el.getAttribute("data-steps").split(",").map(Number);
        var end = Number(el.getAttribute("data-end")) || starts[starts.length - 1];
        starts.forEach(function (s, i) { out.push({ svg: el, from: s, to: i + 1 < starts.length ? starts[i + 1] : end, first: i === 0 }); });
      });
      return out;
    }
    var steps = slides.map(stepsOf);
    // An animation's first step plays on arrival, so a click never shows an empty canvas.
    function base(n) { return steps[n].filter(function (s) { return s.first; }).length; }

    function seek(svg, t) {
      if (!svg.getAnimations) return;
      svg.getAnimations({ subtree: true }).forEach(function (a) { a.pause(); a.currentTime = t * 1000; });
    }
    function play(step, instant) {
      clearTimeout(timer);
      if (instant || reduceMotion || still) { seek(step.svg, step.to); return; }
      seek(step.svg, step.from);
      step.svg.getAnimations({ subtree: true }).forEach(function (a) { a.play(); });
      timer = setTimeout(function () { seek(step.svg, step.to); }, (step.to - step.from) * 1000);
    }
    function paint(n, instant) {
      var list = steps[n], shown = done[n];
      list.forEach(function (s, i) { if (s.el) s.el.classList.toggle("on", i < shown); });
      var last = {};
      list.forEach(function (s, i) { if (s.svg && i < shown) last[i] = s; });
      var keys = Object.keys(last);
      if (keys.length) play(last[keys[keys.length - 1]], instant);
      list.forEach(function (s, i) { if (s.svg && i < shown && last[i] !== s) seek(s.svg, s.to); });
    }
    function show(n, instant) {
      at = Math.max(0, Math.min(slides.length - 1, n));
      if (done[at] < base(at)) done[at] = base(at);
      // A captured slide is a still: every build shown, every animation at its end.
      if (still) done[at] = steps[at].length;
      track.style.transform = "translateX(" + (-100 * at) + "%)";
      slides.forEach(function (s, i) { s.classList.toggle("on", i === at); s.setAttribute("aria-hidden", i === at ? "false" : "true"); });
      if (counter) counter.textContent = (at + 1) + " / " + slides.length;
      var notes = slides[at].querySelector(".slide-notes");
      while (panel.firstChild) panel.removeChild(panel.firstChild);
      if (notes) Array.prototype.forEach.call(notes.childNodes, function (c) { panel.appendChild(c.cloneNode(true)); });
      panel.hidden = !(main.classList.contains("show-notes") && notes);
      paint(at, instant);
      try { history.replaceState(null, "", "#" + slides[at].id); } catch (e) { /* sandboxed frame: the hash stays */ }
    }
    function next() {
      if (done[at] < steps[at].length) { done[at] += 1; paint(at, false); return; }
      if (at < slides.length - 1) show(at + 1, false);
    }
    function prev() {
      if (done[at] > base(at)) { done[at] -= 1; paint(at, true); return; }
      if (at > 0) show(at - 1, true);
    }
    function overview(on) {
      main.classList.toggle("overview", on);
      if (gridBtn) gridBtn.setAttribute("aria-pressed", on ? "true" : "false");
      if (!on) show(at, true);
    }
    doc.querySelector(".deck-next").addEventListener("click", next);
    doc.querySelector(".deck-prev").addEventListener("click", prev);
    if (gridBtn) gridBtn.addEventListener("click", function () { overview(!main.classList.contains("overview")); });
    if (notesBtn) notesBtn.addEventListener("click", function () {
      var on = !main.classList.contains("show-notes");
      main.classList.toggle("show-notes", on);
      notesBtn.setAttribute("aria-pressed", on ? "true" : "false");
      show(at, true);
    });
    slides.forEach(function (s, i) {
      s.addEventListener("click", function () { if (main.classList.contains("overview")) { at = i; overview(false); } });
    });
    doc.addEventListener("keydown", function (ev) {
      var tag = (ev.target && ev.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "select" || tag === "textarea") return;
      var key = ev.key;
      if (key === "ArrowRight" || key === "PageDown" || key === " ") { ev.preventDefault(); next(); }
      else if (key === "ArrowLeft" || key === "PageUp") { ev.preventDefault(); prev(); }
      else if (key === "Home") show(0, true);
      else if (key === "End") show(slides.length - 1, true);
      else if (key === "o" || key === "O") overview(!main.classList.contains("overview"));
      else if (key === "Escape" && main.classList.contains("overview")) overview(false);
    });
    var x0 = null;
    main.addEventListener("pointerdown", function (ev) { x0 = ev.clientX; });
    main.addEventListener("pointerup", function (ev) {
      if (x0 === null || main.classList.contains("overview")) return;
      var dx = ev.clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 50) { if (dx < 0) next(); else prev(); }
    });
    var start = slides.map(function (s) { return "#" + s.id; }).indexOf(location.hash);
    window.briefingDeck = { show: show, next: next, prev: prev };
    show(start >= 0 ? start : 0, true);
  })();
