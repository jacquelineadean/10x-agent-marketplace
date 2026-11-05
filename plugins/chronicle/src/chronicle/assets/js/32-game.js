  /* ---------------------------------------------------------------- game */
  // Quizzes played as holes: each pick is a stroke, a wrong pick drops out, strokes
  // against par name the hole. One record per page in storage; the bar's flags and the
  // scorecard redraw after every pick.
  var GAME = { key: "", state: null, listeners: [], tally: null };

  function gameLoad(key) {
    if (GAME.state && GAME.key === key) return GAME.state;
    var found = null;
    try { found = JSON.parse(localStorage.getItem(key) || "null"); } catch (e) { found = null; }
    GAME.key = key;
    GAME.state = found && typeof found === "object" && found.holes ? found : { holes: {} };
    return GAME.state;
  }
  function gameSave() {
    try { localStorage.setItem(GAME.key, JSON.stringify(GAME.state)); } catch (e) { /* storage blocked: the round lasts this visit */ }
    GAME.listeners.forEach(function (fn) { fn(); });
  }
  function holeState(id) {
    var holes = GAME.state.holes;
    if (!holes[id]) holes[id] = { q: 0, strokes: 0, picks: {}, done: false };
    return holes[id];
  }
  function toPar(n) { return n === 0 ? "E" : (n > 0 ? "+" + n : "−" + Math.abs(n)); }
  function holeName(names, diff) { return names[String(diff)] || (diff > 0 ? "+" + diff : String(diff)); }
  function shuffled(list) {
    var out = list.slice();
    for (var i = out.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = out[i]; out[i] = out[j]; out[j] = t;
    }
    return out;
  }

  function initHole(node, spec) {
    gameLoad(spec.key);
    var id = spec.id;
    var questions = Array.prototype.slice.call(node.querySelectorAll(".hl-q"));
    var strokesEl = node.querySelector(".hl-strokes");
    var feedback = node.querySelector(".hl-feedback");
    var result = node.querySelector(".hl-result");
    // Options shuffle once per visit, so the right answer is never always the same letter.
    questions.forEach(function (li) {
      var list = li.querySelector(".hl-opts");
      shuffled(Array.prototype.slice.call(list.children)).forEach(function (item, k) {
        list.appendChild(item);
        item.querySelector(".hl-key").textContent = String.fromCharCode(65 + k);
      });
    });
    node.classList.add("live");

    function show(st) {
      strokesEl.textContent = String(st.strokes);
      node.classList.toggle("done", st.done);
      questions.forEach(function (li, i) {
        li.hidden = st.done || i !== st.q;
        var picks = st.picks[i] || [];
        li.querySelectorAll(".hl-opt").forEach(function (b) {
          var k = Number(b.getAttribute("data-k"));
          var picked = picks.indexOf(k) >= 0;
          b.classList.toggle("miss", picked && k !== spec.answers[i]);
          b.classList.toggle("hit", picked && k === spec.answers[i]);
          b.disabled = picked || i < st.q;
        });
        li.classList.toggle("answered", (st.picks[i] || []).indexOf(spec.answers[i]) >= 0);
      });
      result.hidden = !st.done;
      if (st.done) renderResult(st, false);
    }

    function renderResult(st, fresh) {
      var diff = st.strokes - spec.par;
      result.textContent = "";
      result.className = "hl-result " + (diff < 0 ? "under" : diff > 0 ? "over" : "even");
      var stamp = html("div", "hl-stamp", null, result);
      stamp.setAttribute("aria-hidden", "true");
      html("b", null, toPar(diff), stamp);
      html("span", null, "to par", stamp);
      var name = html("p", "hl-result-name", holeName(spec.names, diff), result);
      name.tabIndex = -1;
      html("p", "hl-result-line", st.strokes + " strokes on a par " + spec.par + ".", result);
      var misses = questions.filter(function (li, i) {
        return (st.picks[i] || []).some(function (k) { return k !== spec.answers[i]; });
      });
      if (misses.length) {
        html("p", "hl-review-h", "Where it went wrong", result);
        var list = html("ul", "hl-review", null, result);
        misses.forEach(function (li) {
          var i = Number(li.getAttribute("data-i"));
          var item = html("li", null, null, list);
          item.appendChild(li.querySelector(".hl-text").cloneNode(true)).removeAttribute("tabindex");
          var right = li.querySelector('.hl-opt[data-k="' + spec.answers[i] + '"] .hl-opt-text');
          if (right) html("p", "hl-right", right.textContent, item);
          item.appendChild(li.querySelector(".hl-explain").cloneNode(true));
        });
      }
      var row = html("div", "hl-actions", null, result);
      if (spec.next && spec.next.href) {
        var go = html("a", "hl-btn", spec.next.label, row);
        go.href = spec.next.href;
      }
      var again = html("button", "hl-btn ghost", "Replay hole", row);
      again.type = "button";
      again.addEventListener("click", function () {
        delete GAME.state.holes[id];
        gameSave();
        feedback.textContent = "";
        show(holeState(id));
        questions[0].querySelector(".hl-text").focus();
      });
      if (fresh) {
        node.classList.add("pop");
        feedback.textContent = "Hole " + spec.no + ": " + holeName(spec.names, diff) + ", " + st.strokes + " strokes on a par " + spec.par + ".";
        name.focus();
      }
    }

    questions.forEach(function (li, i) {
      li.querySelectorAll(".hl-opt").forEach(function (b) {
        b.addEventListener("click", function () {
          var st = holeState(id);
          if (st.done || i !== st.q || b.disabled) return;
          var k = Number(b.getAttribute("data-k"));
          st.strokes += 1;
          (st.picks[i] = st.picks[i] || []).push(k);
          if (k !== spec.answers[i]) {
            feedback.textContent = "Not this one. That was a stroke; pick again.";
            gameSave();
            show(st);
            return;
          }
          st.q = i + 1;
          st.done = st.q >= questions.length;
          gameSave();
          if (st.done) {
            show(st);
            renderResult(st, true);
            return;
          }
          feedback.textContent = "Right.";
          show(st);
          // The answered question stays in view with its explanation until the reader moves on.
          li.hidden = false;
          li.querySelectorAll(".hl-opt").forEach(function (o) { o.disabled = true; });
          questions[i + 1].hidden = true;
          var next = html("button", "hl-btn hl-next", "Next question", li);
          next.type = "button";
          next.addEventListener("click", function () {
            next.remove();
            feedback.textContent = "";
            show(holeState(id));
            questions[i + 1].querySelector(".hl-text").focus();
          });
          next.focus();
        });
      });
    });

    show(holeState(id));
    gameTally();
  }

  function gameTally() {
    if (GAME.tally) return;
    var bar = doc.querySelector(".spanbar-in");
    var holes = Array.prototype.slice.call(doc.querySelectorAll(".hole[data-fig]"));
    if (!bar || !holes.length) return;
    var box = html("div", "tally", null, null);
    var track = bar.querySelector(".spanbar-track");
    bar.insertBefore(box, track ? track.nextSibling : null);
    bar.parentNode.classList.add("has-tally");
    var flags = holes.map(function (sec) {
      var spec = FIGS[sec.getAttribute("data-fig")] || {};
      var b = html("button", "tally-flag", null, box);
      b.type = "button";
      var s = svg("svg", { viewBox: "0 0 20 34", "aria-hidden": "true" }, b);
      svg("ellipse", { "class": "cup", cx: 6, cy: 31, rx: 5, ry: 1.8 }, s);
      svg("line", { "class": "pole", x1: 6, y1: 31, x2: 6, y2: 5 }, s);
      svg("path", { "class": "cloth", d: "M6.6 5 l11 4 l-11 4 Z" }, s);
      b.addEventListener("click", function () { sec.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" }); });
      return { button: b, spec: spec };
    });
    var card = doc.querySelector(".scorecard[data-fig]");
    if (card) {
      var c = html("button", "tally-card", null, box);
      c.type = "button";
      c.setAttribute("aria-label", "Scorecard");
      var cs = svg("svg", { viewBox: "0 0 22 34", "aria-hidden": "true" }, c);
      svg("rect", { x: 3, y: 7, width: 16, height: 22, rx: 2 }, cs);
      svg("line", { x1: 6, y1: 14, x2: 16, y2: 14 }, cs);
      svg("line", { x1: 6, y1: 19, x2: 16, y2: 19 }, cs);
      svg("line", { x1: 6, y1: 24, x2: 12, y2: 24 }, cs);
      c.addEventListener("click", function () { card.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" }); });
    }
    function paint() {
      flags.forEach(function (f) {
        var st = GAME.state.holes[f.spec.id];
        var cls = "tally-flag", said = "not played";
        if (st && st.done) {
          var diff = st.strokes - f.spec.par;
          cls += diff < 0 ? " under" : diff > 0 ? " over" : " even";
          said = holeName(f.spec.names || {}, diff);
        } else if (st && st.strokes) {
          cls += " started";
          said = "in progress";
        }
        f.button.className = cls;
        f.button.setAttribute("aria-label", "Hole " + f.spec.no + ", par " + f.spec.par + ", " + said);
        f.button.title = f.button.getAttribute("aria-label");
      });
    }
    GAME.tally = paint;
    GAME.listeners.push(paint);
    paint();
  }

  function initScorecard(node, spec) {
    gameLoad(spec.key);
    var table = node.querySelector(".sc-table");
    var cells = Array.prototype.slice.call(table.querySelectorAll("tbody tr:last-child td"));
    var heads = Array.prototype.slice.call(table.querySelectorAll("thead th")).slice(1, -1);
    var summary = node.querySelector(".sc-summary");
    heads.forEach(function (th, i) {
      var row = spec.holes[i];
      var b = html("button", null, th.textContent, null);
      b.type = "button";
      b.setAttribute("aria-label", "Go to hole " + row.no + ", " + row.title);
      th.textContent = "";
      th.appendChild(b);
      b.addEventListener("click", function () {
        var target = doc.getElementById(row.id);
        if (target) target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
      });
    });
    var armed = null;
    function render() {
      var played = 0, playedPar = 0, strokes = 0, under = 0, even = 0, over = 0;
      spec.holes.forEach(function (row, i) {
        var st = GAME.state.holes[row.id];
        var cell = cells[i];
        cell.textContent = "";
        if (st && st.done) {
          var diff = st.strokes - row.par;
          var mark = html("span", "sc-mark " + (diff <= -2 ? "under2" : diff === -1 ? "under" : diff === 0 ? "even" : diff === 1 ? "over" : "over2"), String(st.strokes), cell);
          mark.title = holeName(spec.names, diff);
          played += 1; playedPar += row.par; strokes += st.strokes;
          if (diff < 0) under += 1; else if (diff > 0) over += 1; else even += 1;
        } else {
          cell.textContent = st && st.strokes ? "…" : "–";
        }
      });
      cells[cells.length - 1].textContent = played ? String(strokes) : "–";
      summary.textContent = "";
      html("p", "sc-big", played ? toPar(strokes - playedPar) : "E", summary);
      var words = played === spec.holes.length
        ? "Round complete: " + strokes + " strokes on a par " + spec.holes.reduce(function (s, r) { return s + r.par; }, 0) + "."
        : played ? "Through " + played + " of " + spec.holes.length + " holes: " + strokes + " strokes."
          : "No holes played yet. Your card fills in as you play.";
      html("p", "sc-words", words + (played ? " " + under + " under par, " + even + " at par, " + over + " over." : ""), summary);
      if (played) {
        var reset = html("button", "hl-btn ghost", "Start a new round", summary);
        reset.type = "button";
        reset.addEventListener("click", function () {
          if (armed) {
            clearTimeout(armed);
            armed = null;
            GAME.state.holes = {};
            gameSave();
            location.reload();
            return;
          }
          reset.textContent = "Tap again to clear every hole";
          armed = setTimeout(function () { armed = null; reset.textContent = "Start a new round"; }, 4000);
        });
      }
    }
    GAME.listeners.push(render);
    render();
    gameTally();
  }

  INIT.hole = initHole;
  INIT.scorecard = initScorecard;
