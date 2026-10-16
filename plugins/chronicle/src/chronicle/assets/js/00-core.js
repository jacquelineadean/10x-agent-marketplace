/* chronicle runtime, part 1: helpers, tooltips and chart frames. The build joins every
   js/ file in name order inside one function; all text from the data goes in through
   textContent. */
  "use strict";
  var doc = document;
  var root = doc.documentElement;
  root.classList.add("js");
  var holder = doc.getElementById("chronicle-data");
  if (!holder) return;
  var DATA = JSON.parse(holder.textContent || "{}");
  var FIGS = DATA.figs || {};
  var SOURCES = DATA.sources || {};
  var SVGNS = "http://www.w3.org/2000/svg";
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  /* ------------------------------------------------------------ helpers */
  function svg(tag, attrs, parent) {
    var node = doc.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }
  function html(tag, cls, text, parent) {
    var node = doc.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (parent) parent.appendChild(node);
    return node;
  }
  function txt(parent, x, y, s, attrs) {
    var a = attrs || {};
    a.x = x; a.y = y;
    var t = svg("text", a, parent);
    t.textContent = String(s);
    return t;
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function linear(d0, d1, r0, r1) {
    var span = d1 - d0 || 1;
    var f = function (v) { return r0 + (v - d0) / span * (r1 - r0); };
    f.invert = function (px) { return d0 + (px - r0) / (r1 - r0) * span; };
    return f;
  }
  function niceStep(span, count) {
    var raw = span / Math.max(count, 1);
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var norm = raw / mag;
    var step = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
    return step * mag;
  }
  function ticks(lo, hi, count) {
    var step = niceStep(hi - lo, count);
    var out = [];
    var start = Math.ceil(lo / step - 1e-9) * step;
    for (var v = start; v <= hi + step * 1e-6; v += step) out.push(Math.round(v / step) * step || 0);
    return out;
  }
  function niceMax(v) {
    if (v <= 0) return 1;
    var step = niceStep(v, 4);
    return Math.ceil(v / step) * step;
  }
  var ROLES = { accent: "var(--s1)", legacy: "var(--legacy)", muted: "var(--muted)", bad: "var(--bad)", good: "var(--good)", warn: "var(--warn)", ink: "var(--ink)", surface: "var(--surface)", rule: "var(--rule)" };
  /* A color name from a story: a role, s1 to s6, a theme color (kraft or c-kraft) or a hex. */
  function colorOf(name, fallback) {
    var c = String(name || "");
    if (ROLES[c]) return ROLES[c];
    if (/^s[1-6]$/.test(c)) return "var(--" + c + ")";
    if (/^#[0-9a-fA-F]{3,8}$/.test(c) || /^var\(--[a-z0-9-]+\)$/.test(c)) return c;
    if (/^c-[a-z][a-z0-9-]*$/.test(c)) return "var(--" + c + ")";
    if (/^[a-z][a-z0-9-]*$/.test(c)) return "var(--c-" + c + ", " + (fallback || "var(--muted)") + ")";
    return fallback || "var(--muted)";
  }
  function seriesColor(i, s) {
    if (s && s.color) return colorOf(s.color, "var(--s" + ((i % 6) + 1) + ")");
    return "var(--s" + ((i % 6) + 1) + ")";
  }
  function fmt(v, kind) {
    if (v === null || v === undefined || isNaN(v)) return "n/a";
    var n = Number(v);
    switch (kind) {
      case "pct": return (Math.abs(n) >= 10 || Number.isInteger(n) ? Math.round(n) : n.toFixed(1)) + "%";
      case "pct1": return n.toFixed(1) + "%";
      case "pct2": return n.toFixed(2) + "%";
      case "pct3": return n.toFixed(3) + "%";
      case "int": return Math.round(n).toLocaleString("en-US");
      case "dec1": return n.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
      case "dec2": return n.toFixed(2);
      case "money_k": return n >= 1000 ? "$" + (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, "") + "M" : "$" + Math.round(n) + "K";
      case "money": return compactMoney(n);
      case "ms": return Math.round(n).toLocaleString("en-US") + " ms";
      case "compact": return compact(n);
      default:
        if (Math.abs(n) >= 1000) return Math.round(n).toLocaleString("en-US");
        return Number.isInteger(n) ? String(n) : n.toFixed(1);
    }
  }
  function compact(n) {
    var a = Math.abs(n);
    if (a >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + "B";
    if (a >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (a >= 1e3) return (n / 1e3).toFixed(a >= 1e5 ? 0 : 1).replace(/\.0$/, "") + "K";
    return String(Math.round(n));
  }
  function compactMoney(n) { return (n < 0 ? "−$" : "$") + compact(Math.abs(n)); }
  function parseDate(s) {
    var p = String(s).split("-").map(Number);
    return new Date(Date.UTC(p[0], (p[1] || 1) - 1, p[2] || 1));
  }
  function isoDay(d) { return d.toISOString().slice(0, 10); }
  function fmtDate(d, style) {
    var m = MONTHS[d.getUTCMonth()], y = d.getUTCFullYear();
    if (style === "month") return m + " " + y;
    if (style === "short") return d.getUTCDate() + " " + m;
    return d.getUTCDate() + " " + m + " " + y;
  }
  function labelX(x) {
    var s = String(x);
    if (/^\d{4}-\d{2}$/.test(s)) { var d = parseDate(s); return MONTHS[d.getUTCMonth()] + " " + d.getUTCFullYear(); }
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return fmtDate(parseDate(s));
    return s;
  }
  function tickX(x, withYear) {
    var s = String(x);
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
      var day = parseDate(s);
      return day.getUTCDate() + " " + MONTHS[day.getUTCMonth()] + (withYear ? " " + day.getUTCFullYear() : "");
    }
    if (/^\d{4}-\d{2}/.test(s)) {
      var d = parseDate(s), m = d.getUTCMonth();
      return withYear ? MONTHS[m] + " " + d.getUTCFullYear() : MONTHS[m];
    }
    return s;
  }
  function addDays(d, n) { return new Date(d.getTime() + n * 86400000); }
  function monthsBetween(a, b) { return (b.getUTCFullYear() - a.getUTCFullYear()) * 12 + b.getUTCMonth() - a.getUTCMonth(); }

  /* -------------------------------------------------------------- tooltip */
  var tip = html("div", "tip", null, doc.body);
  tip.setAttribute("role", "status");
  function showTip(build, x, y) {
    while (tip.firstChild) tip.removeChild(tip.firstChild);
    build(tip);
    tip.classList.add("on");
    var r = tip.getBoundingClientRect();
    var left = x + 14, top = y + 14;
    if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
    if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = Math.max(8, top) + "px";
  }
  function hideTip() { tip.classList.remove("on"); }
  function tipRow(parent, color, value, label) {
    var row = html("div", "tip-row", null, parent);
    if (color) { var k = html("span", "tip-key", null, row); k.style.background = color; }
    html("b", null, value, row);
    if (label) html("span", null, label, row);
  }
  function pointerXY(ev) {
    if (ev.touches && ev.touches[0]) return [ev.touches[0].clientX, ev.touches[0].clientY];
    return [ev.clientX, ev.clientY];
  }

  /* ---------------------------------------------------------- fact chips */
  function factTip(node) {
    var src = SOURCES[node.getAttribute("data-src") || ""];
    var note = node.getAttribute("data-note");
    var r = node.getBoundingClientRect();
    showTip(function (t) {
      html("div", "tip-h", src ? src.label : "Fact", t);
      if (note) html("div", null, note, t);
      if (src && src.asOf) html("div", "tip-src", "As of " + src.asOf, t);
      if (!src) html("div", "tip-src", "No source recorded", t);
    }, r.left, r.bottom);
  }
  doc.querySelectorAll(".fact").forEach(function (node) {
    node.addEventListener("mouseenter", function () { factTip(node); });
    node.addEventListener("focus", function () { factTip(node); });
    node.addEventListener("mouseleave", hideTip);
    node.addEventListener("blur", hideTip);
  });

  /* ------------------------------------------------------------ chart frame */
  function frame(mount, opts) {
    while (mount.firstChild) mount.removeChild(mount.firstChild);
    var width = Math.max(260, mount.clientWidth || 600);
    var narrow = width < 560;
    var height = opts.height || (narrow ? 250 : 320);
    var m = { top: opts.top !== undefined ? opts.top : 26, right: opts.right !== undefined ? opts.right : (narrow ? 12 : 24), bottom: 30, left: opts.left !== undefined ? opts.left : 8 };
    var s = svg("svg", { width: width, height: height, viewBox: "0 0 " + width + " " + height }, mount);
    return { svg: s, width: width, height: height, m: m, narrow: narrow, iw: width - m.left - m.right, ih: height - m.top - m.bottom };
  }
  function yAxis(f, y, vals, format, unit, outside) {
    var g = svg("g", { "class": "grid" }, f.svg);
    var labels = svg("g", { "class": "axis" }, f.svg);
    vals.forEach(function (v, i) {
      var py = y(v);
      svg("line", { x1: f.m.left, x2: f.width - f.m.right, y1: py, y2: py, "class": i === 0 ? "baseline" : "" }, g);
      var label = fmt(v, format) + (i === vals.length - 1 && unit ? " " + unit : "");
      if (outside) txt(labels, f.m.left - 6, py + 4, label, { "text-anchor": "end" });
      else txt(labels, f.m.left, py - 5, label);
    });
  }
  function xAxis(f, xs, xpos, minGap) {
    var g = svg("g", { "class": "axis" }, f.svg);
    var gap = minGap || (f.narrow ? 64 : 72);
    var every = Math.max(1, Math.ceil(gap / Math.max(1, f.iw / Math.max(1, xs.length - 1))));
    var last = -1e9, lastYear = null;
    xs.forEach(function (x, i) {
      if (i % every !== 0 && i !== xs.length - 1) return;
      var px = xpos(i);
      if (px - last < gap * (lastYear === null ? 1.1 : 0.8)) return;
      last = px;
      var year = /^\d{4}/.test(String(x)) ? String(x).slice(0, 4) : null;
      var anchor = i === 0 ? "start" : (i === xs.length - 1 ? "end" : "middle");
      txt(g, px, f.height - 8, tickX(x, year !== null && year !== lastYear), { "text-anchor": anchor });
      lastYear = year;
      svg("line", { x1: px, x2: px, y1: f.height - f.m.bottom, y2: f.height - f.m.bottom + 4, stroke: "var(--ink-2)" }, g);
    });
  }
  function pathFrom(points) {
    var d = "", pen = false;
    points.forEach(function (p) {
      if (!p || p[1] === null || isNaN(p[1])) { pen = false; return; }
      d += (pen ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1);
      pen = true;
    });
    return d;
  }
  function indexRange(xs, focus) {
    if (!focus) return null;
    var lo = -1, hi = -1;
    for (var i = 0; i < xs.length; i++) {
      var s = String(xs[i]);
      if (lo < 0 && s >= String(focus.from)) lo = i;
      if (s <= String(focus.to || focus.from)) hi = i;
    }
    if (lo < 0 || hi < lo) return null;
    return [lo, hi];
  }
  function legend(parent, items, kind) {
    var ul = html("ul", "legend", null, null);
    items.forEach(function (it, i) {
      var li = html("li", null, null, ul);
      var key = html("span", "key" + (kind === "line" ? " line" : ""), null, li);
      key.style.background = seriesColor(i, it);
      if (it.opacity !== undefined) key.style.opacity = it.opacity;
      li.appendChild(doc.createTextNode(it.name));
    });
    parent.insertBefore(ul, parent.firstChild);
  }
  function hoverLayer(f, n, xpos, onMove, onLeave) {
    var hit = svg("rect", { x: f.m.left, y: f.m.top, width: f.iw, height: f.ih, fill: "transparent", tabindex: 0, "aria-label": "Chart, use arrow keys to read values" }, f.svg);
    var cross = svg("line", { "class": "crosshair", y1: f.m.top - 6, y2: f.height - f.m.bottom, visibility: "hidden" }, f.svg);
    var current = n - 1;
    function at(i, cx, cy) {
      current = clamp(i, 0, n - 1);
      var px = xpos(current);
      cross.setAttribute("x1", px); cross.setAttribute("x2", px); cross.setAttribute("visibility", "visible");
      onMove(current, cx, cy);
    }
    function move(ev) {
      var xy = pointerXY(ev);
      var r = f.svg.getBoundingClientRect();
      var local = (xy[0] - r.left) * (f.width / r.width);
      var best = 0, bd = 1e9;
      for (var i = 0; i < n; i++) { var dd = Math.abs(xpos(i) - local); if (dd < bd) { bd = dd; best = i; } }
      at(best, xy[0], xy[1]);
    }
    function leave() { cross.setAttribute("visibility", "hidden"); hideTip(); if (onLeave) onLeave(); }
    hit.addEventListener("pointermove", move);
    hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", leave);
    hit.addEventListener("blur", leave);
    hit.addEventListener("keydown", function (ev) {
      if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
      ev.preventDefault();
      var r = hit.getBoundingClientRect();
      var ni = current + (ev.key === "ArrowRight" ? 1 : -1);
      var svgR = f.svg.getBoundingClientRect();
      at(ni, svgR.left + xpos(clamp(ni, 0, n - 1)) * (svgR.width / f.width), r.top + 20);
    });
    hit.addEventListener("focus", function () { var svgR = f.svg.getBoundingClientRect(); at(current, svgR.left + xpos(current) * (svgR.width / f.width), svgR.top + 30); });
    return hit;
  }

