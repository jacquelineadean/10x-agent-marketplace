  /* ------------------------------------------------------------------ quiz */
  /* One question at a time. A choice locks the question, marks the right answer and
     shows why; the last question gives a score and a line for that score. */
  var STORE = {
    get: function (key) { try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : null; } catch (e) { return null; } },
    set: function (key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* storage blocked: the state lasts this visit */ } }
  };

  function initQuiz(node, spec) {
    var qs = Array.prototype.slice.call(node.querySelectorAll(".qz-q"));
    var result = node.querySelector(".qz-result");
    var answers = spec.answers || [];
    var at = 0, score = 0, answered = [];
    node.classList.add("live");
    var bar = html("div", "qz-progress", null, null);
    node.insertBefore(bar, node.querySelector(".qz-list"));
    var count = html("p", "qz-count", null, bar);
    var pips = html("div", "qz-pips", null, bar);
    qs.forEach(function () { html("i", null, null, pips); });
    function pipState() {
      Array.prototype.forEach.call(pips.children, function (p, i) {
        p.className = answered[i] === undefined ? (i === at ? "now" : "") : (answered[i] ? "hit" : "miss");
      });
    }
    function show(i) {
      at = i;
      qs.forEach(function (q, k) { q.classList.toggle("on", k === i); });
      count.textContent = word("question", "Question") + " " + (i + 1) + " " + word("of", "of") + " " + qs.length;
      bar.hidden = false;
      result.hidden = true;
      pipState();
    }
    qs.forEach(function (q, qi) {
      var opts = Array.prototype.slice.call(q.querySelectorAll(".qz-opt"));
      var explain = q.querySelector(".qz-explain");
      var nextBtn = html("button", "qz-next btn", qi === qs.length - 1 ? word("see_score", "See your score") : word("next_question", "Next question"), null);
      nextBtn.type = "button";
      nextBtn.hidden = true;
      q.appendChild(nextBtn);
      opts.forEach(function (o) {
        o.addEventListener("click", function () {
          if (answered[qi] !== undefined) return;
          var k = Number(o.getAttribute("data-k"));
          var right = k === answers[qi];
          answered[qi] = right;
          if (right) score += 1;
          opts.forEach(function (x) {
            var xk = Number(x.getAttribute("data-k"));
            x.disabled = true;
            if (xk === answers[qi]) x.classList.add("hit");
            else if (x === o) x.classList.add("miss");
          });
          if (!right && !reduceMotion) { o.classList.add("shake"); setTimeout(function () { o.classList.remove("shake"); }, 400); }
          q.classList.add(right ? "got" : "missed");
          if (explain) explain.classList.add("on");
          nextBtn.hidden = false;
          nextBtn.focus({ preventScroll: true });
          pipState();
        });
      });
      nextBtn.addEventListener("click", function () {
        if (qi < qs.length - 1) { show(qi + 1); qs[qi + 1].querySelector(".qz-opt").focus({ preventScroll: true }); }
        else finish();
      });
    });
    function finish() {
      qs.forEach(function (q) { q.classList.remove("on"); });
      bar.hidden = true;
      while (result.firstChild) result.removeChild(result.firstChild);
      var share = qs.length ? score / qs.length : 0;
      var pick = null;
      (spec.results || []).forEach(function (r) { if (share >= r.min && (!pick || r.min >= pick.min)) pick = r; });
      var stamp = html("div", "qz-stamp", null, result);
      html("b", null, score + "/" + qs.length, stamp);
      html("span", null, pick ? pick.label : word("score", "Score"), stamp);
      var body = html("div", "qz-result-body", null, result);
      html("p", "qz-result-h", pick ? pick.label : "Done", body);
      if (pick && pick.text) html("p", "qz-result-text", pick.text, body);
      var again = html("button", "btn ghost", word("try_again", "Try again"), body);
      again.type = "button";
      again.addEventListener("click", reset);
      result.hidden = false;
      result.classList.toggle("perfect", score === qs.length);
    }
    function reset() {
      score = 0; answered = [];
      qs.forEach(function (q) {
        q.classList.remove("got", "missed");
        var ex = q.querySelector(".qz-explain"); if (ex) ex.classList.remove("on");
        q.querySelector(".qz-next").hidden = true;
        Array.prototype.forEach.call(q.querySelectorAll(".qz-opt"), function (x) { x.disabled = false; x.classList.remove("hit", "miss"); });
      });
      show(0);
    }
    show(0);
  }

  /* ------------------------------------------------------------- checklist */
  function initChecklist(node, spec) {
    var boxes = Array.prototype.slice.call(node.querySelectorAll('input[type="checkbox"]'));
    var count = node.querySelector(".ck-count"), fill = node.querySelector(".ck-fill");
    var key = "chronicle-checklist:" + (doc.title || "") + ":" + (spec.key || "");
    var saved = STORE.get(key) || [];
    boxes.forEach(function (b) { b.checked = saved.indexOf(Number(b.getAttribute("data-k"))) >= 0; });
    function update() {
      var done = boxes.filter(function (b) { return b.checked; });
      if (count) count.textContent = done.length + " " + word("of", "of") + " " + boxes.length + " " + word("done", "done");
      if (fill) fill.style.width = (boxes.length ? done.length / boxes.length * 100 : 0) + "%";
      node.classList.toggle("complete", done.length === boxes.length && boxes.length > 0);
      boxes.forEach(function (b) { b.closest("li").classList.toggle("done", b.checked); });
      STORE.set(key, done.map(function (b) { return Number(b.getAttribute("data-k")); }));
    }
    boxes.forEach(function (b) { b.addEventListener("change", update); });
    update();
  }

  /* ---------------------------------------------------------------- widgets */
  /* A widget is a script written for one page. It gets its root element, its data and
     this kit, so it draws in the page's style without reaching outside the page. */
  var KIT = {
    svg: svg, html: html, text: txt, clamp: clamp, ease: ease, linear: linear, ticks: ticks,
    fmt: fmt, fmtDate: fmtDate, parseDate: parseDate, label: labelX, color: colorOf,
    icon: drawIcon, word: word, reduceMotion: reduceMotion, store: STORE,
    tip: { show: showTip, hide: hideTip, at: pointerXY },
    onScroll: function (fn) { scrollers.push(fn); },
    onFrame: function (fn) { plates.push(fn); },
    chart: function (mountNode, chartSpec) { return mountChart(null, chartSpec, mountNode, {}); }
  };
  function initWidget(node, spec) {
    var registry = window.chronicleWidgets || {};
    var fn = registry[spec.name];
    var root = node.querySelector(".widget-root");
    if (typeof fn !== "function" || !root) return;
    if (spec.height) root.style.minHeight = Number(spec.height) + "px";
    fn(root, spec.data || {}, KIT);
    var fallback = node.querySelector(".widget-fallback");
    if (fallback) fallback.hidden = true;
  }
