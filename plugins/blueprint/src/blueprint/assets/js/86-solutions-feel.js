  /* -------------------------------------------------------- solutions: feel */
  /* A measure with a feel plays its value. A wait runs each compared variant's bar for
     that long in real time; failures marks that many of 100 requests. The words for a wait
     follow Nielsen's three response-time limits: 0.1 s reads as instant, 1 s keeps the
     flow of thought, 10 s is as long as attention holds. */
  var SOL_LIMITS = [[100, "reads as instant"], [1000, "a pause, the flow of thought holds"], [10000, "a wait, attention drifts"]];
  /* A bar never runs longer than this; its text still gives the whole wait. */
  var SOL_LONGEST = 15000;
  /* A moved slider replays the wait this long after it comes to rest. */
  var SOL_REST = 400;
  function solFelt(ms) {
    for (var i = 0; i < SOL_LIMITS.length; i++) if (ms <= SOL_LIMITS[i][0]) return SOL_LIMITS[i][1];
    return "too long, most people leave";
  }
  function solFeel(parent, spec, painters) {
    spec.measures.filter(function (m) { return m.feel; }).forEach(function (m) {
      var box = html("section", "sol-feel", null, parent);
      html("h4", "sol-h", "Feel it: " + m.label, box);
      (m.feel.kind === "wait" ? solWait : solFailures)(box, m, painters);
    });
  }
  function solLane(lanes, label) {
    var lane = html("div", "sol-lane", null, lanes);
    html("span", "sol-lane-name", label, lane);
    return lane;
  }
  function solWait(box, m, painters) {
    var bar = html("div", "sol-run", null, box);
    var go = html("button", "sol-go", m.feel.action || "Send a request", bar);
    go.type = "button";
    var lab = html("label", "sol-check", null, bar);
    var auto = html("input", null, null, lab);
    auto.type = "checkbox"; auto.checked = true;
    html("span", null, "Replay when a value changes", lab);
    var lanes = html("div", "sol-lanes", null, box);
    var timers = [], last = null, ran = false, shown = "";
    function draw(play) {
      timers.forEach(clearTimeout);
      timers = [];
      solClear(lanes);
      last.live.forEach(function (v) {
        var r = last.by[v.id];
        var lane = solLane(lanes, v.label);
        var fill = html("i", null, null, html("span", "sol-track", null, lane));
        var out = html("span", "sol-lane-out", null, lane);
        if (r.error) { out.textContent = "n/a"; return; }
        var ms = r[m.id] * (m.unit === "s" ? 1000 : 1);
        var text = solShow(r[m.id], m) + ": " + solFelt(ms);
        function arrive() { lane.classList.add("done"); fill.style.width = "100%"; out.textContent = text; }
        if (!play) { out.textContent = text; return; }
        if (reduceMotion) { arrive(); return; }
        var run = Math.min(Math.max(ms, 0), SOL_LONGEST);
        out.textContent = "Waiting";
        /* Reading the width makes the browser start the transition from zero. */
        void fill.offsetWidth;
        fill.style.transition = "width " + run + "ms linear";
        fill.style.width = "100%";
        timers.push(setTimeout(arrive, run));
      });
    }
    go.addEventListener("click", function () { ran = true; if (last) draw(true); });
    painters.push(function (f) {
      var now = f.live.map(function (v) { return v.id + v.label + (f.by[v.id].error || f.by[v.id][m.id]); }).join("|");
      last = f;
      /* A change that leaves these waits alone must not cut a running replay short. */
      if (now === shown) return;
      shown = now;
      draw(false);
      if (ran && auto.checked && !reduceMotion) timers.push(setTimeout(function () { draw(true); }, SOL_REST));
    });
  }
  function solFailures(box, m, painters) {
    var lanes = html("div", "sol-lanes", null, box);
    painters.push(function (f) {
      solClear(lanes);
      f.live.forEach(function (v) {
        var r = f.by[v.id];
        var lane = solLane(lanes, v.label);
        var dots = html("span", "sol-dots", null, lane);
        var failed = r.error ? 0 : clamp(Math.round(r[m.id]), 0, 100);
        /* Failures spread evenly over the 100, so the same value always marks the same dots. */
        for (var i = 0; i < 100; i++) html("i", Math.floor((i + 1) * failed / 100) > Math.floor(i * failed / 100) ? "bad" : null, null, dots);
        var text = r.error ? "n/a" : failed + " of 100 requests fail (" + solShow(r[m.id], m) + ")";
        dots.setAttribute("role", "img");
        dots.setAttribute("aria-label", text);
        html("span", "sol-lane-out", text, lane);
      });
    });
  }
