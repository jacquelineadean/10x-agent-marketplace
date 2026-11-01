  /* ------------------------------------------------------------- panorama */
  // A wide painting to look along. The world holds the painting at its own pixel size; the
  // view scales it to a fixed height and pans it as the reader drags, presses the arrow
  // keys or the edge buttons. Animals are rigs that walk, swim, crawl, glide, leap or hop
  // over their range; the tide fades a layer, slides the surf and hides shore animals.
  var JOURNAL = {};
  function journalSeen(key) {
    var found = null;
    try { found = JSON.parse(localStorage.getItem(key) || "null"); } catch (e) { found = null; }
    var seen = found && typeof found === "object" ? found : {};
    Object.keys(JOURNAL[key] || {}).forEach(function (id) { seen[id] = 1; });
    return seen;
  }
  // Each find is merged into what is stored at that moment, so finds made in another
  // panorama on the page, or in another tab, are never written over.
  function journalAdd(key, id) {
    var seen = journalSeen(key);
    seen[id] = 1;
    (JOURNAL[key] = JOURNAL[key] || {})[id] = 1;
    try { localStorage.setItem(key, JSON.stringify(seen)); } catch (e) { /* storage blocked: finds last this visit */ }
    window.dispatchEvent(new CustomEvent("chronicle-journal", { detail: key }));
  }

  function initPanorama(node, spec) {
    var view = node.querySelector(".pa-view");
    var world = node.querySelector(".pa-world");
    var card = node.querySelector(".pa-card");
    var navL = node.querySelector(".pa-nav-l");
    var navR = node.querySelector(".pa-nav-r");
    var spot = node.querySelector(".pa-zone-spot");
    var range = node.querySelector(".pa-tide-range");
    var note = node.querySelector(".pa-tide-note");
    var zoneBtns = Array.prototype.slice.call(node.querySelectorAll(".pa-zone"));
    var tideLayers = Array.prototype.slice.call(node.querySelectorAll(".pa-l-tide"));
    var surfLayers = Array.prototype.slice.call(node.querySelectorAll(".pa-l-surf"));
    var W = spec.width, H = spec.height, V = spec.view || {}, T = spec.tide || null;
    var k = 1, pan = 0, goal = 0, maxPan = 0, vw = 0, held = null, focusZone = -1, last = 0, laid = false;
    var tide = T ? T.start : 1, armed = true;
    var info = {};
    (spec.animals || []).forEach(function (a) { if (!info[a.id]) info[a.id] = a; });
    node.classList.add("live");

    var animals = Array.prototype.slice.call(node.querySelectorAll(".pa-animal")).map(function (el, i) {
      function nums(key) { return (el.getAttribute("data-" + key) || "").split(" ").map(Number); }
      var at = nums("at"), foot = nums("foot"), span = nums("range"), rest = nums("rest");
      var face = Number(el.getAttribute("data-face")) || 1;
      return {
        el: el, flip: el.querySelector(".rig"), rig: rigOf(el.querySelector(".rig")),
        species: el.getAttribute("data-species"), behavior: el.getAttribute("data-behavior") || "wander",
        x: at[0], y: at[1], fx: foot[0], fy: foot[1], lo: span[0], hi: span[1],
        rest: [rest[0] || 2, rest.length > 1 ? rest[1] : 6],
        speed: Number(el.getAttribute("data-speed")) || 30, stride: Number(el.getAttribute("data-stride")) || 60,
        face: face, start: face, tide: el.getAttribute("data-tide") || "",
        z: Number(el.getAttribute("data-z")) || 0, offset: Number(el.getAttribute("data-offset")) || 0,
        height: Number(el.getAttribute("data-height")) || 60, period: Number(el.getAttribute("data-period")) || 6.5,
        timer: 1 + (i % 5) * 0.7, goal: null, path: 0, from: 0, hop: 0, seen: 1, dy: 0, turn: 0
      };
    });

    function tideAlpha(a) {
      if (a.tide === "low") return clamp((0.62 - tide) * 4, 0, 1);
      if (a.tide === "high") return clamp((tide - 0.45) * 4, 0, 1);
      return 1;
    }
    function place(a) {
      var s = a.el.style;
      s.left = (a.x - a.fx).toFixed(1) + "px";
      s.top = (a.y + a.dy - a.fy).toFixed(1) + "px";
      s.zIndex = String(Math.max(2, Math.round(a.y) + a.z));
      // Mirrors turn about the foot point, so an animal turns where it stands.
      a.flip.style.transform = (a.face < 0 ? "scaleX(-1)" : "") + (a.turn ? " rotate(" + a.turn.toFixed(1) + "deg)" : "");
      var o = a.seen * tideAlpha(a);
      s.opacity = o >= 0.999 ? "" : o.toFixed(3);
      s.visibility = o < 0.02 ? "hidden" : "";
    }
    function rested(a) { return a.rest[0] + Math.random() * Math.max(0, a.rest[1] - a.rest[0]); }

    function move(a, dt, now) {
      var moving = false, cycles = 0, span = Math.max(1, a.hi - a.lo), b = a.behavior;
      a.dy = 0; a.turn = 0; a.seen = 1;
      if (b === "wander" || b === "scuttle") {
        if (a.goal === null) {
          a.timer -= dt;
          if (a.timer <= 0 && a.hi > a.lo) a.goal = a.lo + Math.random() * span;
        } else {
          var dx = a.goal - a.x, step = a.speed * dt;
          if (Math.abs(dx) <= Math.max(1, step)) { a.x = a.goal; a.goal = null; a.timer = rested(a); }
          else {
            a.x += step * (dx > 0 ? 1 : -1);
            moving = true; cycles = step / a.stride;
            if (b === "wander") a.face = dx > 0 ? 1 : -1;
          }
        }
      } else if (b === "swim") {
        a.path += a.speed * dt;
        var u = (a.path % (2 * span)) / span;
        var nx = a.lo + (u < 1 ? u : 2 - u) * span;
        a.face = u < 1 ? 1 : -1;
        cycles = Math.abs(nx - a.x) / a.stride;
        a.x = nx; moving = true;
      } else if (b === "crawl") {
        a.path += a.speed * dt;
        var q = (a.path + a.offset) % (span + 120);
        a.x = a.start > 0 ? a.lo + Math.min(q, span) : a.hi - Math.min(q, span);
        a.seen = q > span ? 0 : clamp(Math.min(q / 30, (span - q) / 40), 0, 1);
        a.dy = Math.sin(q / 37 + a.rig.t0) * 3;
        moving = true; cycles = 2.2 * dt;
      } else if (b === "glide") {
        a.path += a.speed * dt;
        var g = (a.path + a.offset) % span;
        a.x = a.start > 0 ? a.lo + g : a.hi - g;
        a.dy = Math.sin(now / 1700 + a.rig.t0) * 12;
        a.seen = clamp(Math.min(g / 80, (span - g) / 80), 0, 1);
      } else if (b === "arc") {
        var t = (now / 1000 + a.rig.t0) % a.period, leap = 0.28 * a.period;
        if (t < leap) {
          var f = t / leap;
          a.x = a.start > 0 ? a.lo + f * span : a.hi - f * span;
          a.dy = -Math.sin(Math.PI * f) * a.height;
          a.turn = -40 + 80 * f;
        } else a.seen = 0;
      } else if (b === "hop") {
        if (a.goal === null) {
          a.timer -= dt;
          if (a.timer <= 0 && a.hi > a.lo) { a.goal = a.lo + Math.random() * span; a.from = a.x; a.hop = 0; a.face = a.goal > a.x ? 1 : -1; }
        } else {
          a.hop = Math.min(1, a.hop + dt / 0.45);
          a.x = a.from + (a.goal - a.from) * a.hop;
          a.dy = -Math.sin(Math.PI * a.hop) * 26;
          if (a.hop >= 1) { a.goal = null; a.timer = rested(a); }
        }
      }
      rigStep(a.rig, now, dt, moving, cycles);
      place(a);
    }

    function apply() {
      world.style.transform = "translateX(" + (-pan).toFixed(1) + "px) scale(" + k.toFixed(4) + ")";
      navL.disabled = pan <= 0.5;
      navR.disabled = pan >= maxPan - 0.5;
      if (!zoneBtns.length) return;
      var left = pan / k, right = (pan + vw) / k, middle = (left + right) / 2, any = false;
      var on = spec.zones.map(function (z, i) {
        if (focusZone >= 0) return i === focusZone;
        return Math.max(0, Math.min(right, z.to) - Math.max(left, z.from)) >= 0.55 * (z.to - z.from);
      });
      on.forEach(function (v) { any = any || v; });
      if (!any) on = spec.zones.map(function (z) { return middle >= z.from && middle < z.to; });
      zoneBtns.forEach(function (btn, i) {
        if (on[i]) btn.setAttribute("aria-current", "true"); else btn.removeAttribute("aria-current");
      });
    }
    function panTo(x) {
      goal = clamp(x * k - vw / 2, 0, maxPan);
      if (reduceMotion) { pan = goal; apply(); }
    }
    function layout() {
      vw = view.clientWidth;
      if (!vw) return;
      var vh = vw < 640 ? (V.phone || 360) : (V.desktop || 520);
      k = vh / H;
      if (W * k < vw) { k = vw / W; vh = H * k; }
      view.style.height = vh.toFixed(0) + "px";
      maxPan = Math.max(0, W * k - vw);
      if (!laid && V.start) goal = maxPan * V.start;
      laid = true;
      pan = goal = clamp(goal, 0, maxPan);
      navL.hidden = navR.hidden = maxPan <= 0;
      apply();
    }

    // The tide: a layer fades in, the surf slides up the beach, shore animals come and go.
    function setTide(v) {
      tide = clamp(v, 0, 1);
      var shift = T.shift || [0, 0];
      tideLayers.forEach(function (img) { img.style.opacity = tide.toFixed(2); });
      surfLayers.forEach(function (img) {
        img.style.translate = (shift[0] * (1 - tide)).toFixed(1) + "px " + (shift[1] * (1 - tide)).toFixed(1) + "px";
        img.style.opacity = (0.6 + 0.4 * tide).toFixed(2);
      });
      var said = "";
      (T.notes || []).forEach(function (n) { if (tide >= n.from) said = n.text; });
      if (note) note.textContent = said;
      if (range) {
        range.value = String(Math.round(tide * 100));
        range.setAttribute("aria-valuetext", said || Math.round(tide * 100) + "% of the way to " + T.words[1].toLowerCase());
      }
      animals.forEach(place);
    }
    function watchTide() {
      var left = pan / k, right = (pan + vw) / k, best = null, near = Infinity;
      var shown = (T.watch || []).some(function (r) {
        return Math.max(0, Math.min(right, r[1]) - Math.max(left, r[0])) >= 0.3 * (r[1] - r[0]);
      });
      if (shown) return;
      (T.watch || []).forEach(function (r) {
        var d = Math.abs((r[0] + r[1]) / 2 - (left + right) / 2);
        if (d < near) { near = d; best = r; }
      });
      if (best) panTo((best[0] + best[1]) / 2);
    }

    function pick(a, quiet) {
      var about = info[a.species] || {};
      card.textContent = "";
      if (about.where) html("p", "pa-kicker", about.where, card);
      var name = html("h4", "pa-name", about.name, card);
      if (about.latin) { name.appendChild(doc.createTextNode(" ")); html("em", "pa-latin", about.latin, name); }
      html("p", "pa-fact", about.fact, card);
      animals.forEach(function (o) { o.el.classList.toggle("picked", o.species === a.species); });
      if (spec.journal) journalAdd(spec.journal, a.species);
      if (!quiet) card.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    }
    animals.forEach(function (a) {
      a.el.addEventListener("click", function () { pick(a, false); });
      if (reduceMotion) rigPose(a.rig);
      place(a);
    });

    // The journal: one chip per species, found or not, shared by panoramas with one key.
    var species = Object.keys(info);
    if (spec.journal && species.length > 1) {
      var box = html("div", "pa-journal", null, null);
      card.parentNode.insertBefore(box, card.nextSibling);
      var head = html("p", "pa-journal-head", "", box);
      var list = html("div", "pa-journal-list", null, box);
      var chips = species.map(function (id) {
        var chip = html("button", "pa-chip", info[id].name, list);
        chip.type = "button";
        var state = html("span", "pa-chip-state", "", chip);
        chip.addEventListener("click", function () {
          var first = animals.filter(function (a) { return a.species === id; })[0];
          if (!first) return;
          if (T && first.tide === "high" && tide < 0.5) setTide(0.85);
          if (T && first.tide === "low" && tide > 0.6) setTide(0.15);
          focusZone = -1;
          panTo(first.x);
          pick(first, true);
        });
        return { id: id, chip: chip, state: state };
      });
      var tally = function () {
        var seen = journalSeen(spec.journal), found = 0;
        chips.forEach(function (c) {
          var on = !!seen[c.id];
          if (on) found += 1;
          c.chip.classList.toggle("found", on);
          c.state.textContent = on ? ", found" : ", not found yet";
        });
        head.textContent = "Field journal: " + found + " of " + chips.length + " found." + (found === chips.length ? " Every one found." : " Pick an animal in the painting, or a name below.");
      };
      tally();
      window.addEventListener("chronicle-journal", tally);
      window.addEventListener("storage", function (e) { if (e.key === spec.journal) tally(); });
    }

    zoneBtns.forEach(function (btn, i) {
      btn.addEventListener("click", function () {
        var z = spec.zones[i];
        focusZone = i;
        panTo((z.from + z.to) / 2);
        if (spot) {
          spot.style.left = z.from + "px";
          spot.style.width = (z.to - z.from) + "px";
          spot.classList.remove("flash");
          void spot.offsetWidth;
          spot.classList.add("flash");
        }
        card.textContent = "";
        html("p", "pa-kicker", "Place", card);
        html("h4", "pa-name", z.label, card);
        html("p", "pa-fact", z.text, card);
        animals.forEach(function (o) { o.el.classList.remove("picked"); });
        apply();
      });
    });

    if (T && range) {
      range.addEventListener("input", function () {
        setTide(Number(range.value) / 100);
        if (armed) { armed = false; watchTide(); }
      });
      range.addEventListener("change", function () { armed = true; });
      setTide(tide);
    }

    function nudge(by) {
      focusZone = -1;
      goal = clamp(goal + by, 0, maxPan);
      if (reduceMotion) { pan = goal; apply(); }
    }
    navL.addEventListener("click", function () { nudge(-0.6 * vw); });
    navR.addEventListener("click", function () { nudge(0.6 * vw); });
    view.addEventListener("keydown", function (e) {
      if (e.target !== view) return;
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") nudge((e.key === "ArrowLeft" ? -0.35 : 0.35) * vw);
      else if (e.key === "Home" || e.key === "End") nudge(e.key === "Home" ? -maxPan : maxPan);
      else return;
      e.preventDefault();
    });
    view.addEventListener("pointerdown", function (e) {
      if (e.button !== 0 || e.target.closest("button")) return;
      held = { x: e.clientX, pan: pan, id: e.pointerId };
      goal = pan;
      try { view.setPointerCapture(e.pointerId); } catch (err) { /* no capture: the drag ends at the view's edge */ }
    });
    view.addEventListener("pointermove", function (e) {
      if (!held || e.pointerId !== held.id) return;
      var dx = e.clientX - held.x;
      if (Math.abs(dx) > 4) focusZone = -1;
      pan = goal = clamp(held.pan - dx, 0, maxPan);
      apply();
    });
    ["pointerup", "pointercancel"].forEach(function (type) { view.addEventListener(type, function () { held = null; }); });
    // Tabbing to an animal off to one side pans to it; the browser's own scroll of the
    // clipped view is undone, so the pan stays the only offset.
    view.addEventListener("scroll", function () { view.scrollLeft = 0; view.scrollTop = 0; });
    world.addEventListener("focusin", function (e) {
      var el = e.target.closest(".pa-animal");
      var a = el && animals.filter(function (o) { return o.el === el; })[0];
      if (a && (a.x * k < pan + 40 || a.x * k > pan + vw - 40)) panTo(a.x);
    });

    layout();
    if (window.ResizeObserver) {
      // Layout runs on the next frame, outside the observer, since it sets the view's height.
      new ResizeObserver(function () { requestAnimationFrame(function () { if (view.clientWidth !== vw) layout(); }); }).observe(view);
    } else window.addEventListener("resize", layout);

    tickers.push(function (vh, now) {
      if (!vw) return;
      var r = view.getBoundingClientRect();
      if (r.width === 0 || r.bottom < -100 || r.top > vh + 100) { last = 0; return; }
      var dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      if (Math.abs(goal - pan) > 0.5) { pan += (goal - pan) * Math.min(1, 6 * dt); apply(); }
      else if (pan !== goal) { pan = goal; apply(); }
      if (!reduceMotion && dt > 0) animals.forEach(function (a) { move(a, dt, now); });
    });
  }
  INIT.panorama = initPanorama;
