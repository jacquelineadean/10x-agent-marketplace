  /* -------------------------------------------------------------- prototype */
  /* Tabs switch screens; a card or row with a link opens its screen; rows without one open
     their text; the device toggle sets the frame's width. The hash names the screen. */
  var proto = (function () {
    var frame = doc.querySelector(".proto-frame");
    if (!frame) return null;
    var tabs = Array.prototype.slice.call(frame.querySelectorAll(".proto-tab"));
    var screens = Array.prototype.slice.call(frame.querySelectorAll(".proto-screen"));
    function show(id, focus) {
      var found = screens.some(function (s) { return s.id === id; });
      if (!found) return;
      screens.forEach(function (s) { s.hidden = s.id !== id; });
      tabs.forEach(function (t) {
        var on = t.getAttribute("aria-controls") === id;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        if (on && focus) t.focus();
      });
      try { history.replaceState(null, "", "#" + id); } catch (e) { /* sandboxed frame: the hash stays */ }
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { show(t.getAttribute("aria-controls"), false); });
      t.addEventListener("keydown", function (ev) {
        var step = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
        if (!step) return;
        ev.preventDefault();
        var next = tabs[(i + step + tabs.length) % tabs.length];
        show(next.getAttribute("aria-controls"), true);
      });
    });
    frame.querySelectorAll(".proto-device").forEach(function (b) {
      b.addEventListener("click", function () {
        frame.setAttribute("data-device", b.getAttribute("data-device"));
        frame.querySelectorAll(".proto-device").forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
      });
    });
    var start = location.hash.slice(1);
    show(screens.some(function (s) { return s.id === start; }) ? start : (screens[0] && screens[0].id), false);
    return { show: show };
  })();
  function follow(node) {
    node.querySelectorAll("[data-link]").forEach(function (el) {
      el.addEventListener("click", function () {
        var id = el.getAttribute("data-link");
        if (proto) { proto.show(id, true); return; }
        var target = doc.getElementById(id);
        if (target) target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
      });
    });
  }
  INIT.cards = follow;
  INIT.list = function (node) {
    follow(node);
    node.querySelectorAll(".plist-row[aria-controls]").forEach(function (row) {
      row.addEventListener("click", function () {
        var open = row.getAttribute("aria-expanded") === "true";
        row.setAttribute("aria-expanded", open ? "false" : "true");
        var more = doc.getElementById(row.getAttribute("aria-controls"));
        if (more) more.hidden = open;
      });
    });
  };
