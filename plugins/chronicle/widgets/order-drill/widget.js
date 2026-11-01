// Tap the steps in order. A wrong tap says it comes later; the done list grows.
var steps = (data.steps || []).map(String);
var finished = String(data.done || "That is the whole sequence.");
var next = 0;
var done = kit.html("ol", "od-done", null, root);
var pool = kit.html("div", "od-pool", null, root);
var msg = kit.html("p", "od-msg", "", root);
msg.setAttribute("aria-live", "polite");
var again = kit.html("button", "od-again", kit.word("again", "Again"), root);
again.type = "button";

function shuffle(list) {
  var out = list.slice();
  for (var i = out.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var t = out[i]; out[i] = out[j]; out[j] = t;
  }
  return out;
}

function tap(button, name) {
  if (name !== steps[next]) {
    msg.textContent = "Not yet: " + name + " comes later.";
    button.classList.add("od-miss");
    setTimeout(function () { button.classList.remove("od-miss"); }, kit.reduceMotion ? 0 : 450);
    return;
  }
  kit.html("li", null, name, done);
  button.remove();
  next += 1;
  if (next === steps.length) {
    msg.textContent = finished;
    again.hidden = false;
    again.focus();
    return;
  }
  msg.textContent = "Right. What comes next?";
  var first = pool.querySelector("button");
  if (first) first.focus();
}

function deal() {
  next = 0;
  done.textContent = "";
  pool.textContent = "";
  again.hidden = true;
  msg.textContent = "Tap the first step.";
  shuffle(steps).forEach(function (name) {
    var b = kit.html("button", "od-chip", name, pool);
    b.type = "button";
    b.addEventListener("click", function () { tap(b, name); });
  });
}

again.addEventListener("click", deal);
deal();
