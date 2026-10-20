  /* --------------------------------------------------------- progress bar */
  /* The sticky bar maps reading position onto a device chosen by the theme: bridge
     arches, an icon riding a line, an icon walking a route the page draws (a trail, a
     river, a subway line), a tape measure, flags on a course, a clock or numbered steps.
     Every device shares the same chapter geometry. A theme may draw its own icon. */
  var ICON_PATHS = {
    parcel: "M-9,-7 L9,-7 L9,7 L-9,7 Z M-9,-2 L9,-2 M-2,-7 L-2,7",
    van: "M-11,5 L-11,-5 Q-11,-7 -9,-7 L3,-7 L7,-2 L11,-1 L11,5 Z M3,-6 L3,-2 L7,-2",
    truck: "M-12,5 L-12,-7 L3,-7 L3,5 Z M3,-3 L8,-3 L11,1 L11,5 L3,5",
    cart: "M-11,-7 L-7,-7 L-4,4 L8,4 L10,-4 L-6,-4",
    plane: "M-11,0 L11,0 M2,0 L-4,-8 M2,0 L-4,8 M-9,0 L-11,-4 M-9,0 L-11,4",
    train: "M-10,5 L-10,-5 Q-10,-8 -6,-8 L6,-8 Q10,-8 10,-5 L10,5 Z M-10,-1 L10,-1",
    ship: "M-11,1 L11,1 L7,7 L-8,7 Z M-4,1 L-4,-6 L5,-1 L-4,-1",
    pin: "M0,8 C-6,1 -7,-2 -7,-4 A7,7 0 1 1 7,-4 C7,-2 6,1 0,8 Z",
    ball: "M-6,0 A6,6 0 1 0 6,0 A6,6 0 1 0 -6,0 Z",
    boot: "M-8,7 L-8,-8 L-1,-8 L-1,0 Q6,1 9,4 L9,7 Z",
    rocket: "M-10,0 Q-4,-6 8,0 Q-4,6 -10,0 Z M-6,-3 L-10,-7 M-6,3 L-10,7",
    cup: "M-9,-6 L7,-6 L5,7 L-7,7 Z M7,-3 C12,-3 12,3 6,3",
    book: "M-10,-7 L0,-5 L10,-7 L10,6 L0,8 L-10,6 Z M0,-5 L0,8",
    dot: "M-5,0 A5,5 0 1 0 5,0 A5,5 0 1 0 -5,0 Z"
  };
  var WHEELS = { van: [[-6, 6], [6, 6]], truck: [[-8, 6], [7, 6]], cart: [[-3, 7], [6, 7]], train: [[-6, 6], [6, 6]] };

  var CUSTOM_ICON = (DATA.progress && DATA.progress.icon_path) || "";
  function drawIcon(parent, name, x, y, scale) {
    var g = svg("g", { "class": "pb-icon", transform: "translate(" + x + "," + y + ") scale(" + (scale || 1) + ")" }, parent);
    svg("path", { d: name === "custom" && CUSTOM_ICON ? CUSTOM_ICON : (ICON_PATHS[name] || ICON_PATHS.dot), "class": "pb-icon-body" }, g);
    (WHEELS[name] || []).forEach(function (w) { svg("circle", { cx: w[0], cy: w[1], r: 2.4, "class": "pb-icon-wheel" }, g); });
    return g;
  }

  function initProgress() {
    var track = doc.querySelector(".spanbar-track");
    var now = doc.querySelector(".spanbar-now");
    var nav = DATA.nav || [];
    var cfg = DATA.progress || { kind: "arches" };
    var sections = nav.map(function (n) { return doc.getElementById(n.id); });
    if (!track || !nav.length) return function () {};
    doc.documentElement.setAttribute("data-progress", cfg.kind);
    var total = cfg.total || 0;
    var starts = nav.map(function (n, i) {
      return total && typeof n.at === "number" ? clamp(n.at / total, 0, 1) : i / nav.length;
    });
    function spanOf(i) { return [starts[i], i + 1 < starts.length ? starts[i + 1] : 1]; }
    var device = null;

    function go(i) { if (sections[i]) sections[i].scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" }); }
    function hook(g, i) {
      g.setAttribute("tabindex", "0");
      g.setAttribute("role", "listitem");
      g.setAttribute("aria-label", nav[i].no + ". " + nav[i].title);
      g.addEventListener("click", function () { go(i); });
      g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(i); } });
      g.addEventListener("pointerenter", function (ev) { var xy = pointerXY(ev); showTip(function (t) { html("div", "tip-h", nav[i].no + "  " + nav[i].title, t); }, xy[0], xy[1] + 10); });
      g.addEventListener("pointerleave", hideTip);
    }

    var DEVICES = {
      arches: function (s, w, h) {
        var deckY = 6, spring = 30, parts = [];
        svg("line", { x1: 0, x2: w, y1: deckY, y2: deckY, "class": "deck" }, s);
        svg("line", { x1: 0, x2: w, y1: spring + 3, y2: spring + 3, "class": "water" }, s);
        var defs = svg("defs", null, s);
        nav.forEach(function (n, i) {
          var sp = spanOf(i), pier = Math.min(6, (sp[1] - sp[0]) * w * 0.08);
          var x0 = sp[0] * w + pier, x1 = sp[1] * w - pier;
          var cx = (x0 + x1) / 2, rx = (x1 - x0) / 2, ry = Math.min(spring - deckY - 5, rx), ring = 4;
          var outer = "M" + x0 + "," + spring + " A" + rx + "," + ry + " 0 0 1 " + x1 + "," + spring;
          var band = outer + " L" + (x1 - ring) + "," + spring + " A" + (rx - ring) + "," + (ry - ring) + " 0 0 0 " + (x0 + ring) + "," + spring + " Z";
          var g = svg("g", { "class": "arch pb-part" }, s);
          var clip = svg("clipPath", { id: "arch-clip-" + i }, defs);
          var clipRect = svg("rect", { x: x0, y: 0, width: 0, height: h }, clip);
          svg("path", { d: band, "class": "arch-fill", "clip-path": "url(#arch-clip-" + i + ")" }, g);
          svg("path", { d: outer, "class": "arch-ring" }, g);
          svg("path", { d: "M" + (x0 + ring) + "," + spring + " A" + (rx - ring) + "," + (ry - ring) + " 0 0 1 " + (x1 - ring) + "," + spring, "class": "arch-ring" }, g);
          svg("line", { x1: x0, x2: x0, y1: deckY, y2: spring + 3, "class": "deck" }, g);
          svg("line", { x1: x1, x2: x1, y1: deckY, y2: spring + 3, "class": "deck" }, g);
          var keyY = spring - ry;
          var key = svg("rect", { x: cx - 3, y: keyY - 3, width: 6, height: 6, transform: "rotate(45 " + cx + " " + keyY + ")", "class": "arch-key" }, g);
          svg("rect", { x: sp[0] * w, y: 0, width: (sp[1] - sp[0]) * w, height: h, "class": "pb-hit" }, g);
          hook(g, i);
          parts.push({ g: g, clip: clipRect, key: key, x0: x0, width: x1 - x0 });
        });
        return function (fracs, current) {
          parts.forEach(function (pt, i) {
            pt.clip.setAttribute("width", (pt.width * fracs[i]).toFixed(1));
            pt.key.classList.toggle("on", fracs[i] >= 0.97);
            pt.g.classList.toggle("current", i === current);
          });
        };
      },

      track: function (s, w, h) {
        var pad = 14, y = h / 2 + 3, x = linear(0, 1, pad, w - pad), line = cfg.line || "solid";
        var base = svg("g", { "class": "pb-line pb-" + line }, s);
        if (line === "belt") {
          svg("rect", { x: pad - 7, y: y - 5, width: w - 2 * pad + 14, height: 10, rx: 5, "class": "pb-belt" }, base);
          for (var r = pad; r <= w - pad; r += 24) svg("line", { x1: r, x2: r, y1: y - 3, y2: y + 3, "class": "pb-roller" }, base);
        } else if (line === "road") {
          svg("rect", { x: pad - 6, y: y - 4, width: w - 2 * pad + 12, height: 8, rx: 2, "class": "pb-road" }, base);
          svg("line", { x1: pad, x2: w - pad, y1: y, y2: y, "class": "pb-lane" }, base);
        } else if (line === "rail") {
          for (var t = pad; t <= w - pad; t += 7) svg("line", { x1: t, x2: t, y1: y - 4, y2: y + 4, "class": "pb-sleeper" }, base);
          svg("line", { x1: pad, x2: w - pad, y1: y - 2.5, y2: y - 2.5, "class": "pb-rail" }, base);
          svg("line", { x1: pad, x2: w - pad, y1: y + 2.5, y2: y + 2.5, "class": "pb-rail" }, base);
        } else {
          svg("line", { x1: pad, x2: w - pad, y1: y, y2: y, "class": "pb-base" + (line === "dashed" ? " dashed" : "") }, base);
        }
        var done = svg("line", { x1: pad, x2: pad, y1: y, y2: y, "class": "pb-done pb-done-" + line }, s);
        var stops = nav.map(function (n, i) {
          var g = svg("g", { "class": "pb-stop pb-part" }, s);
          var px = x(starts[i]);
          svg("circle", { cx: px, cy: y, r: 4.5, "class": "pb-dot" }, g);
          svg("rect", { x: px - 9, y: 0, width: 18, height: h, "class": "pb-hit" }, g);
          hook(g, i);
          return g;
        });
        svg("circle", { cx: x(1), cy: y, r: 3, "class": "pb-end" }, s);
        var icon = drawIcon(s, CUSTOM_ICON ? "custom" : (cfg.icon || "parcel"), pad, y - 9, 0.9);
        return function (fracs, current, pos) {
          var px = x(pos);
          done.setAttribute("x2", px.toFixed(1));
          icon.setAttribute("transform", "translate(" + px.toFixed(1) + "," + (y - 10) + ") scale(0.9)");
          stops.forEach(function (g, i) {
            g.classList.toggle("passed", fracs[i] > 0);
            g.classList.toggle("current", i === current);
          });
        };
      },

      route: function (s, w, h) {
        /* The theme's path lives in a 1000 x 40 box; it is sampled by length and scaled to
           the bar, so stops fall at equal distances along the route, not along x. */
        var pad = 14, n = 160, sx = (w - 2 * pad) / 1000, sy = (h - 8) / 40;
        var probe = svg("path", { d: cfg.path || "M0,20 L1000,20", fill: "none" }, s);
        var len = probe.getTotalLength ? probe.getTotalLength() : 0;
        function at(t) {
          var p = len ? probe.getPointAtLength(len * clamp(t, 0, 1)) : { x: t * 1000, y: 20 };
          return [pad + p.x * sx, 4 + p.y * sy];
        }
        function points(list) { return list.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" "); }
        var pts = [];
        for (var k = 0; k <= n; k++) pts.push(at(k / n));
        s.removeChild(probe);
        svg("polyline", { points: points(pts), "class": "pb-route-line pb-" + (cfg.line || "dashed") }, s);
        var done = svg("polyline", { points: "", "class": "pb-route-done" }, s);
        var stops = nav.map(function (nv, i) {
          var g = svg("g", { "class": "pb-stop pb-part" }, s);
          var p = at(starts[i]);
          svg("circle", { cx: p[0], cy: p[1], r: 4.5, "class": "pb-dot" }, g);
          svg("rect", { x: p[0] - 9, y: 0, width: 18, height: h, "class": "pb-hit" }, g);
          hook(g, i);
          return g;
        });
        var end = at(1);
        svg("circle", { cx: end[0], cy: end[1], r: 3, "class": "pb-end" }, s);
        var icon = drawIcon(s, CUSTOM_ICON ? "custom" : (cfg.icon || "pin"), pts[0][0], pts[0][1], 0.8);
        return function (fracs, current, pos) {
          var p = at(pos);
          done.setAttribute("points", points(pts.slice(0, Math.floor(pos * n) + 1).concat([p])));
          icon.setAttribute("transform", "translate(" + p[0].toFixed(1) + "," + (p[1] - 9).toFixed(1) + ") scale(0.8)");
          stops.forEach(function (g, i) {
            g.classList.toggle("passed", fracs[i] > 0);
            g.classList.toggle("current", i === current);
          });
        };
      },

      tape: function (s, w, h) {
        var caseW = 30, y = h / 2 - 7, tapeH = 16, x0 = caseW - 4, len = w - x0 - 4;
        var reel = svg("g", { "class": "pb-reel" }, s);
        var tape = svg("g", { "class": "pb-tape" }, s);
        var clip = svg("clipPath", { id: "pb-tape-clip" }, svg("defs", null, s));
        var clipRect = svg("rect", { x: x0, y: 0, width: 0, height: h }, clip);
        tape.setAttribute("clip-path", "url(#pb-tape-clip)");
        svg("rect", { x: x0, y: y, width: len, height: tapeH, rx: 1.5, "class": "pb-tape-body" }, tape);
        var unit = cfg.total ? len / cfg.total : len / (nav.length * 10);
        var count = cfg.total ? cfg.total : nav.length * 10;
        var every = Math.max(1, Math.ceil(count / (len / 6)));
        for (var k = 0; k <= count; k += every) {
          var tx = x0 + k * unit, major = k % (every * 5) === 0;
          svg("line", { x1: tx, x2: tx, y1: y, y2: y + (major ? 9 : 5), "class": "pb-tick" }, tape);
        }
        var parts = nav.map(function (n, i) {
          var px = x0 + starts[i] * len;
          var g = svg("g", { "class": "pb-part pb-mark" }, tape);
          svg("line", { x1: px, x2: px, y1: y, y2: y + tapeH, "class": "pb-chapter" }, g);
          txt(g, px + 2.5, y + tapeH - 2.5, n.no, { "class": "pb-num" });
          return g;
        });
        svg("rect", { x: 1, y: y - 6, width: caseW, height: tapeH + 12, rx: 6, "class": "pb-case" }, reel);
        svg("circle", { cx: caseW / 2 + 1, cy: y + tapeH / 2, r: 6, "class": "pb-case-hub" }, reel);
        var hook2 = svg("rect", { x: x0, y: y - 3, width: 3, height: tapeH + 6, "class": "pb-hook" }, s);
        var hits = svg("g", null, s);
        nav.forEach(function (n, i) {
          var sp = spanOf(i);
          var g = svg("rect", { x: x0 + sp[0] * len, y: 0, width: (sp[1] - sp[0]) * len, height: h, "class": "pb-hit" }, hits);
          hook(g, i);
        });
        return function (fracs, current, pos) {
          var px = Math.max(10, pos * len);
          clipRect.setAttribute("width", px.toFixed(1));
          hook2.setAttribute("x", (x0 + px - 1).toFixed(1));
          parts.forEach(function (g, i) { g.classList.toggle("current", i === current); });
        };
      },

      flags: function (s, w, h) {
        var parts = [];
        var ball = svg("circle", { r: 3.2, cy: h - 6, cx: 0, "class": "pb-ball" }, s);
        svg("line", { x1: 0, x2: w, y1: h - 2.5, y2: h - 2.5, "class": "pb-ground" }, s);
        nav.forEach(function (n, i) {
          var sp = spanOf(i), px = (sp[0] + (sp[1] - sp[0]) * 0.72) * w;
          var g = svg("g", { "class": "pb-flag pb-part" }, s);
          svg("line", { x1: px, x2: px, y1: 4, y2: h - 3, "class": "pb-pole" }, g);
          svg("path", { d: "M" + px + ",4 L" + (px + 11) + ",8 L" + px + ",12 Z", "class": "pb-cloth" }, g);
          svg("ellipse", { cx: px, cy: h - 3, rx: 3, ry: 1.2, "class": "pb-cup" }, g);
          svg("rect", { x: sp[0] * w, y: 0, width: (sp[1] - sp[0]) * w, height: h, "class": "pb-hit" }, g);
          hook(g, i);
          parts.push({ g: g, x: px });
        });
        return function (fracs, current, pos) {
          var bx = pos * w;
          ball.setAttribute("cx", clamp(bx, 4, w - 4).toFixed(1));
          parts.forEach(function (pt, i) {
            pt.g.classList.toggle("played", fracs[i] >= 0.97);
            pt.g.classList.toggle("started", fracs[i] > 0 && fracs[i] < 0.97);
            pt.g.classList.toggle("current", i === current);
          });
        };
      },

      clock: function (s, w, h) {
        var r = h / 2 - 3, cx = r + 3, cy = h / 2, bx = cx + r + 12, bw = w - bx - 2;
        svg("circle", { cx: cx, cy: cy, r: r, "class": "pb-rim" }, s);
        var wedge = svg("path", { d: "", "class": "pb-elapsed" }, s);
        for (var k = 0; k < 12; k++) {
          var a = k / 12 * Math.PI * 2;
          svg("line", { x1: cx + Math.sin(a) * (r - 3), y1: cy - Math.cos(a) * (r - 3), x2: cx + Math.sin(a) * (r - 1), y2: cy - Math.cos(a) * (r - 1), "class": "pb-tick" }, s);
        }
        var hand = svg("line", { x1: cx, y1: cy, x2: cx, y2: cy - r + 3, "class": "pb-hand" }, s);
        svg("circle", { cx: cx, cy: cy, r: 1.8, "class": "pb-hub" }, s);
        var parts = nav.map(function (n, i) {
          var sp = spanOf(i);
          var g = svg("g", { "class": "pb-phase pb-part" }, s);
          var x0 = bx + sp[0] * bw, ww = Math.max(2, (sp[1] - sp[0]) * bw - 2);
          svg("rect", { x: x0, y: cy - 7, width: ww, height: 14, rx: 2, "class": "pb-phase-bg" }, g);
          var fill = svg("rect", { x: x0, y: cy - 7, width: 0, height: 14, rx: 2, "class": "pb-phase-fill" }, g);
          if (ww > 26) txt(g, x0 + 5, cy + 4, n.no, { "class": "pb-num" });
          hook(g, i);
          return { g: g, fill: fill, w: ww };
        });
        return function (fracs, current, pos) {
          var a = pos * Math.PI * 2;
          var large = pos > 0.5 ? 1 : 0;
          var ex = cx + Math.sin(a) * (r - 1), ey = cy - Math.cos(a) * (r - 1);
          wedge.setAttribute("d", pos <= 0 ? "" : "M" + cx + "," + cy + " L" + cx + "," + (cy - r + 1) + " A" + (r - 1) + "," + (r - 1) + " 0 " + large + " 1 " + ex.toFixed(2) + "," + ey.toFixed(2) + " Z");
          hand.setAttribute("x2", (cx + Math.sin(a) * (r - 4)).toFixed(2));
          hand.setAttribute("y2", (cy - Math.cos(a) * (r - 4)).toFixed(2));
          parts.forEach(function (pt, i) {
            pt.fill.setAttribute("width", (pt.w * fracs[i]).toFixed(1));
            pt.g.classList.toggle("current", i === current);
          });
        };
      },

      steps: function (s, w, h) {
        var pad = 12, y = h / 2, x = linear(0, nav.length - 1 || 1, pad, w - pad);
        svg("line", { x1: pad, x2: w - pad, y1: y, y2: y, "class": "pb-base" }, s);
        var done = svg("line", { x1: pad, x2: pad, y1: y, y2: y, "class": "pb-done" }, s);
        var parts = nav.map(function (n, i) {
          var g = svg("g", { "class": "pb-step pb-part" }, s);
          svg("circle", { cx: x(i), cy: y, r: 9, "class": "pb-step-dot" }, g);
          txt(g, x(i), y + 3.6, String(i + 1), { "class": "pb-step-n", "text-anchor": "middle" });
          hook(g, i);
          return g;
        });
        return function (fracs, current) {
          var reached = current < 0 ? 0 : current + fracs[current];
          done.setAttribute("x2", x(Math.min(reached, nav.length - 1)).toFixed(1));
          parts.forEach(function (g, i) {
            g.classList.toggle("passed", fracs[i] >= 0.97);
            g.classList.toggle("current", i === current);
          });
        };
      }
    };

    function draw() {
      while (track.firstChild) track.removeChild(track.firstChild);
      var w = Math.max(120, track.clientWidth), h = 34;
      var s = svg("svg", { width: w, height: h, viewBox: "0 0 " + w + " " + h, "class": "pb pb-" + cfg.kind }, track);
      device = (DEVICES[cfg.kind] || DEVICES.arches)(s, w, h);
    }
    draw();
    if (window.ResizeObserver) new ResizeObserver(draw).observe(track);
    return function (vh) {
      var current = -1, fracs = [];
      sections.forEach(function (sec, i) {
        if (!sec) { fracs.push(0); return; }
        var r = sec.getBoundingClientRect();
        fracs.push(clamp((vh * 0.35 - r.top) / Math.max(1, r.height), 0, 1));
        if (r.top < vh * 0.35) current = i;
      });
      var pos = 0;
      if (current >= 0) {
        var sp = spanOf(current);
        pos = sp[0] + (sp[1] - sp[0]) * fracs[current];
      }
      if (device) device(fracs, current, pos);
      if (now) {
        while (now.firstChild) now.removeChild(now.firstChild);
        if (current >= 0) { html("b", null, nav[current].no + "  ", now); now.appendChild(doc.createTextNode(nav[current].title)); }
        else now.appendChild(doc.createTextNode(cfg.start_label || word("overview", "Overview")));
      }
    };
  }
