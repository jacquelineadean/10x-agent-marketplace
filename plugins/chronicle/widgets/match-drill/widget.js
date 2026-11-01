// Match each term to its meaning: pick a term, then the meaning that belongs to it.
var pairs = (data.pairs || []).map(function (p) { return { term: String(p.term), meaning: String(p.meaning) }; });
var finished = String(data.done || "Every term found its meaning.");
var grid = kit.html("div", "md-grid", null, root);
var terms = kit.html("div", "md-col", null, grid);
var meanings = kit.html("div", "md-col", null, grid);
var msg = kit.html("p", "md-msg", "", root);
msg.setAttribute("aria-live", "polite");
var again = kit.html("button", "md-again", kit.word("again", "Again"), root);
again.type = "button";
var chosen = null;
var matched = 0;
var tries = 0;

function shuffle(list) {
  var out = list.slice();
  for (var i = out.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var t = out[i]; out[i] = out[j]; out[j] = t;
  }
  return out;
}

function pickTerm(button, pair) {
  if (chosen) chosen.button.setAttribute("aria-pressed", "false");
  chosen = { button: button, pair: pair };
  button.setAttribute("aria-pressed", "true");
  msg.textContent = "Now pick the meaning of " + pair.term + ".";
}

function pickMeaning(button, pair) {
  if (!chosen) { msg.textContent = "Pick a term first."; return; }
  tries += 1;
  if (chosen.pair !== pair) {
    msg.textContent = "Not that one. " + chosen.pair.term + " means something else.";
    return;
  }
  chosen.button.disabled = true;
  button.disabled = true;
  chosen.button.setAttribute("aria-pressed", "false");
  chosen.button.classList.add("md-done");
  button.classList.add("md-done");
  chosen = null;
  matched += 1;
  if (matched === pairs.length) {
    msg.textContent = finished + " " + pairs.length + " matched in " + tries + " tries.";
    again.hidden = false;
    again.focus();
  } else {
    msg.textContent = "Matched. " + (pairs.length - matched) + " to go.";
  }
}

function deal() {
  terms.textContent = "";
  meanings.textContent = "";
  chosen = null;
  matched = 0;
  tries = 0;
  again.hidden = true;
  msg.textContent = "Pick a term.";
  pairs.forEach(function (pair) {
    var b = kit.html("button", "md-term", pair.term, terms);
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", function () { pickTerm(b, pair); });
  });
  shuffle(pairs).forEach(function (pair) {
    var b = kit.html("button", "md-meaning", pair.meaning, meanings);
    b.type = "button";
    b.addEventListener("click", function () { pickMeaning(b, pair); });
  });
}

again.addEventListener("click", deal);
deal();
