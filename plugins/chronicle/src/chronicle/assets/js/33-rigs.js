  /* ------------------------------------------------------------------ rigs */
  // A rig is a figure painted in parts. Every frame each part turns about its pivot by a
  // rule for its role, and the rig's gait says whether the legs stride, the head grazes or
  // the flippers stroke. Plates play a gait in place; a panorama also walks rigs about.
  var TURN = Math.PI * 2;
  function rigNum(node, key, fallback) {
    var v = parseFloat(node.getAttribute("data-" + key));
    return isNaN(v) ? fallback : v;
  }
  function rigOf(el) {
    return {
      el: el,
      gait: el.getAttribute("data-gait") || "still",
      bob: rigNum(el, "bob", 2), h: rigNum(el, "h", 1), w: rigNum(el, "w", 1),
      speed: rigNum(el, "speed", 30), stride: rigNum(el, "stride", 60),
      cycle: Math.random(), t0: Math.random() * 10, act: 0,
      parts: Array.prototype.slice.call(el.querySelectorAll(".part")).map(function (p) {
        return {
          el: p, role: p.getAttribute("data-role"), amp: rigNum(p, "amp", 0), phase: rigNum(p, "phase", 0),
          speed: rigNum(p, "speed", 3), down: rigNum(p, "down", 0), nod: rigNum(p, "nod", 0),
          look: rigNum(p, "look", 0), last: null
        };
      })
    };
  }
  // One frame. `moving` strides the legs; `cycles` is how far the stride cycle went on.
  function rigStep(rig, now, dt, moving, cycles) {
    var t = now / 1000 + rig.t0;
    rig.cycle += cycles;
    var c = TURN * rig.cycle;
    rig.act += ((moving ? 0 : 1) - rig.act) * Math.min(1, 2.5 * dt);
    var scale = rig.el.clientHeight / rig.h;
    var lift = (moving ? Math.abs(Math.sin(c)) * rig.bob : Math.sin(1.6 * t) * 0.8) * scale;
    rig.parts.forEach(function (p) {
      var a = 0;
      if (p.role === "leg" || p.role === "flipper") a = moving ? p.amp * Math.sin(c + TURN * p.phase) : 0;
      else if (p.role === "head") a = (moving ? p.nod * Math.sin(2 * c) : 0) + rig.act * p.down * (0.75 + 0.25 * Math.sin(1.3 * t)) + p.look * Math.sin(0.4 * t);
      else if (p.role === "tail" || p.role === "wing") a = p.amp * Math.sin(p.speed * t + TURN * p.phase);
      else if (p.role === "ear") a = Math.pow(Math.max(0, Math.sin(p.speed * t + TURN * p.phase)), 30) * p.amp;
      else if (p.role === "claw") a = rig.act * p.amp * Math.max(0, Math.sin(p.speed * t));
      if (p.last === null || Math.abs(a - p.last) > 0.05) {
        p.el.style.rotate = a.toFixed(2) + "deg";
        p.last = a;
      }
      p.el.style.translate = "0 " + (-lift).toFixed(2) + "px";
    });
  }
  // A gait played where the rig stands: plates, and animals resting in a panorama.
  function rigInPlace(rig, now, dt) {
    var g = rig.gait;
    if (g === "walk" || g === "swim") rigStep(rig, now, dt, true, dt * rig.speed / Math.max(1, rig.stride));
    else if (g === "crawl") rigStep(rig, now, dt, true, 2.2 * dt);
    else rigStep(rig, now, dt, false, 0);
  }
  // The pose a still copy shows: heads down where the gait grazes, everything at rest.
  function rigPose(rig) {
    rig.act = 1;
    rig.t0 = 0;
    rigStep(rig, 0, 0, false, 0);
  }
  // A rig on a plate plays its gait in place while it is on screen; a still copy poses it.
  function initRig(node) {
    var rig = rigOf(node);
    if (reduceMotion) { rigPose(rig); return; }
    var last = 0;
    tickers.push(function (vh, now) {
      var r = node.getBoundingClientRect();
      if (r.bottom < -50 || r.top > vh + 50) { last = 0; return; }
      var dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      rigInPlace(rig, now, dt);
    });
  }
  INIT.rig = initRig;
