  /* -------------------------------------------------------------- figures */
  var scrollers = [];
  var plates = [];

  function initStats(node, spec) {
    var sparks = spec.sparks || {};
    Object.keys(sparks).forEach(function (k) {
      var stat = node.querySelector('.stat[data-i="' + k + '"] .spark');
      var vals = (sparks[k] || []).filter(function (v) { return v !== null; });
      if (!stat || vals.length < 2) return;
      function draw() {
        while (stat.firstChild) stat.removeChild(stat.firstChild);
        var w = stat.clientWidth || 160, h = 30;
        stat.setAttribute("viewBox", "0 0 " + w + " " + h);
        var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
        var y = linear(lo, hi, h - 4, 4);
        var pts = vals.map(function (v, i) { return [2 + i / (vals.length - 1) * (w - 8), y(v)]; });
        var p = svg("path", { d: pathFrom(pts), fill: "none", "stroke-width": 1.6, "stroke-linejoin": "round" }, stat);
        p.style.stroke = "var(--muted)";
        var e = pts[pts.length - 1];
        svg("circle", { cx: e[0], cy: e[1], r: 3.2, "stroke-width": 1.5 }, stat).style.cssText = "fill:var(--accent);stroke:var(--paper)";
      }
      draw();
      if (window.ResizeObserver) new ResizeObserver(draw).observe(stat);
    });
  }

  function initScrolly(node, spec) {
    var mount = node.querySelector(".mount");
    var ctl = mountChart(node, spec.chart, mount, {});
    var steps = Array.prototype.slice.call(node.querySelectorAll(".step"));
    var active = -1;
    scrollers.push(function (vh) {
      var idx = -1;
      steps.forEach(function (s, i) { if (s.getBoundingClientRect().top < vh * 0.62) idx = i; });
      if (idx === active) return;
      active = idx;
      steps.forEach(function (s, i) { s.classList.toggle("on", i === idx); });
      if (ctl) ctl.update({ focus: idx >= 0 ? (spec.steps[idx].focus || null) : null });
    });
  }

  function initTimeline(node, spec) {
    var mount = node.querySelector(".mount");
    var list = Array.prototype.slice.call(node.querySelectorAll(".ev"));
    var events = spec.events || [];
    var eras = spec.eras || [];
    var selected = 0;
    var todayStr = spec.today;
    events.forEach(function (ev, i) { if (!todayStr || ev.date <= todayStr) selected = i; });
    function select(i) {
      selected = i;
      list.forEach(function (li, k) { li.classList.toggle("on", k === i); });
      draw();
    }
    function draw() {
      while (mount.firstChild) mount.removeChild(mount.firstChild);
      var width = Math.max(280, mount.clientWidth || 600), narrow = width < 600;
      var height = narrow ? 120 : 150;
      var s = svg("svg", { width: width, height: height, viewBox: "0 0 " + width + " " + height }, mount);
      var dates = events.map(function (e) { return parseDate(e.date); });
      eras.forEach(function (e) { dates.push(parseDate(e.from)); dates.push(parseDate(e.to)); });
      var t0 = Math.min.apply(null, dates), t1 = Math.max.apply(null, dates);
      var x = linear(t0, t1, 10, width - 10);
      var trackY = narrow ? 70 : 88;
      eras.forEach(function (e, k) {
        var a = x(parseDate(e.from)), b = x(parseDate(e.to));
        svg("rect", { x: a, y: 18, width: Math.max(1, b - a - 2), height: trackY - 8, "class": "tl-era" + (k % 2 ? " alt" : "") }, s);
        if (e.label.length * 7 + 12 < b - a) txt(s, a + 6, 32, e.label, { "class": "tl-era-label" });
      });
      svg("line", { x1: 10, x2: width - 10, y1: trackY, y2: trackY, stroke: "var(--ink-2)", "stroke-width": 1.2 }, s);
      var year = new Date(t0).getUTCFullYear();
      var ax = svg("g", { "class": "axis" }, s);
      for (var yr = year; yr <= new Date(t1).getUTCFullYear(); yr++) {
        for (var mo = 0; mo < 12; mo += 3) {
          var td = Date.UTC(yr, mo, 1);
          if (td < t0 || td > t1) continue;
          var px = x(td);
          svg("line", { x1: px, x2: px, y1: trackY, y2: trackY + 5, stroke: "var(--ink-2)" }, ax);
          txt(ax, px, trackY + 19, mo === 0 ? String(yr) : MONTHS[mo], { "text-anchor": "middle" });
        }
      }
      if (todayStr) {
        var tx = x(parseDate(todayStr));
        svg("line", { x1: tx, x2: tx, y1: 14, y2: trackY + 6, "class": "tl-today" }, s);
        txt(s, tx + 4, 14, "Today", { "class": "tl-today-label" });
      }
      events.forEach(function (ev, i) {
        var g = svg("g", { "class": "tl-ev" + (i === selected ? " on" : ""), tabindex: 0, role: "button", "aria-label": ev.title }, s);
        var px = x(parseDate(ev.date));
        svg("circle", { cx: px, cy: trackY, r: 12, fill: "transparent" }, g);
        svg("circle", { cx: px, cy: trackY, r: i === selected ? 7 : 5.5, "class": "tl-dot " + (ev.kind || "milestone") }, g);
        if (i === selected) {
          var anchor = px > width * 0.75 ? "end" : (px < width * 0.2 ? "start" : "middle");
          txt(g, px, trackY - 14, ev.title, { "text-anchor": anchor });
        }
        g.addEventListener("click", function () { select(i); });
        g.addEventListener("keydown", function (e2) {
          if (e2.key === "Enter" || e2.key === " ") { e2.preventDefault(); select(i); }
          if (e2.key === "ArrowRight" || e2.key === "ArrowLeft") {
            e2.preventDefault();
            var ni = clamp(i + (e2.key === "ArrowRight" ? 1 : -1), 0, events.length - 1);
            select(ni);
            var nodes = mount.querySelectorAll(".tl-ev"); if (nodes[ni]) nodes[ni].focus();
          }
        });
        g.addEventListener("pointerenter", function (e3) {
          var xy = pointerXY(e3);
          showTip(function (t) { html("div", "tip-h", ev.title, t); html("div", null, fmtDate(parseDate(ev.date)), t); }, xy[0], xy[1]);
        });
        g.addEventListener("pointerleave", hideTip);
      });
    }
    select(selected);
    if (window.ResizeObserver) new ResizeObserver(function () { draw(); }).observe(mount);
  }

  function initStepper(node, spec) {
    var items = Array.prototype.slice.call(node.querySelectorAll(".st"));
    var controls = node.querySelector(".st-controls");
    var prev = node.querySelector(".st-prev"), next = node.querySelector(".st-next"), count = node.querySelector(".st-count");
    var ctl = spec.chart ? mountChart(node, spec.chart, node.querySelector(".mount"), {}) : null;
    var at = 0;
    controls.hidden = false;
    function go(i) {
      at = clamp(i, 0, items.length - 1);
      items.forEach(function (it, k) { it.classList.toggle("on", k === at); });
      prev.disabled = at === 0; next.disabled = at === items.length - 1;
      count.textContent = word("step", "Step") + " " + (at + 1) + " " + word("of", "of") + " " + items.length;
      if (ctl) ctl.update({ focus: spec.steps[at].focus || null });
    }
    prev.addEventListener("click", function () { go(at - 1); });
    next.addEventListener("click", function () { go(at + 1); });
    node.addEventListener("keydown", function (ev) {
      if (ev.target.closest && ev.target.closest(".mount")) return;
      if (ev.key === "ArrowRight") go(at + 1);
      if (ev.key === "ArrowLeft") go(at - 1);
    });
    go(0);
  }

  function initCompare(node) {
    var flips = Array.prototype.slice.call(node.querySelectorAll(".flip"));
    var seg = Array.prototype.slice.call(node.querySelectorAll(".seg button"));
    flips.forEach(function (b) { b.addEventListener("click", function () { b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") === "true" ? "false" : "true"); }); });
    seg.forEach(function (b) {
      b.addEventListener("click", function () {
        var side = b.getAttribute("data-side") === "1";
        seg.forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
        flips.forEach(function (f, k) { setTimeout(function () { f.setAttribute("aria-pressed", side ? "true" : "false"); }, reduceMotion ? 0 : k * 90); });
      });
    });
  }

  function initMatrix(node, spec) {
    var mount = node.querySelector(".mount");
    var rows = Array.prototype.slice.call(node.querySelectorAll(".risk"));
    var items = spec.items || [];
    var selected = -1;
    function select(i) {
      selected = selected === i ? -1 : i;
      rows.forEach(function (r, k) { r.classList.toggle("on", k === selected); r.querySelector(".risk-btn").setAttribute("aria-expanded", k === selected ? "true" : "false"); });
      draw();
    }
    rows.forEach(function (r, k) { r.querySelector(".risk-btn").addEventListener("click", function () { select(k); }); });
    function draw() {
      while (mount.firstChild) mount.removeChild(mount.firstChild);
      var width = Math.max(260, Math.min(mount.clientWidth || 400, 460));
      var pad = 34, size = width - pad - 6, cell = size / 5;
      var s = svg("svg", { width: width, height: size + pad + 6, viewBox: "0 0 " + width + " " + (size + pad + 6) }, mount);
      for (var li = 1; li <= 5; li++) for (var im = 1; im <= 5; im++) {
        var score = li * im;
        var r = svg("rect", { x: pad + (li - 1) * cell + 1, y: (5 - im) * cell + 1, width: cell - 2, height: cell - 2, "class": "mx-cell" }, s);
        if (score >= 12) { var hot = svg("rect", { x: pad + (li - 1) * cell + 1, y: (5 - im) * cell + 1, width: cell - 2, height: cell - 2, "class": "mx-hot" }, s); hot.style.opacity = String(0.06 + (score - 12) / 13 * 0.22); }
        r.setAttribute("rx", 2);
      }
      var ax = svg("g", { "class": "axis" }, s);
      txt(ax, pad, size + 22, "Likelihood →", {});
      var tl = txt(ax, 12, size, "Impact →", { transform: "rotate(-90 12 " + size + ")" });
      tl.setAttribute("x", 12);
      var buckets = {};
      items.forEach(function (it, i) {
        var key = it.likelihood + "-" + it.impact;
        var k = buckets[key] = (buckets[key] || 0) + 1;
        var cx = pad + (it.likelihood - 0.5) * cell + (k - 1) * 20 - 8;
        var cy = (5 - it.impact + 0.5) * cell;
        var g = svg("g", { "class": "mx-dot" + (i === selected ? " on" : ""), tabindex: 0, role: "button", "aria-label": String(it.id || i + 1) + ": " + (it.title || "") }, s);
        svg("circle", { cx: cx, cy: cy, r: 11 }, g);
        txt(g, cx, cy + 3.5, it.id || String(i + 1), {});
        g.addEventListener("click", function () { select(i); });
        g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); select(i); } });
        g.addEventListener("pointerenter", function (ev) { var xy = pointerXY(ev); showTip(function (t) { html("div", "tip-h", (it.id || "") + " " + (it.title || ""), t); html("div", null, "Likelihood " + it.likelihood + " of 5, impact " + it.impact + " of 5", t); }, xy[0], xy[1]); });
        g.addEventListener("pointerleave", hideTip);
      });
    }
    draw();
    if (window.ResizeObserver) new ResizeObserver(draw).observe(mount);
  }

  function initRoadmap(node, spec) {
    var mount = node.querySelector(".mount");
    var rows = Array.prototype.slice.call(node.querySelectorAll(".rm"));
    var items = spec.items || [];
    var lanes = spec.lanes || items.map(function (i) { return i.lane; }).filter(function (v, i, a) { return a.indexOf(v) === i; });
    var selected = 0;
    function select(i) { selected = i; rows.forEach(function (r, k) { r.classList.toggle("on", k === i); }); draw(); }
    function draw() {
      while (mount.firstChild) mount.removeChild(mount.firstChild);
      var width = Math.max(300, mount.clientWidth || 600);
      var narrow = width < 600;
      var labelW = narrow ? 0 : 108, rowH = narrow ? 34 : 30, lanePad = narrow ? 16 : 7, top = 26;
      var rowOf = [], laneRows = lanes.map(function () { return []; });
      items.map(function (it, i) { return i; }).sort(function (a, b) { return items[a].start < items[b].start ? -1 : 1; }).forEach(function (i) {
        var it = items[i], rows = laneRows[lanes.indexOf(it.lane)] || [];
        var r = 0;
        while (r < rows.length && rows[r] > it.start) r++;
        rows[r] = it.end;
        rowOf[i] = r;
      });
      var laneTop = [], acc = top;
      lanes.forEach(function (_, k) { laneTop.push(acc); acc += lanePad + Math.max(1, laneRows[k].length) * rowH + 4; });
      var height = acc + 8;
      var wrap = width;
      var s = svg("svg", { width: wrap, height: height, viewBox: "0 0 " + wrap + " " + height }, mount);
      var defs = svg("defs", null, s);
      var pat = svg("pattern", { id: "rm-hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, defs);
      svg("rect", { width: 6, height: 6, fill: "var(--accent-wash)" }, pat);
      svg("line", { x1: 0, y1: 0, x2: 0, y2: 6, "class": "rm-hatch-line" }, pat);
      var t0 = parseDate(spec.start || items[0].start), t1 = parseDate(spec.end || items[items.length - 1].end);
      var x = linear(t0.getTime(), t1.getTime(), labelW + 4, wrap - 8);
      var ax = svg("g", { "class": "axis" }, s);
      var cur = new Date(Date.UTC(t0.getUTCFullYear(), t0.getUTCMonth(), 1));
      while (cur <= t1) {
        var px = x(cur.getTime());
        var mo = cur.getUTCMonth();
        if (mo % 3 === 0) {
          svg("line", { x1: px, x2: px, y1: top - 6, y2: height - 4, stroke: "var(--grid)" }, ax);
          txt(ax, px + 3, top - 10, mo === 0 ? MONTHS[0] + " " + cur.getUTCFullYear() : MONTHS[mo], {});
        }
        cur = new Date(Date.UTC(cur.getUTCFullYear(), mo + 1, 1));
      }
      lanes.forEach(function (lane, k) {
        var ly = laneTop[k], lh = lanePad + Math.max(1, laneRows[k].length) * rowH;
        svg("rect", { x: labelW, y: ly + 2, width: wrap - labelW, height: lh, "class": "rm-lane" }, s).style.opacity = k % 2 ? 0.5 : 1;
        if (!narrow) txt(s, 0, ly + lh / 2 + 6, lane, { "class": "rm-lane-label" });
        else txt(s, labelW + 6, ly + 13, lane, { "class": "rm-lane-label" }).style.fontSize = "10px";
      });
      if (spec.today) {
        var tx = x(parseDate(spec.today).getTime());
        svg("line", { x1: tx, x2: tx, y1: top - 4, y2: height - 4, "class": "tl-today" }, s);
        txt(s, tx + 4, height - 8, "Today", { "class": "tl-today-label" });
      }
      items.forEach(function (it, i) {
        var lane = lanes.indexOf(it.lane);
        var a = x(parseDate(it.start).getTime()), b = x(parseDate(it.end).getTime());
        var ly = laneTop[lane] + lanePad + rowOf[i] * rowH;
        var bh = rowH - 8;
        var g = svg("g", { "class": "rm-bar " + (it.confidence || "committed") + (i === selected ? " on" : ""), tabindex: 0, role: "button", "aria-label": it.title }, s);
        svg("rect", { x: a, y: ly, width: Math.max(6, b - a), height: bh, rx: 2 }, g);
        var label = it.title, charW = narrow ? 5.6 : 6.6;
        var inside = (b - a) > label.length * charW + 14;
        var tlab = txt(g, inside ? a + 7 : b + 6, ly + bh / 2 + 4, label, { "class": inside ? "in" : "" });
        if (narrow) tlab.style.fontSize = "10.5px";
        if (!inside && b + 6 + label.length * charW > wrap) { tlab.setAttribute("x", a - 6); tlab.setAttribute("text-anchor", "end"); }
        if (!(inside && (it.confidence || "committed") === "committed") && tlab.getBBox) {
          // A chip under the label keeps it readable over hatching and grid lines.
          var bb = tlab.getBBox();
          g.insertBefore(svg("rect", { x: bb.x - 3, y: bb.y - 1, width: bb.width + 6, height: bb.height + 2, rx: 2, "class": "rm-chip" }), tlab);
        }
        g.addEventListener("click", function () { select(i); });
        g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); select(i); } });
      });
    }
    select(0);
    if (window.ResizeObserver) new ResizeObserver(draw).observe(mount);
  }

  function initTeam(node) {
    var squads = Array.prototype.slice.call(node.querySelectorAll(".squad"));
    squads.forEach(function (s) {
      s.setAttribute("tabindex", "0");
      s.addEventListener("click", function () { squads.forEach(function (o) { o.classList.toggle("on", o === s && !s.classList.contains("on")); }); });
    });
  }

  function initModel(node, spec) {
    var controls = node.querySelector(".controls");
    var mount = node.querySelector(".mount");
    var readout = node.querySelector(".readout");
    var d = spec.data || {};
    function slider(id, label, min, max, step, value, show, hint) {
      var wrap = html("div", "ctl", null, controls);
      var lab = html("label", null, null, wrap);
      lab.setAttribute("for", id);
      html("span", null, label, lab);
      var out = html("output", null, show(value), lab);
      out.setAttribute("for", id);
      var input = html("input", null, null, wrap);
      input.type = "range"; input.id = id; input.min = min; input.max = max; input.step = step; input.value = value;
      if (hint) html("p", "hint", hint, wrap);
      return { input: input, out: out, show: show };
    }
    function tiles(list) {
      var t = controls.querySelector(".tiles") || html("div", "tiles", null, controls);
      while (t.firstChild) t.removeChild(t.firstChild);
      list.forEach(function (it) { var tile = html("div", "tile", null, t); html("p", "t-label", it[0], tile); html("p", "t-value" + (it[2] ? " " + it[2] : ""), it[1], tile); });
    }
    function sentence(parts) {
      while (readout.firstChild) readout.removeChild(readout.firstChild);
      parts.forEach(function (p) { if (typeof p === "string") readout.appendChild(doc.createTextNode(p)); else html("b", null, p[0], readout); });
    }
    var uid = node.getAttribute("data-fig");
    if (spec.kind === "forecast") {
      var v0 = Number(d.velocity), g0 = Number(d.growth);
      var vs = slider(uid + "-v", "Points finished per sprint", Math.round(v0 * 0.5), Math.round(v0 * 1.6), 1, v0, function (v) { return String(v); }, "Recent average: " + v0);
      var gs = slider(uid + "-g", "Points added per sprint", 0, Math.max(60, g0 * 2), 1, g0, function (v) { return String(v); }, "Recent average: " + g0);
      var spec2 = { chart: "burnup", data: { x: d.x, scope: d.scope, done: d.done, velocity: v0, growth: g0 } };
      var ctl = mountChart(node, spec2, mount, { velocity: v0, growth: g0, target: d.target });
      var update = function () {
        var v = Number(vs.input.value), g = Number(gs.input.value);
        vs.out.textContent = vs.show(v); gs.out.textContent = gs.show(g);
        ctl.update({ velocity: v, growth: g });
        var fin = ctl.api && ctl.api.finish;
        var target = parseDate(d.target);
        if (!fin) {
          tiles([["Projected finish", "Never", "bad"], ["Net progress", (v - g) + " pts a sprint", "bad"]]);
          sentence(["At ", [v + " points a sprint"], " with ", [g + " added"], ", the backlog grows as fast as the team clears it, so the work never finishes."]);
          return;
        }
        var weeks = Math.round((fin.date - target) / (7 * 86400000));
        var late = weeks > 0;
        tiles([["Projected finish", fmtDate(fin.date), late ? "bad" : "good"], ["Against target", weeks === 0 ? "On target" : Math.abs(weeks) + (Math.abs(weeks) === 1 ? " week " : " weeks ") + (late ? "late" : "early"), late ? "bad" : "good"], ["Sprints left", String(fin.sprints), ""], ["Net progress", (v - g) + " pts a sprint", ""]]);
        sentence(["At ", [v + " points a sprint"], " with ", [g + " points added"], " each sprint, the remaining " + fmt(d.remaining, "int") + " points take ", [fin.sprints + " sprints"], ", landing about ", [fmtDate(fin.date)], late ? ", " + Math.abs(weeks) + " weeks after the " + fmtDate(target) + " target." : (weeks === 0 ? ", on the " + fmtDate(target) + " target." : ", " + Math.abs(weeks) + " weeks before the " + fmtDate(target) + " target.")]);
      };
      vs.input.addEventListener("input", update); gs.input.addEventListener("input", update);
      update();
    } else if (spec.kind === "savings") {
      var first = parseDate(d.first), last = parseDate(d.last), plan = parseDate(d.plan_month), renewal = parseDate(d.renewal_month);
      var span = monthsBetween(first, last);
      var planIdx = monthsBetween(first, plan);
      var L = d.labels || {};
      var oldName = L.old || "the old system", newName = L.new || "New system";
      var ms = slider(uid + "-m", "Switch " + oldName + " off at the end of", 0, span, 1, planIdx, function (i) { return fmtDate(new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + Number(i), 1)), "month"); }, "Plan: " + fmtDate(plan, "month"));
      var year = Number(d.year) || first.getUTCFullYear();
      var costFor = function (offIdx) {
        var off = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + offIdx, 1));
        var months = [], total = 0;
        for (var mo = 0; mo < 12; mo++) {
          var dt = new Date(Date.UTC(year, mo, 1));
          var running = dt <= off;
          var c = running ? Number(d.now) : Number(d.after);
          var renew = running && dt.getTime() === renewal.getTime() && off > renewal ? Number(d.renewal) : 0;
          if (off > renewal && dt.getTime() === renewal.getTime()) renew = Number(d.renewal);
          months.push({ date: dt, base: c, renew: renew });
          total += c + renew;
        }
        return { months: months, total: total, off: off };
      };
      var planCost = costFor(planIdx);
      var updateS = function () {
        var idx = Number(ms.input.value);
        ms.out.textContent = ms.show(idx);
        var r = costFor(idx);
        var delta = r.total - planCost.total;
        var renewed = r.off > renewal;
        tiles([[year + " run cost", compactMoney(r.total), ""], ["Against plan", (delta === 0 ? "On plan" : (delta > 0 ? "+" : "−") + compactMoney(Math.abs(delta)).replace(/^−/, "")), delta > 0 ? "bad" : (delta < 0 ? "good" : "")], [L.renewal || "License renewal", renewed ? compactMoney(Number(d.renewal)) : "Avoided", renewed ? "bad" : "good"], ["Saving once off", compactMoney(Number(d.now) - Number(d.after)) + "/mo", "good"]]);
        sentence(["Switching " + oldName + " off at the end of ", [fmtDate(r.off, "month")], " puts " + year + " run cost at ", [compactMoney(r.total)], delta === 0 ? ", the plan." : (delta > 0 ? ", " + compactMoney(delta) + " more than plan" : ", " + compactMoney(-delta) + " less than plan"), renewed ? ", including the " + compactMoney(Number(d.renewal)) + " " + (L.renewal || "license renewal").toLowerCase() + "." : (delta === 0 ? "" : ".")]);
        drawSavings(r);
      };
      var drawSavings = function (r) {
        while (mount.firstChild) mount.removeChild(mount.firstChild);
        var f = frame(mount, { right: 8, height: 260, left: 46 });
        var maxV = niceMax(Math.max.apply(null, r.months.map(function (m) { return m.base + m.renew; })));
        var y = linear(0, maxV, f.height - f.m.bottom, f.m.top);
        yAxis(f, y, ticks(0, maxV, 3), "money", "", true);
        var slot = f.iw / 12, bw = Math.min(24, slot - 6);
        r.months.forEach(function (m, i) {
          var x = f.m.left + slot * i + slot / 2 - bw / 2;
          var running = m.date <= r.off;
          var p = svg("path", { d: barPath(x, y(0), bw, y(m.base), 4) }, f.svg);
          p.style.fill = running ? "var(--legacy)" : "var(--s1)";
          if (m.renew) {
            var p2 = svg("path", { d: barPath(x, y(m.base) - 2, bw, y(m.base + m.renew), 4) }, f.svg);
            p2.style.fill = "var(--bad)";
            txt(f.svg, x + bw / 2, y(m.base + m.renew) - 6, "Renewal", { "text-anchor": "middle", "class": "note-text" });
          }
          txt(f.svg, x + bw / 2, f.height - 8, MONTHS[m.date.getUTCMonth()].slice(0, f.narrow ? 1 : 3), { "text-anchor": "middle", "class": "axis" }).style.fill = "var(--muted)";
        });
        legend(mount, [{ name: L.both || "Both running", color: "var(--legacy)" }, { name: newName + " only", color: "var(--s1)" }, { name: L.renewal || "License renewal", color: "var(--bad)" }], "bar");
      };
      ms.input.addEventListener("input", updateS);
      updateS();
    }
  }

