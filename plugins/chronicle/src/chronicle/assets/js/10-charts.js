  /* --------------------------------------------------------- line and area */
  function drawLine(mount, spec, state) {
    var data = spec.data, xs = data.x, series = data.series;
    var format = (spec.format && spec.format.y) || "auto";
    var stacked = spec.chart === "stacked";
    var area = spec.chart === "area";
    var n = xs.length;
    var narrow = (mount.clientWidth || 600) < 560;
    var labelRoom = stacked ? 8 : (narrow ? 64 : 120);
    var f = frame(mount, { right: labelRoom, top: spec.notes && spec.notes.length ? 46 : 26, left: stacked ? 40 : 8 });
    var tops = [];
    if (stacked) {
      var acc = new Array(n).fill(0);
      series.forEach(function (s) {
        var lower = acc.slice();
        acc = acc.map(function (v, i) { return v + (Number(s.values[i]) || 0); });
        tops.push({ lower: lower, upper: acc.slice() });
      });
    }
    var maxV = stacked ? (spec.normalize ? 100 : Math.max.apply(null, tops[tops.length - 1].upper)) : Math.max.apply(null, series.map(function (s) { return Math.max.apply(null, s.values.filter(function (v) { return v !== null; })); }));
    var minV = spec.y_min !== undefined ? spec.y_min : 0;
    var top = spec.y_max !== undefined ? spec.y_max : (stacked && spec.normalize ? 100 : niceMax(maxV));
    var y = linear(minV, top, f.height - f.m.bottom, f.m.top);
    var xpos = function (i) { return f.m.left + (n === 1 ? f.iw / 2 : i / (n - 1) * f.iw); };
    yAxis(f, y, ticks(minV, top, f.narrow ? 3 : 4), format, spec.unit, stacked);
    var range = indexRange(xs, state.focus);
    if (range) {
      var x0 = xpos(range[0]) - (range[0] === range[1] ? 6 : 0), x1 = xpos(range[1]) + (range[0] === range[1] ? 6 : 0);
      svg("rect", { "class": "focus-band", x: x0, y: f.m.top - 6, width: Math.max(2, x1 - x0), height: f.ih + 6 }, f.svg);
    }
    var layer = svg("g", null, f.svg);
    if (stacked) {
      series.forEach(function (s, si) {
        var t = tops[si];
        var d = "";
        for (var i = 0; i < n; i++) d += (i ? "L" : "M") + xpos(i).toFixed(1) + "," + y(t.upper[i]).toFixed(1);
        for (var j = n - 1; j >= 0; j--) d += "L" + xpos(j).toFixed(1) + "," + y(t.lower[j]).toFixed(1);
        var p = svg("path", { d: d + "Z" }, layer);
        p.style.fill = seriesColor(si, s);
        p.style.opacity = si === 0 ? 0.85 : 0.32;
        if (si > 0) {
          var edge = svg("path", { d: pathFrom(t.lower.map(function (v, i) { return [xpos(i), y(v)]; })), fill: "none", "stroke-width": 2 }, layer);
          edge.style.stroke = "var(--paper)";
        }
      });
      series.forEach(function (s, si) {
        var t = tops[si];
        var mid = (t.upper[n - 1] + t.lower[n - 1]) / 2;
        var band = y(t.lower[n - 1]) - y(t.upper[n - 1]);
        if (band < 28) return;
        var lx = xpos(n - 1) - 8;
        var a = txt(layer, lx, y(mid) - 2, s.name, { "text-anchor": "end", "class": "label-strong" });
        a.style.fill = si === 0 ? "#FFFFFF" : "var(--ink)";
        var b = txt(layer, lx, y(mid) + 14, fmt(s.values[n - 1], format), { "text-anchor": "end" });
        b.style.fill = si === 0 ? "#FFFFFF" : "var(--ink)";
      });
      if (range) {
        var t0 = tops[0];
        var seg = [];
        for (var k = range[0]; k <= range[1]; k++) seg.push([xpos(k), y(t0.upper[k])]);
        var hl = svg("path", { d: pathFrom(seg), fill: "none", "stroke-width": 3, "stroke-linecap": "round" }, layer);
        hl.style.stroke = "var(--ink)";
        var endI = range[1];
        svg("circle", { cx: xpos(endI), cy: y(t0.upper[endI]), r: 4.5, "stroke-width": 2 }, layer).style.cssText = "fill:var(--ink);stroke:var(--paper)";
        if (endI < n - 1) {
          var lab = txt(layer, xpos(endI), y(t0.upper[endI]) - 10, fmt(series[0].values[endI], format), { "text-anchor": endI > n * 0.8 ? "end" : "middle", "class": "label-strong" });
          lab.style.fontSize = "13px";
        }
      }
      legend(mount, series.map(function (s, si) { return { name: s.name, color: s.color, opacity: si === 0 ? 0.85 : 0.32 }; }), "area");
    } else {
      series.forEach(function (s, si) {
        var pts = s.values.map(function (v, i) { return [xpos(i), v === null ? null : y(v)]; });
        if (area || series.length === 1) {
          var d = pathFrom(pts);
          if (d) {
            var first = pts.findIndex(function (p) { return p[1] !== null; });
            var lastI = pts.length - 1;
            var ad = d + "L" + xpos(lastI).toFixed(1) + "," + y(minV).toFixed(1) + "L" + xpos(first).toFixed(1) + "," + y(minV).toFixed(1) + "Z";
            var ap = svg("path", { d: ad }, layer);
            ap.style.fill = seriesColor(si, s); ap.style.opacity = 0.1;
          }
        }
        var line = svg("path", { d: pathFrom(pts), fill: "none", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round", "class": range ? "dimmed" : "" }, layer);
        line.style.stroke = seriesColor(si, s);
        if (range) {
          var seg2 = pts.slice(range[0], range[1] + 1);
          var hl2 = svg("path", { d: pathFrom(seg2), fill: "none", "stroke-width": 3, "stroke-linecap": "round" }, layer);
          hl2.style.stroke = seriesColor(si, s);
          var peak = range[0];
          for (var q = range[0]; q <= range[1]; q++) if ((s.values[q] || 0) > (s.values[peak] || 0)) peak = q;
          var showI = state.focus && state.focus.at === "end" ? range[1] : peak;
          if (s.values[showI] !== null) {
            svg("circle", { cx: xpos(showI), cy: y(s.values[showI]), r: 4.5, "stroke-width": 2 }, layer).style.cssText = "fill:" + seriesColor(si, s) + ";stroke:var(--paper)";
            txt(layer, xpos(showI), y(s.values[showI]) - 11, fmt(s.values[showI], format), { "text-anchor": showI > n * 0.85 ? "end" : (showI < n * 0.1 ? "start" : "middle"), "class": "label-strong" });
          }
        }
        var lastIdx = s.values.length - 1;
        while (lastIdx > 0 && s.values[lastIdx] === null) lastIdx--;
        var ly = y(s.values[lastIdx]);
        var dot = svg("circle", { cx: xpos(lastIdx), cy: ly, r: 4, "stroke-width": 2 }, layer);
        dot.style.cssText = "fill:" + seriesColor(si, s) + ";stroke:var(--paper)";
        if (!range) {
          var tx = xpos(lastIdx) + 8;
          txt(layer, tx, ly + 4, fmt(s.values[lastIdx], format) + (spec.unit && !f.narrow ? " " + spec.unit : ""), { "class": "label-strong" });
          if (!f.narrow && series.length > 1) txt(layer, tx, ly + 19, s.name);
        }
      });
      if (series.length > 1) legend(mount, series, "line");
    }
    var noteEnds = [];
    (spec.notes || []).forEach(function (note, k) {
      var i = xs.indexOf(note.x);
      if (i < 0) return;
      var px = xpos(i);
      var v = series[0].values[i];
      var py = y(stacked ? tops[0].upper[i] : v);
      var half = String(note.text).length * 3.3 + 8;
      var row = 0;
      while (noteEnds[row] !== undefined && noteEnds[row] > px - half) row++;
      noteEnds[row] = px + half;
      var ty = 14 + row * 15;
      svg("line", { "class": "note-line", x1: px, x2: px, y1: ty + 6, y2: py - 7 }, f.svg);
      var anchor = px > f.width * 0.7 ? "end" : (px < f.width * 0.15 ? "start" : "middle");
      txt(f.svg, px, ty, note.text, { "class": "note-text", "text-anchor": anchor });
    });
    xAxis(f, xs, xpos);
    hoverLayer(f, n, xpos, function (i, cx, cy) {
      showTip(function (t) {
        html("div", "tip-h", labelX(xs[i]), t);
        series.forEach(function (s, si) { tipRow(t, seriesColor(si, s), fmt(s.values[i], format), s.name); });
      }, cx, cy);
    });
    return {
      table: function () {
        return { cols: ["", ].concat(series.map(function (s) { return s.name; })), rows: xs.map(function (x, i) { return [labelX(x)].concat(series.map(function (s) { return fmt(s.values[i], format); })); }) };
      }
    };
  }

  /* ---------------------------------------------------------------- bars */
  function barPath(x, y0, w, y1, r) {
    var top = Math.min(y0, y1), h = Math.abs(y1 - y0);
    var rr = Math.min(r, w / 2, h);
    return "M" + x + "," + (top + h) + "V" + (top + rr) + "Q" + x + "," + top + " " + (x + rr) + "," + top + "H" + (x + w - rr) + "Q" + (x + w) + "," + top + " " + (x + w) + "," + (top + rr) + "V" + (top + h) + "Z";
  }
  function drawBars(mount, spec) {
    var data = spec.data, cats = data.categories, series = data.series;
    var format = (spec.format && spec.format.y) || "auto";
    var stacked = !!spec.stacked;
    var f = frame(mount, { right: 8, left: 46 });
    var n = cats.length;
    var totals = cats.map(function (_, i) { return series.reduce(function (a, s) { return a + (Number(s.values[i]) || 0); }, 0); });
    var maxV = stacked ? Math.max.apply(null, totals) : Math.max.apply(null, series.map(function (s) { return Math.max.apply(null, s.values); }));
    var top = niceMax(maxV);
    var y = linear(0, top, f.height - f.m.bottom, f.m.top);
    yAxis(f, y, ticks(0, top, f.narrow ? 3 : 4), format, "", true);
    var slot = f.iw / n;
    var groupW = stacked ? Math.min(24, slot - 4) : Math.min(24 * series.length + 2 * (series.length - 1), slot - 4);
    var barW = stacked ? groupW : (groupW - 2 * (series.length - 1)) / series.length;
    var xpos = function (i) { return f.m.left + slot * i + slot / 2; };
    var layer = svg("g", null, f.svg);
    cats.forEach(function (c, i) {
      var base = 0;
      series.forEach(function (s, si) {
        var v = Number(s.values[i]) || 0;
        if (!v) return;
        var x = stacked ? xpos(i) - barW / 2 : xpos(i) - groupW / 2 + si * (barW + 2);
        var y0 = stacked ? y(base) : y(0);
        var y1 = stacked ? y(base + v) : y(v);
        var isTop = !stacked || si === series.length - 1 || series.slice(si + 1).every(function (o) { return !(Number(o.values[i]) || 0); });
        var gap = stacked && base > 0 ? 2 : 0;
        var d = isTop ? barPath(x, y0 - gap, barW, y1, 4) : "M" + x + "," + (y0 - gap) + "V" + y1 + "H" + (x + barW) + "V" + (y0 - gap) + "Z";
        var p = svg("path", { d: d, tabindex: -1 }, layer);
        p.style.fill = seriesColor(si, s);
        p.addEventListener("pointermove", function (ev) {
          var xy = pointerXY(ev);
          p.style.opacity = 0.8;
          showTip(function (t) {
            html("div", "tip-h", labelX(c), t);
            series.forEach(function (o, oi) { tipRow(t, seriesColor(oi, o), fmt(o.values[i], format), o.name); });
            if (stacked) tipRow(t, null, fmt(totals[i], format), "total");
          }, xy[0], xy[1]);
        });
        p.addEventListener("pointerleave", function () { p.style.opacity = 1; hideTip(); });
        base += v;
      });
    });
    var lastI = n - 1;
    txt(layer, xpos(lastI), y(stacked ? totals[lastI] : series[0].values[lastI]) - 8, fmt(stacked ? totals[lastI] : series[0].values[lastI], format), { "text-anchor": "end", "class": "label-strong" });
    xAxis(f, cats, xpos);
    if (series.length > 1) legend(mount, series, "bar");
    return {
      table: function () {
        var cols = [""].concat(series.map(function (s) { return s.name; }));
        if (stacked) cols.push("Total");
        return { cols: cols, rows: cats.map(function (c, i) { var r = [labelX(c)].concat(series.map(function (s) { return fmt(s.values[i], format); })); if (stacked) r.push(fmt(totals[i], format)); return r; }) };
      }
    };
  }

  /* -------------------------------------------------------------- burnup */
  function project(done, scope, velocity, growth, maxSprints) {
    var d = done, s = scope, out = [];
    for (var k = 1; k <= maxSprints; k++) {
      d += velocity; s += growth;
      out.push([d, s]);
      if (d >= s) break;
    }
    return out;
  }
  function drawBurnup(mount, spec, state) {
    var data = spec.data;
    var xs = data.x, scope = data.scope, done = data.done;
    var v = state.velocity !== undefined ? state.velocity : Number(data.velocity);
    var g = state.growth !== undefined ? state.growth : Number(data.growth);
    var n = xs.length;
    var horizon = 30;
    var mid = project(done[n - 1], scope[n - 1], v, g, horizon);
    var fast = project(done[n - 1], scope[n - 1], v * 1.15, g, horizon);
    var slow = project(done[n - 1], scope[n - 1], v * 0.85, g, horizon);
    var extra = Math.min(horizon, Math.max(mid.length, Math.min(slow.length, mid.length + 6)) + 1);
    var total = n + extra;
    var f = frame(mount, { right: f2narrow(mount) ? 10 : 132, height: spec.height });
    var maxV = Math.max(scope[n - 1] + g * extra, done[n - 1] + v * extra * 0.5);
    var top = niceMax(Math.max.apply(null, scope.concat([maxV])));
    var y = linear(0, top, f.height - f.m.bottom, f.m.top);
    var xpos = function (i) { return f.m.left + i / (total - 1) * f.iw; };
    yAxis(f, y, ticks(0, top, f.narrow ? 3 : 4), "int", "pts");
    var layer = svg("g", null, f.svg);
    var last = n - 1;
    var start = parseDate(xs[last]);
    var dateAt = function (i) { return i <= last ? parseDate(xs[i]) : addDays(start, 14 * (i - last)); };
    if (state.target) {
      var tgt = parseDate(state.target);
      var ti = last + (tgt - start) / (14 * 86400000);
      if (ti > 0 && ti < total) {
        var tx = xpos(ti);
        svg("line", { x1: tx, x2: tx, y1: f.m.top - 4, y2: f.height - f.m.bottom, "stroke-dasharray": "4 3", "class": "note-line" }, layer);
        if (!f.narrow) txt(layer, tx - 4, f.m.top + 6, "Target", { "text-anchor": "end", "class": "note-text sub" });
      }
    }
    var cone = "M" + xpos(last) + "," + y(done[last]);
    fast.forEach(function (p, k) { cone += "L" + xpos(last + k + 1) + "," + y(Math.min(p[0], top)); });
    for (var k2 = slow.length - 1; k2 >= 0; k2--) cone += "L" + xpos(last + k2 + 1) + "," + y(slow[k2][0]);
    var cp = svg("path", { d: cone + "Z" }, layer);
    cp.style.fill = "var(--s1)"; cp.style.opacity = 0.12;
    var donePts = done.map(function (d, i) { return [xpos(i), y(d)]; });
    var area = pathFrom(donePts) + "L" + xpos(last) + "," + y(0) + "L" + xpos(0) + "," + y(0) + "Z";
    var ap = svg("path", { d: area }, layer); ap.style.fill = "var(--s1)"; ap.style.opacity = 0.1;
    var sl = svg("path", { d: pathFrom(scope.map(function (s, i) { return [xpos(i), y(s)]; })), fill: "none", "stroke-width": 2 }, layer);
    sl.style.stroke = "var(--ink-2)";
    var dl = svg("path", { d: pathFrom(donePts), fill: "none", "stroke-width": 2.2 }, layer);
    dl.style.stroke = "var(--s1)";
    var projS = [[xpos(last), y(scope[last])]].concat(mid.map(function (p, k) { return [xpos(last + k + 1), y(p[1])]; }));
    var projD = [[xpos(last), y(done[last])]].concat(mid.map(function (p, k) { return [xpos(last + k + 1), y(p[0])]; }));
    var ps = svg("path", { d: pathFrom(projS), fill: "none", "stroke-width": 1.6, "stroke-dasharray": "5 4" }, layer); ps.style.stroke = "var(--ink-2)";
    var pd = svg("path", { d: pathFrom(projD), fill: "none", "stroke-width": 1.8, "stroke-dasharray": "5 4" }, layer); pd.style.stroke = "var(--s1)";
    var finishes = mid.length && mid[mid.length - 1][0] >= mid[mid.length - 1][1];
    var narrow = f.narrow;
    var labX = xpos(last) + 6;
    txt(layer, xpos(last) - 6, y(scope[last]) + (f.narrow ? 18 : -9), "Scope " + fmt(scope[last], "int"), { "text-anchor": "end", "class": "label-strong" });
    txt(layer, xpos(last) - 8, y(done[last]) + 40, "Done " + fmt(done[last], "int"), { "text-anchor": "end", "class": "label-strong" });
    svg("circle", { cx: xpos(last), cy: y(done[last]), r: 4, "stroke-width": 2 }, layer).style.cssText = "fill:var(--s1);stroke:var(--paper)";
    var finishInfo = null;
    if (finishes) {
      var fi = last + mid.length;
      var fd = dateAt(fi);
      var fx = xpos(fi), fy = y(mid[mid.length - 1][1]);
      svg("circle", { cx: fx, cy: fy, r: 5.5, "stroke-width": 2 }, layer).style.cssText = "fill:var(--ink);stroke:var(--paper)";
      if (narrow) {
        txt(layer, fx, fy - 12, "Finish " + fmtDate(fd), { "text-anchor": "end", "class": "label-strong" });
      } else {
        txt(layer, fx + 10, fy - 6, "Projected finish", { "class": "note-text sub" });
        txt(layer, fx + 10, fy + 10, fmtDate(fd), { "class": "label-strong" });
      }
      finishInfo = { date: fd, sprints: mid.length };
    } else {
      txt(layer, labX, y(done[last]) - 30, "No finish at this pace", { "class": "label-strong" });
    }
    var dates = []; for (var i = 0; i < total; i++) dates.push(isoDay(dateAt(i)).slice(0, 7));
    xAxis(f, dates, xpos);
    hoverLayer(f, total, xpos, function (i, cx, cy) {
      showTip(function (t) {
        var dd = dateAt(i);
        html("div", "tip-h", (i <= last ? "Sprint " + (i + 1) + ", ended " : "Projected, ") + fmtDate(dd), t);
        if (i <= last) {
          tipRow(t, "var(--s1)", fmt(done[i], "int"), "points done");
          tipRow(t, "var(--ink-2)", fmt(scope[i], "int"), "points in scope");
        } else if (mid[i - last - 1]) {
          tipRow(t, "var(--s1)", fmt(Math.min(mid[i - last - 1][0], mid[i - last - 1][1]), "int"), "done, projected");
          tipRow(t, "var(--ink-2)", fmt(mid[i - last - 1][1], "int"), "scope, projected");
        }
      }, cx, cy);
    });
    return {
      finish: finishInfo,
      table: function () { return { cols: ["Sprint end", "Done", "Scope"], rows: xs.map(function (x, i) { return [labelX(x), fmt(done[i], "int"), fmt(scope[i], "int")]; }) }; }
    };
  }
  function f2narrow(mount) { return (mount.clientWidth || 600) < 560; }

  /* ------------------------------------------------------------ calendar */
  function drawCalendar(mount, spec) {
    while (mount.firstChild) mount.removeChild(mount.firstChild);
    var vals = spec.data.values, start = parseDate(spec.data.start);
    var weeks = Math.ceil(vals.length / 7);
    var avail = Math.max(240, mount.clientWidth || 600) - 30;
    var gap = avail / weeks < 9 ? 1 : 2;
    var cell = clamp(Math.floor(avail / weeks) - gap, 3, 16);
    var step = cell + gap;
    var width = 30 + weeks * step, height = 22 + 7 * step + 30;
    var s = svg("svg", { width: width, height: height, viewBox: "0 0 " + width + " " + height }, mount);
    var max = Math.max.apply(null, vals);
    var bins = [0, 1, 3, 5, 8];
    function cls(v) { if (!v) return 0; for (var b = bins.length - 1; b >= 1; b--) if (v >= bins[b]) return b; return 1; }
    var g = svg("g", { "class": "axis" }, s);
    ["Mon", "Wed", "Fri"].forEach(function (d, k) { txt(g, 0, 22 + (k * 2) * step + cell - 1, d); });
    var lastMonth = -1, lastLabelX = -1e9;
    var unit = spec.unit || "";
    for (var i = 0; i < vals.length; i++) {
      var d = addDays(start, i);
      var w = Math.floor(i / 7), dow = (d.getUTCDay() + 6) % 7;
      var x = 30 + w * step, yy = 22 + dow * step;
      if (d.getUTCDate() <= 7 && d.getUTCMonth() !== lastMonth && dow === 0) {
        lastMonth = d.getUTCMonth();
        var mlabel = d.getUTCMonth() === 0 ? MONTHS[0] + " " + d.getUTCFullYear() : MONTHS[d.getUTCMonth()];
        if (x - lastLabelX > (d.getUTCMonth() === 0 ? 30 : 26)) { txt(g, x, 12, mlabel); lastLabelX = x + (mlabel.length > 3 ? 26 : 0); }
      }
      var r = svg("rect", { x: x, y: yy, width: cell, height: cell, rx: 2 }, s);
      r.style.fill = "var(--seq-" + cls(vals[i]) + ")";
      (function (date, v, rect) {
        rect.addEventListener("pointermove", function (ev) {
          var xy = pointerXY(ev);
          rect.style.stroke = "var(--ink)"; rect.style.strokeWidth = "1.5";
          showTip(function (t) { html("div", "tip-h", DAYS[date.getUTCDay()] + " " + fmtDate(date), t); tipRow(t, null, String(v), unit); }, xy[0], xy[1]);
        });
        rect.addEventListener("pointerleave", function () { rect.style.stroke = ""; hideTip(); });
      })(d, vals[i], r);
    }
    var ly = 22 + 7 * step + 18;
    var lx = Math.max(64, width - (bins.length * (cell + 3)) - 70);
    txt(g, lx - 6, ly + cell - 2, "Fewer", { "text-anchor": "end" });
    bins.forEach(function (b, k) { var rr = svg("rect", { x: lx + k * (cell + 3), y: ly, width: cell, height: cell, rx: 2 }, s); rr.style.fill = "var(--seq-" + k + ")"; });
    txt(g, lx + bins.length * (cell + 3) + 4, ly + cell - 2, "More (" + max + ")");
    var weeklyTotals = [];
    return {
      table: function () {
        var rows = [];
        for (var w2 = 0; w2 < weeks; w2++) {
          var sum = 0; for (var k = 0; k < 7; k++) sum += vals[w2 * 7 + k] || 0;
          rows.push(["Week of " + fmtDate(addDays(start, w2 * 7)), String(sum)]);
        }
        weeklyTotals = rows;
        return { cols: ["Week", unit || "Count"], rows: weeklyTotals };
      }
    };
  }

  /* -------------------------------------------------------- small multiples */
  function drawMultiples(mount, spec) {
    while (mount.firstChild) mount.removeChild(mount.firstChild);
    var items = spec.data.items, xs = spec.data.x;
    var format = (spec.format && spec.format.y) || "auto";
    var width = Math.max(260, mount.clientWidth || 600);
    var cols = width < 520 ? 1 : width < 900 ? 2 : items.length >= 4 ? 4 : items.length;
    var grid = html("div", null, null, mount);
    grid.style.display = "grid";
    grid.style.gridTemplateColumns = "repeat(" + cols + ", minmax(0, 1fr))";
    grid.style.gap = "1.4rem 1.6rem";
    var lo = spec.y_min !== undefined ? spec.y_min : Math.min.apply(null, items.map(function (it) { return Math.min.apply(null, it.values.filter(function (v) { return v !== null; })); }));
    var hi = spec.y_max !== undefined ? spec.y_max : Math.max.apply(null, items.map(function (it) { return Math.max.apply(null, it.values.filter(function (v) { return v !== null; })); }));
    items.forEach(function (it) {
      var cell = html("div", null, null, grid);
      var head = html("div", null, null, cell);
      head.style.cssText = "display:flex;justify-content:space-between;align-items:baseline;gap:.5rem;font:600 .86rem/1.3 var(--f-ui);margin-bottom:.2rem";
      html("span", null, it.name, head);
      var lastI = it.values.length - 1; while (lastI > 0 && it.values[lastI] === null) lastI--;
      var lv = html("span", null, fmt(it.values[lastI], format), head);
      lv.style.color = "var(--ink-2)"; lv.style.fontWeight = "500";
      var w = Math.floor((width - (cols - 1) * 26) / cols);
      var h = 120;
      var m = { l: 4, r: 6, t: 14, b: 20 };
      var s = svg("svg", { width: w, height: h, viewBox: "0 0 " + w + " " + h }, cell);
      var n = xs.length;
      var xpos = function (i) { return m.l + i / (n - 1) * (w - m.l - m.r); };
      var y = linear(lo, hi, h - m.b, m.t);
      var gg = svg("g", { "class": "grid" }, s);
      svg("line", { x1: m.l, x2: w - m.r, y1: y(lo), y2: y(lo), "class": "baseline" }, gg);
      svg("line", { x1: m.l, x2: w - m.r, y1: y(hi), y2: y(hi) }, gg);
      if (spec.target !== undefined) {
        var ty = y(Number(spec.target));
        var tl = svg("line", { x1: m.l, x2: w - m.r, y1: ty, y2: ty, "stroke-dasharray": "4 3", "stroke-width": 1.2 }, s);
        tl.style.stroke = "var(--bad)";
        txt(s, w - m.r, ty + 12, "Target " + fmt(spec.target, format), { "class": "note-text sub", "text-anchor": "end" }).style.fontSize = "10.5px";
      }
      var pts = it.values.map(function (v, i) { return [xpos(i), v === null ? null : y(clamp(v, lo, hi))]; });
      var firstI = pts.findIndex(function (p) { return p[1] !== null; });
      if (firstI >= 0) {
        var ad = pathFrom(pts) + "L" + xpos(lastI) + "," + y(lo) + "L" + xpos(firstI) + "," + y(lo) + "Z";
        var ap = svg("path", { d: ad }, s); ap.style.fill = "var(--s1)"; ap.style.opacity = 0.1;
      }
      var ln = svg("path", { d: pathFrom(pts), fill: "none", "stroke-width": 2, "stroke-linejoin": "round" }, s);
      ln.style.stroke = "var(--s1)";
      var minI = -1; it.values.forEach(function (v, i) { if (v !== null && (minI < 0 || v < it.values[minI])) minI = i; });
      if (minI >= 0 && it.values[minI] < Number(spec.target)) {
        var c = svg("circle", { cx: xpos(minI), cy: y(it.values[minI]), r: 3.5, "stroke-width": 2 }, s);
        c.style.cssText = "fill:var(--bad);stroke:var(--paper)";
        txt(s, xpos(minI) + 6, y(it.values[minI]) + 3, fmt(it.values[minI], format), { "class": "note-text" }).style.fontSize = "10.5px";
      }
      var ax = svg("g", { "class": "axis" }, s);
      if (firstI >= 0) txt(ax, xpos(firstI), h - 5, tickX(xs[firstI], true), { "text-anchor": firstI > n * 0.6 ? "end" : "start" }).style.fontSize = "10.5px";
      txt(ax, xpos(n - 1), h - 5, tickX(xs[n - 1], true), { "text-anchor": "end" }).style.fontSize = "10.5px";
      var cross = svg("line", { "class": "crosshair", y1: m.t, y2: h - m.b, visibility: "hidden" }, s);
      var hit = svg("rect", { x: m.l, y: 0, width: w - m.l - m.r, height: h, fill: "transparent" }, s);
      hit.addEventListener("pointermove", function (ev) {
        var xy = pointerXY(ev), r = s.getBoundingClientRect();
        var i = clamp(Math.round(((xy[0] - r.left) * (w / r.width) - m.l) / (w - m.l - m.r) * (n - 1)), 0, n - 1);
        cross.setAttribute("x1", xpos(i)); cross.setAttribute("x2", xpos(i)); cross.setAttribute("visibility", "visible");
        showTip(function (t) { html("div", "tip-h", it.name + ", " + labelX(xs[i]), t); tipRow(t, "var(--s1)", it.values[i] === null ? "Not live" : fmt(it.values[i], format), ""); }, xy[0], xy[1]);
      });
      hit.addEventListener("pointerleave", function () { cross.setAttribute("visibility", "hidden"); hideTip(); });
    });
    return {
      table: function () { return { cols: [""].concat(items.map(function (it) { return it.name; })), rows: xs.map(function (x, i) { return [labelX(x)].concat(items.map(function (it) { return it.values[i] === null ? "" : fmt(it.values[i], format); })); }) }; }
    };
  }

  /* ----------------------------------------------------------------- slope */
  function drawSlope(mount, spec) {
    while (mount.firstChild) mount.removeChild(mount.firstChild);
    var items = spec.data.items, labels = spec.data.labels || ["Before", "After"];
    var width = Math.max(260, mount.clientWidth || 600);
    var cols = width < 520 ? 2 : 4;
    var grid = html("div", null, null, mount);
    grid.style.cssText = "display:grid;grid-template-columns:repeat(" + cols + ",minmax(0,1fr));gap:1.2rem 1.4rem";
    items.forEach(function (it) {
      var cell = html("div", null, null, grid);
      cell.style.borderTop = "1px solid var(--rule)";
      cell.style.paddingTop = ".5rem";
      var title = html("div", null, it.name, cell);
      title.style.cssText = "font:600 .84rem/1.3 var(--f-ui);min-height:2.3em";
      var w = Math.floor((width - (cols - 1) * 22) / cols), h = 170;
      var s = svg("svg", { width: w, height: h, viewBox: "0 0 " + w + " " + h }, cell);
      var before = Number(it.before), after = Number(it.after);
      var top = Math.max(before, after) * 1.08;
      var y = linear(0, top, h - 34, 22);
      var x0 = 46, x1 = w - 46;
      svg("line", { x1: x0, x2: x0, y1: y(0), y2: y(top), stroke: "var(--grid)" }, s);
      svg("line", { x1: x1, x2: x1, y1: y(0), y2: y(top), stroke: "var(--grid)" }, s);
      var better = (it.better === "up") === (after > before);
      var ln = svg("line", { x1: x0, y1: y(before), x2: x1, y2: y(after), "stroke-width": 2 }, s);
      ln.style.stroke = "var(--ink-2)";
      var c0 = svg("circle", { cx: x0, cy: y(before), r: 5, "stroke-width": 2 }, s); c0.style.cssText = "fill:var(--legacy);stroke:var(--paper)";
      var c1 = svg("circle", { cx: x1, cy: y(after), r: 5, "stroke-width": 2 }, s); c1.style.cssText = "fill:var(--s1);stroke:var(--paper)";
      var f0 = fmt(before, it.format), f1 = fmt(after, it.format);
      txt(s, x0 - 10, y(before) + 5, f0, { "class": "label-strong", "text-anchor": "end" }).style.fontSize = "14px";
      txt(s, x1 + 10, y(after) + 5, f1, { "class": "label-strong" }).style.fontSize = "14px";
      var ax = svg("g", { "class": "axis" }, s);
      var short = w < 240;
      var la = short ? String(labels[0]).slice(-4) : labels[0], lb = short ? String(labels[1]).slice(-4) : labels[1];
      txt(ax, x0, h - 16, la, { "text-anchor": "middle" }).style.fontSize = "10.5px";
      txt(ax, x1, h - 16, lb, { "text-anchor": "middle" }).style.fontSize = "10.5px";
      var ratio = before && after ? (after > before ? after / before : before / after) : 0;
      var verdict = html("div", null, (better ? "Better" : "Worse") + (ratio ? ", " + (ratio >= 10 ? Math.round(ratio) : ratio.toFixed(1)) + "×" : ""), cell);
      verdict.style.cssText = "font:600 .74rem/1.3 var(--f-ui);letter-spacing:.04em;color:" + (better ? "var(--good)" : "var(--bad)");
    });
    return { table: function () { return { cols: ["Measure", labels[0], labels[1]], rows: items.map(function (it) { return [it.name, fmt(it.before, it.format), fmt(it.after, it.format)]; }) }; } };
  }

  var CHARTS = { line: drawLine, area: drawLine, stacked: drawLine, bars: drawBars, burnup: drawBurnup, calendar: drawCalendar, multiples: drawMultiples, slope: drawSlope };

  /* ------------------------------------------------------- chart wrapper */
  function mountChart(fig, spec, mount, state) {
    var draw = CHARTS[spec.chart];
    if (!draw || !mount) return null;
    var ctl = { state: state || {}, api: null };
    function render() {
      try { ctl.api = draw(mount, spec, ctl.state); }
      catch (err) {
        while (mount.firstChild) mount.removeChild(mount.firstChild);
        html("p", "fig-note", "This chart could not be drawn: " + err.message, mount);
      }
    }
    ctl.render = render;
    ctl.update = function (patch) { for (var k in patch) ctl.state[k] = patch[k]; render(); };
    render();
    var lastW = mount.clientWidth;
    if (window.ResizeObserver) new ResizeObserver(function () { if (Math.abs(mount.clientWidth - lastW) > 8) { lastW = mount.clientWidth; render(); } }).observe(mount);
    var btn = fig && fig.querySelector(".show-table");
    var slot = fig && fig.querySelector(".table-slot");
    if (btn && slot) {
      btn.addEventListener("click", function () {
        var open = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", open ? "false" : "true");
        btn.textContent = open ? "Show the numbers" : "Hide the numbers";
        slot.hidden = open;
        if (!open && ctl.api && ctl.api.table) {
          while (slot.firstChild) slot.removeChild(slot.firstChild);
          var t = ctl.api.table();
          var table = html("table", "data-table", null, slot);
          var tr = html("tr", null, null, html("thead", null, null, table));
          t.cols.forEach(function (c) { html("th", null, c, tr).setAttribute("scope", "col"); });
          var tb = html("tbody", null, null, table);
          t.rows.forEach(function (r) { var row = html("tr", null, null, tb); r.forEach(function (c) { html("td", null, c, row); }); });
        }
      });
    }
    return ctl;
  }

