// The architecture animation is one script-free SVG; an <img> plays it, and Pause swaps in the still.
var frame = kit.html("div", "frame", null, root);
var img = kit.html("img", null, null, frame);
img.alt = data.alt || "";
img.width = 1280;
img.height = 720;
img.decoding = "async";
var bar = kit.html("div", "bar", null, root);
var toggle = kit.html("button", "toggle", null, bar);
toggle.type = "button";
var note = kit.html("span", "note", data.note || "", bar);
var playing = !kit.reduceMotion;
function show() {
  img.src = playing ? data.src : data.poster;
  toggle.textContent = playing ? kit.word("pause", "Pause") : kit.word("play", "Play");
  toggle.setAttribute("aria-pressed", playing ? "false" : "true");
}
toggle.addEventListener("click", function () {
  playing = !playing;
  show();
});
show();
var list = kit.html("ol", "steps", null, root);
(data.steps || []).forEach(function (step) {
  kit.html("li", null, step, list);
});
