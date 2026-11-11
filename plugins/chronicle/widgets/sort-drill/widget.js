// Sort each card into its group, one card at a time; the score counts first tries.
var buckets = (data.buckets || []).map(String);
var items = (data.items || []).map(function (i) { return { text: String(i.text), bucket: String(i.bucket) }; });
var finished = String(data.done || "Every card is in its group.");
var card = kit.html("p", "sd-card", "", root);
var row = kit.html("div", "sd-buckets", null, root);
var lists = {};
var shelf = kit.html("div", "sd-shelf", null, root);
var msg = kit.html("p", "sd-msg", "", root);
msg.setAttribute("aria-live", "polite");
var again = kit.html("button", "sd-again", kit.word("again", "Again"), root);
again.type = "button";
var queue = [];
var first = true;
var right = 0;

buckets.forEach(function (name) {
  var b = kit.html("button", "sd-bucket", name, row);
  b.type = "button";
  b.addEventListener("click", function () { place(name); });
  var col = kit.html("div", "sd-col", null, shelf);
  kit.html("h5", null, name, col);
  lists[name] = kit.html("ul", null, null, col);
});

function shuffle(list) {
  var out = list.slice();
  for (var i = out.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var t = out[i]; out[i] = out[j]; out[j] = t;
  }
  return out;
}

function show() {
  if (!queue.length) {
    card.textContent = "";
    row.hidden = true;
    msg.textContent = finished + " " + right + " of " + items.length + " right the first time.";
    again.hidden = false;
    again.focus();
    return;
  }
  first = true;
  card.textContent = queue[0].text;
}

function place(name) {
  var item = queue[0];
  if (!item) return;
  if (item.bucket !== name) {
    first = false;
    msg.textContent = "Not " + name + ". Try another group.";
    return;
  }
  if (first) right += 1;
  kit.html("li", null, item.text, lists[name]);
  queue.shift();
  msg.textContent = first ? "Right." : "Right, on a second try.";
  show();
}

function deal() {
  Object.keys(lists).forEach(function (k) { lists[k].textContent = ""; });
  queue = shuffle(items);
  right = 0;
  row.hidden = false;
  again.hidden = true;
  msg.textContent = "Which group does this card belong to?";
  show();
}

again.addEventListener("click", deal);
deal();
