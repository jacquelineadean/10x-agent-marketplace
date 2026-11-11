  /* ------------------------------------------------------- solutions: model */
  /* The build reads each formula into a tree of [operation, argument, ...]. This walks
     the tree by the rules of the build's reader (formula.py), so the page and the build
     compute one number. A step that is not a finite number throws, as it raises there. */
  function solFail(why) { throw new Error(why); }
  var SOL_OPS = {
    add: function (a, b) { return a + b; },
    sub: function (a, b) { return a - b; },
    mul: function (a, b) { return a * b; },
    div: function (a, b) { return b === 0 ? solFail("division by zero") : a / b; },
    mod: function (a, b) { return b === 0 ? solFail("division by zero") : a - b * Math.floor(a / b); },
    pow: function (a, b) { return Math.pow(a, b); },
    neg: function (a) { return -a; },
    not: function (a) { return a ? 0 : 1; },
    lt: function (a, b) { return a < b ? 1 : 0; },
    le: function (a, b) { return a <= b ? 1 : 0; },
    gt: function (a, b) { return a > b ? 1 : 0; },
    ge: function (a, b) { return a >= b ? 1 : 0; },
    eq: function (a, b) { return a === b ? 1 : 0; },
    ne: function (a, b) { return a !== b ? 1 : 0; },
    min: function () { return Math.min.apply(null, arguments); },
    max: function () { return Math.max.apply(null, arguments); },
    abs: function (a) { return Math.abs(a); },
    sqrt: function (a) { return a < 0 ? solFail("sqrt of a negative number") : Math.sqrt(a); },
    log: function (a) { return a <= 0 ? solFail("log of zero or less") : Math.log(a); },
    exp: function (a) { return Math.exp(a); },
    ceil: function (a) { return Math.ceil(a); },
    floor: function (a) { return Math.floor(a); },
    round: function (a) { return Math.floor(a + 0.5); },
    clamp: function (a, lo, hi) { return Math.max(lo, Math.min(hi, a)); }
  };
  function solEval(tree, scope) {
    if (typeof tree === "number") return tree;
    if (typeof tree === "string") return Object.prototype.hasOwnProperty.call(scope, tree) ? scope[tree] : solFail("unknown name " + tree);
    var op = tree[0];
    if (op === "if") return solEval(solEval(tree[1], scope) ? tree[2] : tree[3], scope);
    if (op === "and" || op === "or") {
      var stop = op === "or";
      for (var i = 1; i < tree.length; i++) if (!!solEval(tree[i], scope) === stop) return stop ? 1 : 0;
      return stop ? 0 : 1;
    }
    var out = SOL_OPS[op].apply(null, tree.slice(1).map(function (t) { return solEval(t, scope); }));
    return isFinite(out) ? out : solFail(op + " is not a finite number");
  }
  /* The settings an approach has: the shared ones and those that name it. */
  function solSettings(spec, approach) {
    return spec.settings.filter(function (s) { return !s.approaches.length || s.approaches.indexOf(approach.id) >= 0; });
  }
  function solInputs(spec, scenario) {
    var out = {};
    spec.inputs.forEach(function (c) { out[c.id] = c.value; });
    Object.keys(scenario.inputs).forEach(function (k) { out[k] = scenario.inputs[k]; });
    return out;
  }
  /* A variant is an approach with its own setting values; `off` names the settings turned off. */
  function solVariant(spec, approach, id, label) {
    var settings = {};
    solSettings(spec, approach).forEach(function (c) { settings[c.id] = c.id in approach.settings ? approach.settings[c.id] : c.value; });
    return { id: id, approach: approach, label: label, on: true, added: false, settings: settings, off: {} };
  }
  /* A variant's measures for the inputs given, or { error } when a formula cannot compute. */
  function solMeasure(spec, variant, inputs) {
    var scope = {};
    Object.keys(inputs).forEach(function (k) { scope[k] = inputs[k]; });
    solSettings(spec, variant.approach).forEach(function (c) { scope[c.id] = variant.off[c.id] && c.off !== null ? c.off : variant.settings[c.id]; });
    var out = {};
    try {
      variant.approach.steps.forEach(function (s) { scope[s[0]] = solEval(s[1], scope); });
      Object.keys(variant.approach.measures).forEach(function (m) { out[m] = solEval(variant.approach.measures[m], scope); });
    } catch (err) {
      return { error: err.message };
    }
    return out;
  }
  /* Whether a value is inside the measure's budget; null when it has none. */
  function solMet(m, value) {
    if (m.budget === null) return null;
    return m.better === "higher" ? value >= m.budget : value <= m.budget;
  }
  /* A value in its unit and decimals, as the build's digest writes it. */
  function solShow(value, item) {
    if (value === null || value === undefined || !isFinite(value)) return "n/a";
    if (item.unit === "$") return compactMoney(value);
    var d = item.decimals || 0;
    var body = Number(value).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }).replace("-", "−");
    if (item.unit === "%") return body + "%";
    if (item.unit === "x") return body + "×";
    return item.unit ? body + " " + item.unit : body;
  }
  function solSettingText(c, value) {
    if (c.kind === "toggle") return value ? "on" : "off";
    if (c.kind === "choice") return (c.options.filter(function (o) { return o.value === value; })[0] || {}).label || "";
    return solShow(value, c);
  }
  /* The page's first numbers must equal the build's (spec.expect); a difference means the
     two formula readers no longer agree, and the page says so. */
  function solDrift(spec) {
    var bad = [];
    spec.scenarios.forEach(function (sc) {
      spec.approaches.forEach(function (a) {
        var got = solMeasure(spec, solVariant(spec, a, a.id, a.label), solInputs(spec, sc));
        var want = (spec.expect[sc.id] || {})[a.id] || {};
        spec.measures.forEach(function (m) {
          var w = want[m.id];
          if (got.error || !(Math.abs(got[m.id] - w) <= 1e-9 * Math.max(1, Math.abs(w)))) bad.push(a.label + ", " + m.label + ", " + sc.label);
        });
      });
    });
    return bad;
  }
  /* What a reader exports: the chosen variant, the variants compared with it, the inputs
     as they stand and the scenarios the reader saved. `blueprint solutions decide` reads it. */
  function solDecision(spec, state) {
    return {
      schema_version: 1,
      file: spec.file,
      title: spec.title,
      chosen: state.chosen,
      inputs: state.inputs,
      scenarios: state.scenarios.filter(function (s) { return s.added; }).map(function (s) { return { label: s.label, inputs: s.inputs }; }),
      variants: state.variants.filter(function (v) { return v.on || v.id === state.chosen; }).map(function (v) {
        return { id: v.id, approach: v.approach.id, label: v.label, settings: v.settings, off: Object.keys(v.off).filter(function (k) { return v.off[k]; }) };
      })
    };
  }
  function solClear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
