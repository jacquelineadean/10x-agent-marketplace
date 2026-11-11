  /* -------------------------------------------------------- solutions: page */
  /* A reader picks a scenario or moves inputs, changes each variant's settings, turns
     variants and optional settings on and off, adds variants and scenarios, and copies the
     decision. Controls are built when the structure changes; moving one repaints numbers. */
  function initSolutions(node, spec) {
    var app = node.querySelector(".sol-app");
    var fallback = node.querySelector(".sol-static");
    if (!app) return;
    var uid = node.getAttribute("data-fig");
    var seq = 0;
    var state = {
      scenarios: spec.scenarios.slice(),
      scenario: spec.scenarios[0].id,
      inputs: solInputs(spec, spec.scenarios[0]),
      variants: spec.approaches.map(function (a) { return solVariant(spec, a, a.id, a.label); }),
      chosen: "",
      measure: spec.measures[0].id
    };
    var painters = [], cardPainters = [];
    /* One pass computes every variant at the inputs as they stand, the bar scale of each
       measure across the compared variants and the best of them; every part reads it. */
    function paint() {
      var live = state.variants.filter(function (v) { return v.on; });
      var f = { live: live, by: {}, scale: {}, best: {} };
      state.variants.forEach(function (v) { f.by[v.id] = solMeasure(spec, v, state.inputs); });
      spec.measures.forEach(function (m) {
        var top = m.budget !== null ? Math.abs(m.budget) : 0, pick = null;
        live.forEach(function (v) {
          var r = f.by[v.id];
          if (r.error) return;
          top = Math.max(top, Math.abs(r[m.id]));
          if (pick === null || (m.better === "higher" ? r[m.id] > f.by[pick][m.id] : r[m.id] < f.by[pick][m.id])) pick = v.id;
        });
        f.scale[m.id] = top || 1;
        f.best[m.id] = live.length > 1 ? pick : null;
      });
      painters.concat(cardPainters).forEach(function (fn) { fn(f); });
    }
    function button(parent, cls, text, onClick) {
      var b = html("button", cls, text, parent);
      b.type = "button";
      b.addEventListener("click", onClick);
      return b;
    }
    function check(parent, text, on, onChange) {
      var lab = html("label", "sol-check", null, parent);
      var box = html("input", null, null, lab);
      box.type = "checkbox";
      box.checked = on;
      html("span", null, text, lab);
      box.addEventListener("change", function () { onChange(box.checked); });
      return box;
    }
    /* A slider, a switch or a choice for one input or setting. */
    function control(parent, item, get, set) {
      var id = uid + "-c" + (seq += 1);
      var wrap = html("div", "ctl", null, parent);
      var lab = html("label", null, null, wrap);
      lab.setAttribute("for", id);
      html("span", null, item.label, lab);
      var input, out = null;
      if (item.kind === "toggle") {
        input = html("input", null, null, lab);
        input.type = "checkbox";
        input.addEventListener("change", function () { set(input.checked ? 1 : 0); });
      } else if (item.kind === "choice") {
        input = html("select", null, null, wrap);
        item.options.forEach(function (o) { html("option", null, o.label, input).value = String(o.value); });
        input.addEventListener("change", function () { set(Number(input.value)); });
      } else {
        out = html("output", null, null, lab);
        out.setAttribute("for", id);
        input = html("input", null, null, wrap);
        input.type = "range"; input.min = item.min; input.max = item.max; input.step = item.step;
        input.addEventListener("input", function () { out.textContent = solShow(Number(input.value), item); set(Number(input.value)); });
      }
      input.id = id;
      function refresh() {
        if (item.kind === "toggle") input.checked = !!get(); else input.value = String(get());
        if (out) out.textContent = solShow(get(), item);
      }
      refresh();
      return { wrap: wrap, input: input, refresh: refresh };
    }

    /* Left: scenarios and inputs, kept in view while the reader scrolls the rest. */
    var side = html("aside", "sol-side", null, app);
    html("h4", "sol-h", "Scenario", side);
    var chips = html("div", "sol-chips", null, side);
    chips.setAttribute("role", "group");
    chips.setAttribute("aria-label", "Scenario");
    var chipOf = {};
    var about = html("p", "sol-about", null, side);
    html("h4", "sol-h", "Inputs", side);
    var inputCtls = spec.inputs.map(function (c) {
      var ctl = control(side, c, function () { return state.inputs[c.id]; }, function (v) { state.inputs[c.id] = v; state.scenario = ""; paint(); });
      html("p", "hint", (c.source ? (SOURCES[c.source] || {}).label || c.source : "Assumption") + (c.note ? ": " + c.note : ""), ctl.wrap);
      return ctl;
    });
    var save = html("div", "sol-save", null, side);
    var nameBox = html("input", null, null, save);
    nameBox.type = "text"; nameBox.maxLength = 40; nameBox.placeholder = "Name these inputs";
    nameBox.setAttribute("aria-label", "Name for a scenario of these inputs");
    button(save, null, "Save as a scenario", function () {
      var copy = {};
      Object.keys(state.inputs).forEach(function (k) { copy[k] = state.inputs[k]; });
      var id = "saved_" + (seq += 1);
      state.scenarios.push({ id: id, label: nameBox.value.trim() || "Saved scenario", text: "", inputs: copy, added: true });
      state.scenario = id;
      nameBox.value = "";
      drawChips();
      paint();
    });
    function drawChips() {
      solClear(chips);
      chipOf = {};
      state.scenarios.forEach(function (sc) {
        chipOf[sc.id] = button(chips, "sol-chip", sc.label, function () {
          state.scenario = sc.id;
          state.inputs = solInputs(spec, sc);
          inputCtls.forEach(function (c) { c.refresh(); });
          paint();
        });
        if (!sc.added) return;
        button(chips, "sol-x", "×", function () {
          state.scenarios = state.scenarios.filter(function (s) { return s !== sc; });
          if (state.scenario === sc.id) state.scenario = "";
          drawChips();
          paint();
        }).setAttribute("aria-label", "Remove the scenario " + sc.label);
      });
    }
    painters.push(function () {
      var now = null;
      state.scenarios.forEach(function (sc) {
        chipOf[sc.id].setAttribute("aria-pressed", sc.id === state.scenario ? "true" : "false");
        if (sc.id === state.scenario) now = sc;
      });
      about.textContent = now ? now.text : "Inputs moved by hand. Save them as a scenario to compare it with the others.";
    });

    /* Right: one card per variant, then the scenario table, the feel panels and the decision. */
    var main = html("div", "sol-main", null, app);
    var cards = html("section", "sol-cards", null, main);
    function drawCards() {
      solClear(cards);
      cardPainters = [];
      state.variants.forEach(card);
    }
    function card(v) {
      var box = html("article", "sol-card", null, cards);
      var head = html("header", "sol-card-head", null, box);
      if (v.added) {
        var name = html("input", "sol-name", null, head);
        name.type = "text"; name.maxLength = 40; name.value = v.label;
        name.setAttribute("aria-label", "Variant name");
        name.addEventListener("input", function () { v.label = name.value; paint(); });
      } else {
        html("h4", "sol-name", v.label, head);
      }
      var flags = html("div", "sol-flags", null, head);
      check(flags, "Compare", v.on, function (on) { v.on = on; paint(); });
      var choose = button(flags, "sol-choose", "Choose", function () { state.chosen = state.chosen === v.id ? "" : v.id; paint(); });
      html("p", "sol-text", v.added ? "A variant of " + v.approach.label + "." : v.approach.text, box);
      var list = html("dl", "sol-measures", null, box);
      var rows = spec.measures.map(function (m) {
        var row = html("div", "sol-m", null, list);
        html("dt", null, m.label, row);
        var dd = html("dd", null, null, row);
        var note = html("span", "sol-tag", null, dd);
        var val = html("b", null, null, dd);
        var bar = html("span", "sol-bar", null, row);
        return { m: m, row: row, val: val, note: note, fill: html("i", null, null, bar), mark: m.budget === null ? null : html("u", null, null, bar) };
      });
      var problem = html("p", "sol-err", null, box);
      var own = solSettings(spec, v.approach);
      if (own.length) {
        var set = html("details", "sol-settings", null, box);
        set.open = true;
        html("summary", null, "Settings", set);
        own.forEach(function (c) {
          var ctl = control(set, c, function () { return v.settings[c.id]; }, function (value) { v.settings[c.id] = value; paint(); });
          if (c.off === null) return;
          ctl.input.disabled = !!v.off[c.id];
          check(ctl.wrap, "On", !v.off[c.id], function (on) { v.off[c.id] = !on; ctl.input.disabled = !on; paint(); });
        });
      }
      var foot = html("footer", "sol-card-foot", null, box);
      var add = button(foot, null, "Add a variant", function () {
        var copy = solVariant(spec, v.approach, v.approach.id + "_" + (seq += 1), v.label + " variant");
        Object.keys(v.settings).forEach(function (k) { copy.settings[k] = v.settings[k]; });
        Object.keys(v.off).forEach(function (k) { copy.off[k] = v.off[k]; });
        copy.added = true;
        state.variants.splice(state.variants.indexOf(v) + 1, 0, copy);
        drawCards();
        paint();
      });
      if (v.added) button(foot, null, "Remove", function () {
        state.variants = state.variants.filter(function (o) { return o !== v; });
        if (state.chosen === v.id) state.chosen = "";
        drawCards();
        paint();
      });
      cardPainters.push(function (f) {
        var r = f.by[v.id], picked = state.chosen === v.id;
        box.className = "sol-card" + (v.on ? "" : " off") + (picked ? " chosen" : "");
        choose.setAttribute("aria-pressed", picked ? "true" : "false");
        choose.textContent = picked ? "Chosen" : "Choose";
        add.disabled = state.variants.length >= spec.most_variants;
        problem.hidden = !r.error;
        problem.textContent = r.error ? "Cannot compute: " + r.error : "";
        rows.forEach(function (row) {
          var m = row.m, value = r.error ? null : r[m.id], ok = r.error ? null : solMet(m, value);
          row.val.textContent = solShow(value, m);
          row.row.className = "sol-m" + (ok === null ? "" : ok ? " ok" : " miss");
          row.note.textContent = ok === false ? (m.better === "higher" ? "under budget" : "over budget") : (v.on && f.best[m.id] === v.id ? "best" : "");
          row.fill.style.width = (r.error ? 0 : clamp(Math.abs(value) / f.scale[m.id] * 100, 0, 100)) + "%";
          if (row.mark) row.mark.style.left = clamp(Math.abs(m.budget) / f.scale[m.id] * 100, 0, 100) + "%";
        });
      });
    }

    var across = html("section", "sol-across", null, main);
    html("h4", "sol-h", "Across scenarios", across);
    var seg = html("div", "seg", null, across);
    var segOf = {};
    spec.measures.forEach(function (m) { segOf[m.id] = button(seg, null, m.label, function () { state.measure = m.id; paint(); }); });
    seg.hidden = spec.measures.length < 2;
    var table = html("table", null, null, html("div", "table-scroll", null, across));
    painters.push(function (f) {
      var m = spec.measures.filter(function (o) { return o.id === state.measure; })[0];
      spec.measures.forEach(function (o) { segOf[o.id].setAttribute("aria-pressed", o === m ? "true" : "false"); });
      var cols = state.scenarios.map(function (sc) { return { label: sc.label, inputs: solInputs(spec, sc), now: sc.id === state.scenario }; });
      if (!state.scenario) cols.push({ label: "Inputs by hand", inputs: state.inputs, now: true });
      solClear(table);
      var top = html("tr", null, null, html("thead", null, null, table));
      html("th", null, m.label + (m.budget === null ? "" : ", budget " + solShow(m.budget, m)), top).scope = "col";
      cols.forEach(function (c) { html("th", c.now ? "now" : null, c.label, top).scope = "col"; });
      var body = html("tbody", null, null, table);
      f.live.forEach(function (v) {
        var tr = html("tr", null, null, body);
        html("th", null, v.label, tr).scope = "row";
        cols.forEach(function (c) {
          var r = solMeasure(spec, v, c.inputs), ok = r.error ? null : solMet(m, r[m.id]);
          html("td", (c.now ? "now" : "") + (ok === null ? "" : ok ? " ok" : " miss"), r.error ? "n/a" : solShow(r[m.id], m), tr);
        });
      });
    });

    solFeel(main, spec, painters);

    var decide = html("section", "sol-decide", null, main);
    html("h4", "sol-h", "Decision", decide);
    var line = html("p", "sol-line", null, decide);
    line.setAttribute("aria-live", "polite");
    var status = html("span", "sol-status", null, null);
    status.setAttribute("role", "status");
    var json = html("textarea", "sol-json", null, null);
    json.readOnly = true; json.rows = 8; json.hidden = true;
    json.setAttribute("aria-label", "The decision as JSON");
    var copy = button(decide, "sol-copy", "Copy the decision", function () {
      var text = JSON.stringify(solDecision(spec, state), null, 1);
      json.value = text;
      json.hidden = false;
      json.select();
      function done(ok) { status.textContent = ok ? "Copied. Paste it to Claude or save it as decision.json." : "Copy the selected text and save it as decision.json."; }
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      else done(false);
    });
    decide.appendChild(status);
    decide.appendChild(json);
    painters.push(function () {
      var v = state.variants.filter(function (o) { return o.id === state.chosen; })[0];
      copy.disabled = !v;
      /* A copy made before the last change no longer matches the page, so it goes. */
      json.hidden = true;
      status.textContent = "";
      line.textContent = v ? "Chosen: " + v.label + solSettings(spec, v.approach).map(function (c) {
        return ", " + c.label + " " + (v.off[c.id] ? "turned off" : solSettingText(c, v.settings[c.id]));
      }).join("") + "." : "Choose a variant to export its settings for the implementation.";
    });

    var drift = solDrift(spec);
    if (drift.length) html("p", "fig-note sol-drift", "This page's simulator and its build disagree for " + drift[0] + (drift.length > 1 ? " and " + (drift.length - 1) + " more" : "") + ". Rebuild the page.", app);
    app.hidden = false;
    if (fallback) fallback.hidden = true;
    drawChips();
    drawCards();
    paint();
  }
  INIT.solutions = initSolutions;
