  /* ----------------------------------------------------------- architecture */
  /* A built animation made explorable: parts open their details, numbered pins mark
     decisions, and a player steps through the animation's own steps on its one clock. */
  INIT.architecture = function (node, spec) {
    var svg = node.querySelector(".arch-svg svg");
    if (!svg) return;
    var slug = ((svg.getAttribute("class") || "").match(/chr-a-([a-z0-9-]+)/) || [])[1] || "";
    var stage = node.querySelector(".arch-stage");
    var layer = node.querySelector(".arch-pins");
    var detail = node.querySelector(".arch-detail");
    var current = null;
    function partEl(id) {
      var kinds = ["n", "g", "e", "d"];
      for (var i = 0; i < kinds.length; i++) {
        var el = doc.getElementById(slug + "-" + kinds[i] + "-" + id);
        if (el) return el;
      }
      return null;
    }
    function say(title, text, el) {
      while (detail.firstChild) detail.removeChild(detail.firstChild);
      html("h4", "arch-title", title, detail);
      if (text) html("p", null, text, detail);
      if (current) current.classList.remove("arch-on");
      current = el || null;
      if (current) current.classList.add("arch-on");
    }
    Object.keys(spec.parts || {}).forEach(function (id) {
      var el = partEl(id), p = spec.parts[id];
      if (!el) return;
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "button");
      el.setAttribute("aria-label", p.title);
      el.classList.add("arch-part");
      function open() { say(p.title, p.text, el); }
      el.addEventListener("click", open);
      el.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } });
    });
    var pins = (spec.pins || []).map(function (p, k) {
      var btn = html("button", "arch-pin", String(k + 1), layer);
      btn.type = "button";
      btn.setAttribute("aria-label", "Pin " + (k + 1) + ": " + p.title);
      btn.addEventListener("click", function () { say((k + 1) + ". " + p.title, p.text, partEl(p.part)); });
      return { btn: btn, part: p.part };
    });
    function place() {
      var box = stage.getBoundingClientRect();
      pins.forEach(function (p) {
        var el = partEl(p.part);
        if (!el) { p.btn.hidden = true; return; }
        var r = el.getBoundingClientRect();
        p.btn.style.left = (r.right - box.left - 10) + "px";
        p.btn.style.top = (r.top - box.top - 10) + "px";
      });
    }
    place();
    if (window.ResizeObserver) new ResizeObserver(place).observe(stage);
    window.addEventListener("load", place);

    if (spec.player === false || !svg.getAttribute("data-steps") || !svg.getAnimations) return;
    var starts = svg.getAttribute("data-steps").split(",").map(Number);
    var end = Number(svg.getAttribute("data-end")) || starts[starts.length - 1];
    var bar = node.querySelector(".arch-player");
    var playBtn = html("button", "arch-play", word("pause", "Pause"), bar);
    playBtn.type = "button";
    var list = html("ol", "arch-steps", null, bar);
    var at = -1, playing = !reduceMotion;
    function seek(t) { svg.getAnimations({ subtree: true }).forEach(function (a) { a.pause(); a.currentTime = t * 1000; }); }
    function mark(k) {
      at = k;
      Array.prototype.forEach.call(list.children, function (li, i) { li.firstChild.setAttribute("aria-current", i === k ? "step" : "false"); });
    }
    starts.forEach(function (s, k) {
      var cap = doc.getElementById(slug + "-cap-" + k);
      var li = html("li", null, null, list);
      // The caption group starts with its step number; the list numbers steps itself.
      var said = cap ? cap.textContent.replace(/\s+/g, " ").trim().replace(/^\d+\s*/, "") : "";
      var b = html("button", "arch-step", said || "Step " + (k + 1), li);
      b.type = "button";
      b.addEventListener("click", function () {
        playing = false;
        playBtn.textContent = word("play", "Play");
        seek(k + 1 < starts.length ? starts[k + 1] - 0.05 : end);
        mark(k);
      });
    });
    playBtn.addEventListener("click", function () {
      playing = !playing;
      playBtn.textContent = playing ? word("pause", "Pause") : word("play", "Play");
      svg.getAnimations({ subtree: true }).forEach(function (a) { if (playing) a.play(); else a.pause(); });
    });
    if (!playing) { seek(end); playBtn.textContent = word("play", "Play"); }
    tickers.push(function () {
      if (!playing) return;
      var anims = svg.getAnimations({ subtree: true });
      if (!anims.length) return;
      var t = (anims[0].currentTime || 0) / 1000 % (Number(svg.getAttribute("data-duration")) || 1e9);
      var k = -1;
      starts.forEach(function (s, i) { if (t >= s) k = i; });
      if (k !== at) mark(k);
    });
  };
