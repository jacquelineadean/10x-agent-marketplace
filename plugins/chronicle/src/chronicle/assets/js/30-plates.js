  /* ---------------------------------------------------------------- plates */
  function initPlate(node, spec) {
    var stage = node.querySelector(".stage");
    var overlay = node.querySelector(".overlay");
    var layers = Array.prototype.slice.call(node.querySelectorAll(".layer"));
    var anchors = spec.anchors || {};
    var cable = null;
    var descend = layers.filter(function (l) { return l.getAttribute("data-motion") === "descend"; })[0];
    if (descend && anchors.hook && anchors.load) {
      cable = svg("line", { "class": "cable", x1: anchors.hook[0], y1: anchors.hook[1], x2: anchors.load[0], y2: anchors.load[1] }, overlay);
    }
    if (!reduceMotion) stage.classList.add("pre");
    // On a phone a wide painting fills a taller frame and pans as the reader scrolls, so
    // its labels and hotspots stay big enough to read and tap.
    var phone = window.matchMedia ? window.matchMedia("(max-width: 700px)") : null;
    var pan = false;
    function setPan() {
      pan = !!(phone && phone.matches) && node.classList.contains("wide") && (spec.width || 1) / (spec.height || 1) > 1.3;
      node.classList.toggle("pan", pan);
      if (!pan) stage.style.transform = "";
    }
    setPan();
    if (phone && phone.addEventListener) phone.addEventListener("change", setPan);
    var developed = reduceMotion;
    var spots = Array.prototype.slice.call(node.querySelectorAll(".spot"));
    var cards = Array.prototype.slice.call(node.querySelectorAll(".spot-card"));
    spots.forEach(function (b) {
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-spot");
        var on = b.getAttribute("aria-pressed") !== "true";
        spots.forEach(function (o) { o.setAttribute("aria-pressed", o === b && on ? "true" : "false"); });
        cards.forEach(function (c) { c.hidden = !(on && c.getAttribute("data-spot") === k); });
      });
    });
    plates.push(function (vh, now) {
      var r = stage.getBoundingClientRect();
      if (r.bottom < -50 || r.top > vh + 50) return;
      if (!developed && r.top < vh * 0.82) {
        developed = true;
        stage.classList.add("go");
        requestAnimationFrame(function () { stage.classList.remove("pre"); });
      }
      var p = clamp((vh - r.top) / (vh + r.height), 0, 1);
      if (pan) {
        var frameEl = stage.parentNode;
        var spare = r.width - frameEl.clientWidth;
        var q = reduceMotion ? 0.5 : clamp((p - 0.2) / 0.6, 0, 1);
        stage.style.transform = "translateX(" + (-spare * q).toFixed(1) + "px)";
      }
      layers.forEach(function (l, k) {
        var motion = l.getAttribute("data-motion");
        var travel = Number(l.getAttribute("data-travel")) / 100 * r.height;
        var phase = k * 1.7;
        if (motion === "pop") {
          if (developed && !l.classList.contains("popped")) l.classList.add("popped");
          return;
        }
        if (motion === "rise") {
          var tr = reduceMotion ? 1 : ease(clamp((p - 0.15) / 0.45, 0, 1));
          l.style.transform = "translateY(" + (-travel * tr).toFixed(1) + "px)";
          return;
        }
        if (motion === "descend") {
          var t = reduceMotion ? 1 : ease(clamp((p - 0.18) / 0.42, 0, 1));
          l.style.transform = "translateY(" + (travel * t).toFixed(1) + "px)";
          if (cable) {
            var h = spec.height || 1;
            cable.setAttribute("y2", (anchors.load[1] + travel * t / r.height * h).toFixed(1));
          }
        } else if (reduceMotion) {
          return;
        } else if (motion === "drift") {
          l.style.transform = "translate(" + (Math.sin(now / 3800) * travel * 1.6).toFixed(1) + "px," + (Math.cos(now / 2900) * travel * 0.25).toFixed(1) + "px)";
        } else if (motion === "fall") {
          var span = travel || 40;
          l.style.transform = "translateY(" + ((now / 9) % span - span / 2).toFixed(1) + "px)";
        } else if (motion === "cross") {
          var dist = Math.max(1, travel);
          var px = (now / 22 + phase * 97) % dist;
          l.style.transform = "translateX(" + px.toFixed(1) + "px)";
          l.style.opacity = String(clamp(Math.min(px / 40, (dist - px) / 40), 0, 1));
        } else if (motion === "sway") {
          l.style.transformOrigin = "50% 100%";
          l.style.transform = "rotate(" + (Math.sin(now / 1300 + phase) * 2.2).toFixed(2) + "deg)";
        } else if (motion === "bob") {
          l.style.transform = "translateY(" + (Math.sin(now / 850 + phase) * (travel || 4)).toFixed(1) + "px)";
        } else if (motion === "spin") {
          l.style.transformOrigin = "50% 50%";
          l.style.transform = "rotate(" + ((now / 18) % 360).toFixed(1) + "deg)";
        }
      });
    });
  }
