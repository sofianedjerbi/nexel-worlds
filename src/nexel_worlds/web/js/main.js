// Chat, panel buttons, URL options and start-up.

// Chat, like many sandbox games: recent lines show for a while then fade; Enter opens the history and the input.
const CHAT_KEEP = 100;
// What the game itself says may be dressed ("add bold, line return... make them beautiful in the chat"): **bold** for
// the word that matters, a new line where one is written, `K` for a key drawn as a key. What a player says is never
// dressed: it is shown as typed.
const rich = (text) => esc(text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<kbd>$1</kbd>").replace(/\n/g, "<br>");
const plain = (text) => String(text).replace(/\*\*|`/g, "").replace(/\n/g, " ");
function chatLine(text, cls = "", who = null) {
  const log = $("chatlog"), last = log.lastElementChild;
  if (last && last.dataset.text === text + (who || "")) {           // the same line again: count it
    last.dataset.n = +(last.dataset.n || 1) + 1; last.querySelector(".n").textContent = ` ×${last.dataset.n}`;
    last.dataset.t = Date.now(); last.classList.remove("old"); return;
  }
  const d = document.createElement("div"); d.className = cls; d.dataset.text = text + (who || ""); d.dataset.t = Date.now();
  d.innerHTML = (who ? `<span class="who">${esc(who)}</span> ` : "") + (who ? esc(text) : rich(text)) + `<span class="n"></span>`;
  log.appendChild(d); while (log.childElementCount > CHAT_KEEP) log.firstElementChild.remove();
  log.scrollTop = log.scrollHeight;
}
// A phone: two short lines top left, gone after a few seconds (not over the top left quarter of the screen for as
// long as the welcome lasts); a tap on them opens what was said, a tap anywhere else shuts it, and the line to write in.
const chatSmall = () => document.body.classList.contains("touch") && (innerWidth <= 600 || innerHeight <= 520), chatKeep = () => (chatSmall() ? Math.min(opt("chat"), 6) : opt("chat"));
$("chatlog").addEventListener("click", () => { const b = $("chatbox"); if (chatSmall() && !b.classList.contains("open")) { b.classList.toggle("peek"); $("chatlog").scrollTop = 1e9; } });
addEventListener("pointerdown", (e) => { const b = $("chatbox"); if (e.target.closest("#chatbox, #tTalk") || !chatSmall()) return; b.classList.remove("peek"); if (b.classList.contains("open")) closeChat(); }, true);
setInterval(() => { for (const d of $("chatlog").children) d.classList.toggle("old", Date.now() - d.dataset.t > chatKeep() * 1000); }, 500);      // (the settings' A chat line stays)
// What you sent before comes back with the arrows ("implement up/down arrow to browse chat/command history"): Up goes
// back through it, Down forward again, and past the newest the line you were writing is there as you left it. Begun
// from a "/", only the commands come back. It is kept from one visit to the next (the last SAID_KEEP lines).
// The arrows stay the list's (complete.js) while a list of several is being walked: a line with something typed.
const SAID_KEEP = 50;
let said = JSON.parse(localStorage.getItem("nexel-said") || "[]"), saidAt = null, saidDraft = "";
function saidKey(e) {
  if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return false;
  const i = $("say"), up = e.key === "ArrowUp";
  if (saidAt === null) {                               // not going through it yet: Up begins, unless the arrows are the list's
    if (!up || (comp.items.length > 1 && i.value !== "" && i.value !== "/")) return false;
    saidDraft = i.value;
  }
  const list = saidDraft.startsWith("/") ? said.filter((l) => l.startsWith("/")) : said;
  e.preventDefault();
  if (!list.length) return true;
  const at = Math.max(0, (saidAt === null ? list.length : saidAt) + (up ? -1 : 1));
  if (at >= list.length) { saidAt = null; i.value = saidDraft; } else { saidAt = at; i.value = list[at]; }
  i.setSelectionRange(i.value.length, i.value.length);
  suggest();                                           // (a command that comes back has its hints)
  return true;
}
function saidAdd(line) {
  said = [...said.filter((l) => l !== line), line].slice(-SAID_KEEP);      // (said twice: once, at its latest place)
  localStorage.setItem("nexel-said", JSON.stringify(said));
}
$("say").addEventListener("input", () => { saidAt = null; });
function openChat(prefix = "") { saidAt = null; $("chatbox").classList.remove("peek"); $("chatbox").classList.add("open"); const i = $("say"); i.value = prefix; i.focus(); $("chatlog").scrollTop = 1e9; askTools(); suggest(); }   // (complete.js)
function closeChat() { $("chatbox").classList.remove("open"); $("say").blur(); suggest(); }
$("say").addEventListener("keydown", (e) => {
  e.stopPropagation();
  if (e.key === "Escape") closeChat();
  if (saidKey(e) || completeKey(e) || e.key !== "Enter") return;   // (the arrows: what you sent before; Tab, the arrows: the list over the line, complete.js)
  const line = e.target.value.trim(); closeChat(); e.target.value = "";
  if (!line) return;
  saidAdd(line);
  if (line.startsWith("/")) {
    const parts = line.slice(1).match(/(?:[^\s"]+|"[^"]*")+/g) || [], tool = parts.shift(), args = {};
    for (const p of parts) { const [k, ...v] = p.split("="); const val = v.join("=").replace(/^"|"$/g, ""); args[k] = /^-?\d+$/.test(val) ? +val : val === "true" ? true : val === "false" ? false : val; }
    if (!localCommand(tool) && !serverCommand(line, tool, () => act(tool, args))) act(tool, args);   // (/coords, /perf: debug.js; /tp, /help...: the server's, commands.js; anything else is an action)
  } else if (line.startsWith("!")) act("shout", {text: line.slice(1).trim()});
  else if (shouted(line)) act("shout", {text: line});      // WRITTEN IN CAPITALS: a shout, as it reads
  else act("say", {text: line});
});
$("postbtn").onclick = postLetter; $("openbtn").onclick = takeLetters;
$("mailclose").onclick = () => { $("mail").style.display = "none"; };
$("letter").addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter") postLetter(); if (e.key === "Escape") $("mail").style.display = "none"; });
$("craftclose").onclick = () => { sfx("close"); $("craft").style.display = "none"; drawGoals(); };
$("say").addEventListener("blur", closeChat);
function toggleCraft() { const c = $("craft"), open = c.style.display !== "block"; sfx(open ? "open" : "close"); c.style.display = open ? "block" : "none"; if (open) craftOpened(); drawGoals(); }   // (C; on a phone, its button at the top)
$("helpbtn").onclick = () => { const h = $("help"); const on = h.style.display !== "block"; h.style.display = on ? "block" : "none"; localStorage.setItem("nexel-help", on ? "on" : "off"); };
$("goalhelp").onclick = () => $("helpbtn").click();
$("join").onclick = () => { const n = $("name").value.trim(); if (n) joinGame(n); };
$("brand").onclick = () => { if (!me) $("joinbox").style.display = "block"; };
$("name").value = localStorage.getItem("nexel-name") || "";
{ let fresh = true; const n = $("name"); n.addEventListener("focus", () => { fresh = true; setTimeout(() => n.select(), 0); }); n.addEventListener("mouseup", (e) => { if (fresh) { e.preventDefault(); n.select(); } fresh = false; }); n.addEventListener("input", () => { fresh = false; }); }   // (the last name, whole: what you type replaces it ("qastepqastep": not added to); it has the focus as the page opens, so the first click takes it whole too)
const qs = new URLSearchParams(location.search);
if (qs.get("follow")) { follow = qs.get("follow"); $("joinbox").style.display = "none"; }
if (qs.get("zoom")) zoom = +qs.get("zoom");
ready.then(() => {
  buildBlob();
  connectSpec(); requestAnimationFrame(frame);
});
