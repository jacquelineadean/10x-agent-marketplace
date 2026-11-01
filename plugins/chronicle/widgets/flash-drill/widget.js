// Flash cards: read the front, show the back, then say whether you knew it.
// A card you missed comes back at the end of the round until you know it.
var cards = (data.cards || []).map(function (c) { return { front: String(c.front), back: String(c.back) }; });
var finished = String(data.done || "You know every card.");
var face = kit.html("div", "fd-card", null, root);
var front = kit.html("p", "fd-front", "", face);
var back = kit.html("p", "fd-back", "", face);
var row = kit.html("div", "fd-row", null, root);
var show = kit.html("button", "fd-show", kit.word("show", "Show"), row);
var knew = kit.html("button", "fd-knew", "I knew it", row);
var missed = kit.html("button", "fd-missed", "Not yet", row);
var count = kit.html("p", "fd-count", "", root);
count.setAttribute("aria-live", "polite");
var again = kit.html("button", "fd-again", kit.word("again", "Again"), root);
[show, knew, missed, again].forEach(function (b) { b.type = "button"; });
var queue = [];
var learned = 0;

function turn() {
  if (!queue.length) {
    face.hidden = true;
    row.hidden = true;
    count.textContent = finished;
    again.hidden = false;
    again.focus();
    return;
  }
  front.textContent = queue[0].front;
  back.textContent = queue[0].back;
  back.hidden = true;
  show.hidden = false;
  knew.hidden = true;
  missed.hidden = true;
  count.textContent = learned + " of " + cards.length + " learned.";
}

show.addEventListener("click", function () {
  back.hidden = false;
  show.hidden = true;
  knew.hidden = false;
  missed.hidden = false;
  knew.focus();
});
knew.addEventListener("click", function () { queue.shift(); learned += 1; turn(); show.focus(); });
missed.addEventListener("click", function () { queue.push(queue.shift()); turn(); show.focus(); });

function deal() {
  queue = cards.slice();
  learned = 0;
  face.hidden = false;
  row.hidden = false;
  again.hidden = true;
  turn();
}

again.addEventListener("click", deal);
deal();
