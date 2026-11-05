  /* ----------------------------------------------------------------- tour */
  // A painted map whose stops open scenes in the same box. Opening a stop zooms the map
  // toward it; stop to stop slides; back to the map zooms out from the stop just left.
  // The page's bar carries the route: a mark per stop and a walker at the open stop, or,
  // while the reader is in the chapters, at the stop the reading has reached.
  function initTour(node, spec) {
    var app = node.querySelector(".tr-app");
    var hub = node.querySelector(".tr-hub");
    var frame = hub.querySelector(".frame");
    var scenes = Array.prototype.slice.call(node.querySelectorAll(".tr-scene"));
    var marks = Array.prototype.slice.call(hub.querySelectorAll(".tr-stop"));
    var where = node.querySelector(".tr-where");
    var count = node.querySelector(".tr-count");
    var toMap = node.querySelector(".tr-tomap");
    var prev = node.querySelector(".tr-prev");
    var next = node.querySelector(".tr-next");
    var fs = node.querySelector(".tr-fs");
    var pinCard = node.querySelector(".tr-pin-card");
    var pinText = Array.prototype.slice.call(node.querySelectorAll(".tr-pins dd"));
    var stops = spec.stops || [], n = stops.length, cur = -1, busy = false;
    node.classList.add("live");
    scenes.forEach(function (s) { s.hidden = true; });

    function load() {
      var found = null;
      try { found = JSON.parse(localStorage.getItem(spec.key) || "null"); } catch (e) { found = null; }
      return found && typeof found === "object" ? found : {};
    }
    var visited = load();
    function remember(id) {
      var seen = load();
      Object.keys(visited).forEach(function (k) { seen[k] = 1; });
      seen[id] = 1;
      visited = seen;
      try { localStorage.setItem(spec.key, JSON.stringify(seen)); } catch (e) { /* storage blocked: visits last this visit */ }
    }

    var trail = buildTrail();
    function paint() {
      var done = 0;
      marks.forEach(function (m, i) {
        var seen = !!visited[stops[i].id];
        if (seen) done += 1;
        m.classList.toggle("visited", seen);
        m.classList.toggle("current", i === cur);
      });
      where.textContent = cur < 0 ? (spec.title ? spec.title + " · " : "") + n + " stops" : "Stop " + (cur + 1) + " of " + n + " · " + stops[cur].title;
      toMap.hidden = cur < 0;
      prev.disabled = cur < 0;
      next.disabled = cur >= n - 1;
      count.textContent = done + " of " + n + " stops visited.";
      syncTrail();
    }

    function topOf() {
      var r = app.getBoundingClientRect();
      if (r.top < 0 || r.top > (window.innerHeight || 800) * 0.6) app.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    }
    function enter(el, cls) {
      el.classList.add(cls);
      requestAnimationFrame(function () { requestAnimationFrame(function () { el.classList.remove(cls); }); });
    }
    function show(i) {
      if (busy || i === cur || i < -1 || i >= n) return;
      var old = cur;
      cur = i;
      if (i >= 0) remember(stops[i].id);
      pinCard.hidden = true;
      paint();
      var out = old >= 0 ? scenes[old] : hub, into = i >= 0 ? scenes[i] : hub;
      function swap() {
        out.hidden = true;
        into.hidden = false;
        if (i >= 0) into.querySelector(".tr-title").focus({ preventScroll: true });
        else if (marks[old]) marks[old].focus({ preventScroll: true });
        topOf();
      }
      if (reduceMotion) { swap(); return; }
      busy = true;
      if (old < 0) {
        frame.style.transformOrigin = stops[i].at[0] + "% " + stops[i].at[1] + "%";
        hub.classList.add("tr-zoom");
        setTimeout(function () { hub.classList.remove("tr-zoom"); swap(); enter(into, "tr-enter"); busy = false; }, 620);
      } else if (i < 0) {
        frame.style.transformOrigin = stops[old].at[0] + "% " + stops[old].at[1] + "%";
        hub.classList.add("tr-zoom", "tr-instant");
        swap();
        requestAnimationFrame(function () { requestAnimationFrame(function () { hub.classList.remove("tr-zoom", "tr-instant"); busy = false; }); });
      } else {
        out.classList.add(i > old ? "tr-leave-l" : "tr-leave-r");
        setTimeout(function () {
          out.classList.remove("tr-leave-l", "tr-leave-r");
          swap();
          enter(into, i > old ? "tr-enter-r" : "tr-enter-l");
          busy = false;
        }, 280);
      }
    }

    marks.forEach(function (m, i) {
      m.addEventListener("click", function (e) { e.preventDefault(); show(i); });
    });
    scenes.forEach(function (s) {
      s.querySelector(".tr-back").addEventListener("click", function (e) { e.preventDefault(); show(-1); });
      var on = s.querySelector(".tr-on");
      if (on) on.addEventListener("click", function (e) { e.preventDefault(); show(Number(on.getAttribute("data-stop"))); });
      var read = s.querySelector(".tr-read");
      if (read) read.addEventListener("click", function () { if (doc.fullscreenElement) doc.exitFullscreen(); });
    });
    toMap.addEventListener("click", function () { show(-1); });
    prev.addEventListener("click", function () { show(cur - 1); });
    next.addEventListener("click", function () { show(cur + 1); });

    hub.querySelectorAll(".tr-pin").forEach(function (pin) {
      pin.addEventListener("click", function (e) {
        e.stopPropagation();
        var k = Number(pin.getAttribute("data-pin"));
        pinCard.textContent = "";
        html("h4", null, pin.getAttribute("aria-label"), pinCard);
        if (pinText[k]) pinCard.appendChild(pinText[k].cloneNode(true));
        pinCard.hidden = false;
      });
    });
    hub.addEventListener("click", function () { pinCard.hidden = true; });

    // Full screen uses the browser's own, so Escape and the system controls close it.
    if (app.requestFullscreen && doc.fullscreenEnabled) {
      fs.hidden = false;
      fs.addEventListener("click", function () {
        if (doc.fullscreenElement === app) doc.exitFullscreen();
        else app.requestFullscreen().catch(function () { fs.hidden = true; });
      });
      doc.addEventListener("fullscreenchange", function () {
        var full = doc.fullscreenElement === app;
        app.classList.toggle("tr-full", full);
        fs.textContent = full ? "Close" : "Full screen";
      });
      app.addEventListener("keydown", function (e) {
        if (doc.fullscreenElement !== app || e.target.closest(".pa-view, input, [role=tab]")) return;
        if (e.key === "ArrowLeft") show(cur - 1);
        else if (e.key === "ArrowRight") show(cur + 1);
      });
    }

    function buildTrail() {
      var bar = doc.querySelector(".spanbar-in");
      if (!bar || bar.querySelector(".tr-trail") || n < 2) return null;
      var box = html("div", "tr-trail", null, null);
      box.setAttribute("role", "group");
      box.setAttribute("aria-label", "Stops on the tour");
      // After the track, and after a game's tally when the page has one, so the route
      // takes the bar's free width.
      var after = bar.querySelector(".tally") || bar.querySelector(".spanbar-track");
      bar.insertBefore(box, after ? after.nextSibling : null);
      bar.parentNode.classList.add("has-trail");
      html("span", "tr-road", null, box);
      var walker = html("span", "tr-walker", null, box);
      walker.setAttribute("aria-hidden", "true");
      var buttons = stops.map(function (s, i) {
        var b = html("button", "tr-mark", String(i + 1), box);
        b.type = "button";
        b.style.left = (100 * i / (n - 1)).toFixed(2) + "%";
        b.setAttribute("aria-label", "Stop " + (i + 1) + ": " + s.title);
        b.title = s.title;
        b.addEventListener("click", function () {
          var r = app.getBoundingClientRect();
          if (r.top < 0 || r.top > (window.innerHeight || 800)) app.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
          show(i);
        });
        return b;
      });
      var sections = stops.map(function (s) { return s.chapter ? doc.getElementById(s.chapter) : null; });
      return { walker: walker, buttons: buttons, sections: sections };
    }
    // Where the reader is: on the tour while it fills the middle of the screen or full
    // screen, else in the chapters, between the stops whose chapters they have reached.
    function readingAt(vh) {
      var r = app.getBoundingClientRect();
      if (doc.fullscreenElement === app || (r.top < vh * 0.65 && r.bottom > vh * 0.35)) return null;
      var at = -1;
      trail.sections.forEach(function (sec, i) {
        if (!sec) return;
        var s = sec.getBoundingClientRect();
        if (s.top < vh * 0.4) at = i + clamp((vh * 0.4 - s.top) / Math.max(1, s.height), 0, 0.99);
      });
      return at;
    }
    function syncTrail(vh) {
      if (!trail) return;
      var at = readingAt(vh || window.innerHeight || 800);
      var pos = at === null ? Math.max(0, cur) : Math.max(0, at);
      trail.walker.style.left = (100 * pos / (n - 1)).toFixed(2) + "%";
      trail.buttons.forEach(function (b, i) {
        var passed = at === null ? !!visited[stops[i].id] || i === cur : i <= at;
        var here = at === null ? i === cur : i === Math.floor(at);
        b.classList.toggle("passed", passed);
        b.classList.toggle("current", here);
        if (here) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
      });
    }
    if (trail) scrollers.push(syncTrail);
    paint();
  }
  INIT.tour = initTour;
