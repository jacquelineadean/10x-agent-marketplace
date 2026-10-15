// Dial in a shot: a practice model of grind against shot time. Finer grind slows the
// shot; the target window comes from the handbook.
var low = Number(data.low), high = Number(data.high);
var maxS = 45;
var row = kit.html("div", "dial-row", null, root);
var label = kit.html("label", "dial-label", "Grind", row);
var input = kit.html("input", "dial-range", null, row);
input.type = "range";
input.min = "1";
input.max = "12";
input.step = "1";
input.value = "3";
input.id = "dial-in-grind";
label.setAttribute("for", input.id);
var ends = kit.html("div", "dial-ends", null, root);
kit.html("span", null, "Coarse", ends);
kit.html("span", null, "Fine", ends);
// Drawn at the figure's own width so labels keep their size on a phone.
var W = Math.max(280, Math.min(600, root.clientWidth || 600));
var chart = kit.svg("svg", { viewBox: "0 0 " + W + " 90", "class": "dial-chart", role: "img", "aria-label": "Shot time against the target window" }, root);
var x = kit.linear(0, maxS, 20, W - 20);
kit.svg("rect", { x: x(0), y: 34, width: x(maxS) - x(0), height: 16, rx: 8, "class": "dial-track" }, chart);
kit.svg("rect", { x: x(low), y: 34, width: x(high) - x(low), height: 16, "class": "dial-band" }, chart);
kit.text(chart, x(low), 24, low + " s", { "text-anchor": "middle", "class": "dial-tick" });
kit.text(chart, x(high), 24, high + " s", { "text-anchor": "middle", "class": "dial-tick" });
var marker = kit.svg("g", { "class": "dial-marker" }, chart);
var stem = kit.svg("line", { x1: 0, x2: 0, y1: 28, y2: 58 }, marker);
var dot = kit.svg("circle", { cx: 0, cy: 42, r: 9 }, marker);
var value = kit.text(chart, 0, 80, "", { "text-anchor": "middle", "class": "dial-value" });
var out = kit.html("p", "dial-out", null, root);
out.setAttribute("aria-live", "polite");
function seconds(g) { return 12 + g * 2.6; }
function update() {
  var s = seconds(Number(input.value));
  var px = x(Math.min(s, maxS));
  marker.setAttribute("transform", "translate(" + px.toFixed(1) + ",0)");
  value.setAttribute("x", px.toFixed(1));
  value.textContent = kit.fmt(s, "int") + " s";
  var good = s >= low && s <= high;
  marker.setAttribute("class", "dial-marker" + (good ? " good" : ""));
  if (s < low) out.textContent = "The shot runs in " + kit.fmt(s, "int") + " seconds: too fast, thin and sour. Grind finer.";
  else if (s > high) out.textContent = "The shot runs in " + kit.fmt(s, "int") + " seconds: too slow, heavy and bitter. Grind coarser.";
  else out.textContent = "The shot runs in " + kit.fmt(s, "int") + " seconds, inside the window. Taste it, then serve it.";
}
input.addEventListener("input", update);
update();
stem.setAttribute("stroke-width", "2");
dot.setAttribute("stroke-width", "2");
