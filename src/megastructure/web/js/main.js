// Chat, panel buttons, URL options and start-up.

function openChat(prefix = "") { $("chat").style.display = "block"; const i = $("say"); i.value = prefix; i.focus(); }
$("say").addEventListener("keydown", (e) => {
  e.stopPropagation();
  if (e.key === "Escape") { $("chat").style.display = "none"; e.target.blur(); }
  if (e.key !== "Enter") return;
  const line = e.target.value.trim(); $("chat").style.display = "none"; e.target.blur(); e.target.value = "";
  if (!line) return;
  if (line.startsWith("/")) {
    const parts = line.slice(1).match(/(?:[^\s"]+|"[^"]*")+/g) || [], tool = parts.shift(), args = {};
    for (const p of parts) { const [k, ...v] = p.split("="); const val = v.join("=").replace(/^"|"$/g, ""); args[k] = /^-?\d+$/.test(val) ? +val : val; }
    act(tool, args);
  } else if (line.startsWith("!")) act("shout", {text: line.slice(1).trim()});
  else act("say", {text: line});
});
$("postbtn").onclick = postLetter; $("openbtn").onclick = takeLetters;
$("mailclose").onclick = () => { $("mail").style.display = "none"; };
$("letter").addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter") postLetter(); if (e.key === "Escape") $("mail").style.display = "none"; });
$("craftclose").onclick = () => { $("craft").style.display = "none"; drawGoals(); };
$("craftbtn").onclick = () => { const c = $("craft"); c.style.display = c.style.display === "block" ? "none" : "block"; drawGoals(); };
$("helpbtn").onclick = () => { const h = $("help"); const on = h.style.display !== "block"; h.style.display = on ? "block" : "none"; localStorage.setItem("megastructure-help", on ? "on" : "off"); };
$("join").onclick = () => { const n = $("name").value.trim(); if (n) joinGame(n); };
$("watch").onclick = () => { $("joinbox").style.display = "none"; };
$("brand").onclick = () => { if (!me) $("joinbox").style.display = "block"; };
$("name").value = localStorage.getItem("megastructure-name") || "";
const qs = new URLSearchParams(location.search);
if (qs.get("follow")) { follow = qs.get("follow"); $("joinbox").style.display = "none"; }
if (qs.get("zoom")) zoom = +qs.get("zoom");
ready.then(() => {
  buildBlob();
  document.querySelectorAll("canvas.ico").forEach((c) => { c.width = c.height = 16; c.getContext("2d").drawImage(IMG.gen, GEN[c.dataset.gen] * 16, 0, 16, 16, 0, 0, 16, 16); });
  connectSpec(); requestAnimationFrame(frame);
});
