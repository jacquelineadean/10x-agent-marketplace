  /* ------------------------------------------------------------- tile map */
  /* Equal squares for regions, colored by a value or a category; with frames, a
     slider and a play button walk the map through time. */
  function initTilemap(node, spec) {
    var mount = node.querySelector(".mount");
    var tiles = spec.tiles || [];
    var frames = spec.frames || null;
    var values = spec.values || {};
    var scale = spec.scale || {};
    var kind = scale.kind || (scale.categories ? "category" : "sequential");
    var format = (spec.format && spec.format.value) || spec.format || "int";
    if (typeof format !== "string") format = "int";
    var idx = frames ? clamp(spec.start == null ? frames.length - 1 : spec.start, 0, frames.length - 1) : 0;
    var cats = {};
    (scale.categories || []).forEach(function (c, i) { cats[String(c.value)] = { label: c.label || c.value, color: colorOf(c.color, "var(--s" + (i + 1) + ")"), on: !!c.dark }; });
    var byId = {};
    tiles.forEach(function (t) { byId[t.id] = t; });
    function valueOf(id, i) {
      var v = values[id];
      if (Array.isArray(v)) return v[Math.min(i, v.length - 1)];
      return v;
    }
    var nums = [];
    Object.keys(values).forEach(function (k) { var v = values[k]; (Array.isArray(v) ? v : [v]).forEach(function (x) { if (typeof x === "number") nums.push(x); }); });
    var lo = scale.min != null ? scale.min : Math.min.apply(null, nums.concat([0]));
    var hi = scale.max != null ? scale.max : Math.max.apply(null, nums.concat([1]));
    var STEPS = 6;
    function bucket(v) { return clamp(Math.floor((v - lo) / Math.max(hi - lo, 1e-9) * STEPS), 0, STEPS - 1); }
    function paint(v) {
      if (v === null || v === undefined || v === "") return { fill: "var(--surface)", dark: false, empty: true };
      if (kind === "category") { var c = cats[String(v)]; return { fill: c ? c.color : "var(--muted)", dark: c ? c.on : true }; }
      var b = bucket(Number(v));
      return { fill: "var(--seq-" + b + ")", dark: b >= 3 };
    }
    function show(v) {
      if (v === null || v === undefined || v === "") return "no data";
      if (kind === "category") return (cats[String(v)] || { label: String(v) }).label;
      return fmt(v, format) + (spec.unit ? " " + spec.unit : "");
    }
    var ctrl = node.querySelector(".tm-ctrl"), range = node.querySelector(".tm-range");
    var play = node.querySelector(".tm-play"), frameOut = node.querySelector(".tm-frame");
    var readout = node.querySelector(".tm-readout");
    var timer = null;
    function stop() { if (timer) { clearInterval(timer); timer = null; } if (play) play.textContent = "Play"; }
    if (ctrl && frames) {
      ctrl.hidden = false;
      range.max = String(frames.length - 1);
      range.value = String(idx);
      range.addEventListener("input", function () { stop(); idx = Number(range.value); draw(); });
      play.addEventListener("click", function () {
        if (timer) { stop(); return; }
        if (idx >= frames.length - 1) idx = 0;
        play.textContent = "Pause";
        draw();
        timer = setInterval(function () {
          if (idx >= frames.length - 1) { stop(); return; }
          idx += 1; range.value = String(idx); draw();
        }, reduceMotion ? 1200 : 650);
      });
    }
    function sentence() {
      if (!readout) return;
      var r = spec.readout;
      if (!r) { readout.textContent = ""; return; }
      var text = typeof r === "string" ? r : (r.text || "");
      var rule = (typeof r === "object" && r.count) || {};
      var count = 0, sum = 0, n = 0, top = null;
      tiles.forEach(function (t) {
        var v = valueOf(t.id, idx);
        if (v === null || v === undefined) return;
        if (typeof v === "number") { sum += v; n += 1; if (!top || v > valueOf(top.id, idx)) top = t; }
        var hit = rule.in ? rule.in.indexOf(v) >= 0 : rule.gte != null ? v >= rule.gte : rule.lte != null ? v <= rule.lte : rule.eq != null ? v === rule.eq : false;
        if (hit) count += 1;
      });
      var vars = {
        frame: frames ? labelX(frames[idx]) : "", count: String(count), total: String(tiles.length),
        sum: fmt(sum, format), mean: n ? fmt(sum / n, format) : "n/a",
        max_label: top ? top.label : "", max: top ? show(valueOf(top.id, idx)) : ""
      };
      readout.textContent = text.replace(/\{(\w+)\}/g, function (m, k) { return vars[k] !== undefined ? vars[k] : m; });
    }
    function history(id) { return frames ? frames.map(function (f, i) { return valueOf(id, i); }) : [valueOf(id, 0)]; }
    function draw() {
      while (mount.firstChild) mount.removeChild(mount.firstChild);
      var rows = 0, cols = 0;
      tiles.forEach(function (t) { rows = Math.max(rows, t.row + 1); cols = Math.max(cols, t.col + 1); });
      var W = Math.max(260, mount.clientWidth || 600), gap = 3;
      var s = Math.min(58, (W - gap * (cols - 1)) / cols);
      var gw = s * cols + gap * (cols - 1), ox = (W - gw) / 2;
      var H = s * rows + gap * (rows - 1) + 4;
      var root = svg("svg", { width: W, height: H, viewBox: "0 0 " + W + " " + H, "class": "tm-svg" }, mount);
      // Small tiles on phones fit about 0.6 em per character: when any value overflows,
      // every tile switches to the short form (11.8K) so the map reads one way.
      var vs = Math.min(15, s * 0.28), valueFormat = format;
      tiles.forEach(function (t) {
        var v = valueOf(t.id, idx);
        if (typeof v === "number" && fmt(v, format).length * vs * 0.6 > s - 4) valueFormat = "compact";
      });
      tiles.forEach(function (t) {
        var v = valueOf(t.id, idx), p = paint(v);
        var gx = ox + t.col * (s + gap), gy = t.row * (s + gap);
        var g = svg("g", { "class": "tm-tile" + (p.empty ? " empty" : "") + (p.dark ? " dark" : ""), tabindex: 0, role: "img", "aria-label": t.label + ": " + show(v) }, root);
        svg("rect", { x: gx, y: gy, width: s, height: s, rx: 3, fill: p.fill }, g);
        var fs = Math.max(8, Math.min(12.5, s * 0.23));
        txt(g, gx + 4, gy + fs + 2, t.id, { "class": "tm-id", "font-size": fs });
        if (s > 34 && kind !== "category" && typeof v === "number") {
          var vt = fmt(v, valueFormat);
          if (vt.length * vs * 0.6 <= s - 4) txt(g, gx + s / 2, gy + s * 0.8, vt, { "class": "tm-val", "text-anchor": "middle", "font-size": vs });
        }
        (spec.markers || []).forEach(function (m) {
          if (m.tile !== t.id) return;
          var k2 = Math.max(0.45, Math.min(0.75, s / 70));
          var mk = svg("g", { "class": "tm-marker", transform: "translate(" + (gx + s - 12 * k2 - 3) + "," + (gy + 10 * k2 + 3) + ")" }, g);
          svg("path", { d: ICON_PATHS[m.icon] || ICON_PATHS.parcel, transform: "scale(" + k2.toFixed(2) + ")" }, mk);
        });
        function build(tip) {
          html("div", "tip-h", t.label, tip);
          html("div", null, show(v) + (frames ? ", " + labelX(frames[idx]) : ""), tip);
          (spec.markers || []).forEach(function (m) { if (m.tile === t.id && m.label) html("div", "tip-src", m.label, tip); });
          var hist = history(t.id).filter(function (x) { return typeof x === "number"; });
          if (frames && hist.length > 2 && kind !== "category") {
            var sw = 150, sh = 30, mx = Math.max.apply(null, hist.concat([hi])) || 1;
            var sp = svg("svg", { width: sw, height: sh + 4, viewBox: "0 0 " + sw + " " + (sh + 4) }, tip);
            sp.style.display = "block"; sp.style.marginTop = "6px";
            var bw = sw / hist.length;
            hist.forEach(function (x, i) {
              var hh = Math.max(1, x / mx * sh);
              var bar = svg("rect", { x: i * bw + 0.5, y: sh - hh, width: Math.max(1, bw - 1), height: hh }, sp);
              bar.style.fill = i === idx ? "var(--tip-ink)" : "color-mix(in srgb, var(--tip-ink) 45%, transparent)";
            });
          }
        }
        g.addEventListener("pointerenter", function (ev) { var xy = pointerXY(ev); showTip(build, xy[0], xy[1]); });
        g.addEventListener("pointermove", function (ev) { var xy = pointerXY(ev); showTip(build, xy[0], xy[1]); });
        g.addEventListener("pointerleave", hideTip);
        g.addEventListener("focus", function () { var r = g.getBoundingClientRect(); showTip(build, r.left + r.width / 2, r.bottom); });
        g.addEventListener("blur", hideTip);
      });
      if (frameOut && frames) frameOut.textContent = labelX(frames[idx]);
      sentence();
    }
    var legend = node.querySelector(".tm-legend");
    if (legend) {
      if (kind === "category") {
        legend.className = "tm-legend legend";
        (scale.categories || []).forEach(function (c, i) {
          var li = html("span", "tm-key", null, legend);
          html("i", null, null, li).style.background = colorOf(c.color, "var(--s" + (i + 1) + ")");
          li.appendChild(doc.createTextNode(c.label || c.value));
        });
      } else {
        var bar = html("div", "tm-ramp", null, legend);
        for (var k = 0; k < STEPS; k++) html("i", null, null, bar).style.background = "var(--seq-" + k + ")";
        var lab = html("div", "tm-ramp-labels", null, legend);
        html("span", null, fmt(lo, format), lab);
        html("span", null, (scale.label || "") , lab);
        html("span", null, fmt(hi, format), lab);
      }
    }
    var btn = node.querySelector(".show-table"), slot = node.querySelector(".table-slot");
    if (btn && slot) {
      btn.addEventListener("click", function () {
        var open = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", open ? "false" : "true");
        btn.textContent = open ? "Show the numbers" : "Hide the numbers";
        slot.hidden = open;
        if (open) return;
        while (slot.firstChild) slot.removeChild(slot.firstChild);
        var table = html("table", "data-table", null, slot);
        var tr = html("tr", null, null, html("thead", null, null, table));
        html("th", null, "Region", tr);
        html("th", null, frames ? labelX(frames[idx]) : "Value", tr);
        var tb = html("tbody", null, null, table);
        tiles.slice().sort(function (a, b) { return a.label < b.label ? -1 : 1; }).forEach(function (t) {
          var row = html("tr", null, null, tb);
          html("td", null, t.label, row);
          html("td", null, show(valueOf(t.id, idx)), row);
        });
      });
    }
    draw();
    var lastW = mount.clientWidth;
    if (window.ResizeObserver) new ResizeObserver(function () { if (Math.abs(mount.clientWidth - lastW) > 8) { lastW = mount.clientWidth; draw(); } }).observe(mount);
  }

  /* ----------------------------------------------------------------- flow */
  /* A process as a row of steps. Each step shows its state in the selected scenario;
     selecting a step opens its story below, and a token can travel the path. */
  var FLOW_STATUS = {
    live: { label: "Live", color: "accent" },
    legacy: { label: "Legacy", color: "legacy" },
    cutover: { label: "In progress", color: "s4" },
    planned: { label: "Planned", color: "muted" }
  };
  function initFlow(node, spec) {
    var items = Array.prototype.slice.call(node.querySelectorAll(".fl-node"));
    var detail = node.querySelector(".fl-detail");
    var seg = node.querySelector(".seg");
    var statuses = spec.statuses || FLOW_STATUS;
    var labels = spec.labels || [];
    var side = Math.max(0, labels.length - 1);
    var selected = -1;
    node.classList.add("live");
    function val(n, key) {
      var v = n[key];
      if (Array.isArray(v)) return v[Math.min(side, v.length - 1)];
      return v;
    }
    function update() {
      items.forEach(function (li, i) {
        var n = spec.nodes[i];
        var st = val(n, "status");
        li.className = "fl-node" + (st ? " st-" + st : "") + (i === selected ? " on" : "");
        var color = statuses[st] ? colorOf(statuses[st].color) : "var(--rule)";
        li.style.setProperty("--fl", color);
        var v = li.querySelector(".fl-val");
        if (v && n.values) v.textContent = val(n, "values");
        var b = li.querySelector(".fl-btn");
        b.setAttribute("aria-pressed", i === selected ? "true" : "false");
        if (statuses[st]) b.setAttribute("aria-label", (n.label || "") + ", " + statuses[st].label + (n.values ? ", " + val(n, "values") : ""));
      });
      if (detail) {
        while (detail.firstChild) detail.removeChild(detail.firstChild);
        if (selected >= 0) {
          var n = spec.nodes[selected];
          var st = val(n, "status");
          html("p", "fl-detail-k", (selected + 1) + " · " + (statuses[st] ? statuses[st].label : ""), detail);
          html("h4", "fl-detail-h", n.label || "", detail);
          var src = items[selected].querySelector(".fl-text");
          if (src) Array.prototype.forEach.call(src.childNodes, function (c) { detail.appendChild(c.cloneNode(true)); });
        }
      }
    }
    items.forEach(function (li, i) {
      li.querySelector(".fl-btn").addEventListener("click", function () { selected = selected === i ? -1 : i; update(); });
    });
    if (seg) {
      seg.hidden = false;
      var buttons = Array.prototype.slice.call(seg.querySelectorAll("button"));
      buttons.forEach(function (b) {
        b.addEventListener("click", function () {
          side = Number(b.getAttribute("data-side"));
          buttons.forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
          update();
        });
      });
    }
    var legend = node.querySelector(".fl-legend");
    if (legend) {
      var used = {};
      spec.nodes.forEach(function (n) { (Array.isArray(n.status) ? n.status : [n.status]).forEach(function (s) { if (s) used[s] = true; }); });
      legend.className = "fl-legend legend";
      Object.keys(statuses).forEach(function (k) {
        if (!used[k]) return;
        var li = html("span", "tm-key", null, legend);
        html("i", null, null, li).style.background = colorOf(statuses[k].color);
        li.appendChild(doc.createTextNode(statuses[k].label));
      });
    }
    if (spec.token && !reduceMotion) {
      var trackEl = node.querySelector(".fl-track");
      var token = html("span", "fl-token", null, trackEl);
      token.setAttribute("aria-hidden", "true");
      var ts = svg("svg", { width: 26, height: 22, viewBox: "-13 -11 26 22" }, token);
      drawIcon(ts, spec.token, 0, 0, 1);
      var t0 = null;
      plates.push(function (vh, now) {
        var r = trackEl.getBoundingClientRect();
        if (r.bottom < 0 || r.top > vh) return;
        if (t0 === null) t0 = now;
        var buttons2 = items.map(function (li) { return li.querySelector(".fl-btn"); });
        var per = 1300, n = buttons2.length;
        var tt = ((now - t0) / per) % (n + 0.6);
        var a = Math.min(Math.floor(tt), n - 1), f = clamp(tt - a, 0, 1);
        var b = Math.min(a + 1, n - 1);
        var ra = buttons2[a].getBoundingClientRect(), rb = buttons2[b].getBoundingClientRect();
        var ease2 = f < 0.55 ? 0 : ease((f - 0.55) / 0.45);
        var x = ra.left + ra.width / 2 + (rb.left - ra.left + (rb.width - ra.width) / 2) * ease2 - r.left;
        var y = ra.top - r.top + (rb.top - ra.top) * ease2 - 14;
        token.style.transform = "translate(" + (x - 13).toFixed(1) + "px," + y.toFixed(1) + "px)";
        token.style.opacity = tt > n - 0.2 ? "0" : "1";
      });
    }
    update();
  }

  /* -------------------------------------------------------------- diagram */
  /* Claude's sanitized SVG. Parts with data-tip explain themselves on hover or focus;
     steps dim every part but the ones a step is about. */
  function initDiagram(node, spec) {
    var root = node.querySelector(".dg-svg");
    if (!root) return;
    Array.prototype.forEach.call(root.querySelectorAll("[data-tip]"), function (el) {
      function build(t) { html("div", null, el.getAttribute("data-tip"), t); }
      el.addEventListener("pointerenter", function (ev) { var xy = pointerXY(ev); showTip(build, xy[0], xy[1]); });
      el.addEventListener("pointerleave", hideTip);
      el.addEventListener("focus", function () { var r = el.getBoundingClientRect(); showTip(build, r.left + r.width / 2, r.bottom); });
      el.addEventListener("blur", hideTip);
    });
    var steps = spec.steps || [];
    var items = Array.prototype.slice.call(node.querySelectorAll(".st"));
    var controls = node.querySelector(".st-controls");
    if (!steps.length || !controls) return;
    var units = Array.prototype.filter.call(root.querySelectorAll("[id]"), function (el) {
      var up = el.parentNode;
      while (up && up !== root) { if (up.getAttribute && up.getAttribute("id")) return false; up = up.parentNode; }
      return el.tagName.toLowerCase() !== "marker" && !(el.closest && el.closest("defs"));
    });
    var prev = node.querySelector(".st-prev"), next = node.querySelector(".st-next"), count = node.querySelector(".st-count");
    var at = 0;
    controls.hidden = false;
    function go(i) {
      at = clamp(i, 0, items.length - 1);
      items.forEach(function (it, k) { it.classList.toggle("on", k === at); });
      prev.disabled = at === 0; next.disabled = at === items.length - 1;
      count.textContent = "Step " + (at + 1) + " of " + items.length;
      var focus = (steps[at] && steps[at].focus) || [];
      var targets = focus.map(function (id) { return doc.getElementById(id); }).filter(Boolean);
      units.forEach(function (u) {
        var hit = !targets.length || targets.some(function (t) { return t === u || u.contains(t) || t.contains(u); });
        u.classList.toggle("dg-dim", !hit);
        u.classList.toggle("dg-on", hit && targets.length > 0);
      });
    }
    prev.addEventListener("click", function () { go(at - 1); });
    next.addEventListener("click", function () { go(at + 1); });
    go(0);
  }
