  /* ---------------------------------------------------------------- rooms */
  // Painted rooms walked through doorways. One room shows at a time: a doorway pushes the
  // view through the door while the next room develops from gray, and focus moves to the
  // new room's name. A numbered dot opens its detail in the caption under the painting.
  function initRooms(node) {
    var rooms = Array.prototype.slice.call(node.querySelectorAll(".rm-room"));
    var tabs = Array.prototype.slice.call(node.querySelectorAll(".rm-tabs [role=tab]"));
    var cur = 0, busy = false;
    node.classList.add("live");

    function fit(room) {
      // On a phone the painting is wider than the frame; start where the room says.
      var frame = room.querySelector(".frame");
      if (frame && frame.scrollWidth > frame.clientWidth) {
        frame.scrollLeft = (frame.scrollWidth - frame.clientWidth) * Number(room.getAttribute("data-focus") || 0.5);
      }
    }
    function close(room) {
      room.querySelectorAll(".rm-dot.on").forEach(function (d) { d.classList.remove("on"); });
      room.querySelector(".rm-about").hidden = false;
      room.querySelectorAll(".rm-details > li").forEach(function (li) { li.hidden = true; });
      var back = room.querySelector(".rm-back");
      if (back) back.hidden = true;
    }
    function go(i, origin, viaTab) {
      if (busy || i === cur || !rooms[i]) return;
      var from = rooms[cur], to = rooms[i];
      close(from);
      tabs.forEach(function (t, k) {
        t.setAttribute("aria-selected", k === i ? "true" : "false");
        t.tabIndex = k === i ? 0 : -1;
      });
      cur = i;
      to.hidden = false;
      fit(to);
      if (reduceMotion) from.hidden = true;
      else {
        busy = true;
        from.style.transformOrigin = origin || "50% 40%";
        from.classList.add("rm-leave");
        to.classList.add("rm-enter");
        requestAnimationFrame(function () { requestAnimationFrame(function () { to.classList.remove("rm-enter"); }); });
        setTimeout(function () { from.hidden = true; from.classList.remove("rm-leave"); busy = false; }, 900);
      }
      if (viaTab) tabs[i].focus();
      else to.querySelector(".rm-title").focus({ preventScroll: true });
    }

    rooms.forEach(function (room, i) {
      room.hidden = i !== 0;
      var dots = Array.prototype.slice.call(room.querySelectorAll(".rm-dot"));
      var items = Array.prototype.slice.call(room.querySelectorAll(".rm-details > li"));
      var cap = room.querySelector(".rm-cap");
      var back = html("button", "rm-back", "Back to the room", cap);
      back.type = "button";
      var opened = null;
      close(room);
      dots.forEach(function (dot) {
        dot.addEventListener("click", function (e) {
          e.preventDefault();
          var k = Number(dot.getAttribute("data-k"));
          dots.forEach(function (d) { d.classList.toggle("on", d === dot); });
          room.querySelector(".rm-about").hidden = true;
          items.forEach(function (li, j) { li.hidden = j !== k; });
          back.hidden = false;
          opened = dot;
        });
      });
      back.addEventListener("click", function () {
        close(room);
        if (opened) opened.focus();
      });
      room.querySelectorAll(".rm-exit").forEach(function (door) {
        door.addEventListener("click", function (e) {
          e.preventDefault();
          var at = (door.getAttribute("data-at") || "50 40").split(" ");
          var box = room.querySelector(".stage").getBoundingClientRect(), whole = room.getBoundingClientRect();
          var x = box.left - whole.left + box.width * Number(at[0]) / 100;
          var y = box.top - whole.top + box.height * Number(at[1]) / 100;
          go(Number(door.getAttribute("data-to")), x.toFixed(0) + "px " + y.toFixed(0) + "px", false);
        });
      });
    });
    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { go(i, null, true); });
      tab.addEventListener("keydown", function (e) {
        var to = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
        if (to === undefined) return;
        e.preventDefault();
        go((to + tabs.length) % tabs.length, null, true);
      });
    });
    fit(rooms[0]);
  }
  INIT.rooms = initRooms;
