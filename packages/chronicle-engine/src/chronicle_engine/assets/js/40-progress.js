  /* --------------------------------------------------------- progress bar */
  /* The sticky bar maps reading position onto a device the theme picks. The engine draws
     numbered steps; a plugin adds devices to DEVICES. Every device shares the same
     chapter geometry and gets it through ctx. A theme may draw its own icon. */
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

  var DEVICES = {};
  DEVICES.steps = function (ctx, s, w, h) {
    var nav = ctx.nav, hook = ctx.hook;
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
  
  };

  function initProgress() {
    var track = doc.querySelector(".spanbar-track");
    var now = doc.querySelector(".spanbar-now");
    var nav = DATA.nav || [];
    var cfg = DATA.progress || { kind: "steps" };
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

    var ctx = { nav: nav, hook: hook, cfg: cfg, starts: starts, spanOf: spanOf, total: total, track: track };

    function draw() {
      while (track.firstChild) track.removeChild(track.firstChild);
      var w = Math.max(120, track.clientWidth), h = 34;
      var s = svg("svg", { width: w, height: h, viewBox: "0 0 " + w + " " + h, "class": "pb pb-" + cfg.kind }, track);
      device = (DEVICES[cfg.kind] || DEVICES.steps)(ctx, s, w, h);
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
