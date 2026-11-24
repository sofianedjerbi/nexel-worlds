// A word asked of you in a small box: what a sign says when you put it up, an animal's name when you tie a name tag
// on it. ("turn the command that could be turned into UI (signs, naming mobs) into ui. As example Signs = write when
// placing. Naming mobs = naming tag required.") Enter gives it, Esc gives up.
let askDone = null;
function askText({title, hint = "", value = "", max = 60, ok = "OK"}) {
  return new Promise((done) => {
    if (askDone) askDone(null);                      // (one at a time: the one before is given up)
    askDone = (v) => { askDone = null; $("ask").style.display = "none"; $("asktext").blur(); done(v); };
    const i = $("asktext");
    $("asktitle").textContent = title; i.placeholder = hint; i.value = value; i.maxLength = max; $("askok").textContent = ok;
    $("ask").style.display = "block";
    setTimeout(() => { i.focus(); i.select(); }, 30);  // (after the key that asked: its own letter is not typed in)
  });
}
$("asktext").addEventListener("keydown", (e) => {
  e.stopPropagation();                               // (the letters are the box's: no walking, no shortcuts)
  if (e.key === "Enter" && askDone) askDone($("asktext").value.trim());
  if (e.key === "Escape" && askDone) askDone(null);
});
$("askok").onclick = () => askDone && askDone($("asktext").value.trim());
$("askclose").onclick = () => askDone && askDone(null);
// A sign or a flag goes up with its words (none: a blank sign; a flag says whose it is).
function placeWritten(d, item) {
  return askText({title: item === "sign" ? "What does the sign say?" : "What does the flag say?", hint: item === "sign" ? "Write on it" : "claimed by " + me, max: 80, ok: "Put up"})
    .then((t) => (t === null ? null : act("place", {dir: d, item, ...(t ? {text: t} : {})})));
}
// A name tag in hand, an animal in front of you: its name. The tag stays on it.
function nameAnimal(e) {
  return askText({title: e.name ? `A new name for ${e.name}` : `Name the ${label(e.kind)}`, hint: "Its name", value: e.name || "", max: 16, ok: "Name"})
    .then((t) => (t ? act("name", {target: e.id, text: t}) : null));
}
