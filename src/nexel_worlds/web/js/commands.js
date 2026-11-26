// The server's commands in the chat line (admin.py on the server): /help and /list for everyone, and for an admin
// /tp, /summon, /give... The server says which you may use (asked each time the line opens: an admin made a moment
// ago has them at once) and what their words can be; it checks every one again when it is sent. A line that names
// one of them, written as a command is ("/give Joe wood 5", no "="), goes to the server, and its answer is a line of
// the chat. A bot's action written with its arguments ("/give target=3 item=wood") is still an action.
let serverCmds = null;                               // {cmds: [{name, usage, desc, args}], all: [names], admin, creatures, items, times}

function askCmds() {
  if (!me) return;
  rpc("cmds", {}).then((r) => {
    if (!r.ok || !r.cmds || (serverCmds && JSON.stringify(serverCmds.cmds) === JSON.stringify(r.cmds))) return;   // (the same: the list being walked is left as it is)
    serverCmds = r;
    if ($("chatbox").classList.contains("open") && $("say").value.startsWith("/")) suggest();
  });
}
// The line sent to the server, if it is one of its commands (true), or left to be an action (false)
// (not known yet, the line sent before the list came: the server says if it is one, or `orElse` makes it an action)
function serverCommand(line, word, orElse) {
  const w = String(word || "").toLowerCase();
  if ((serverCmds && !serverCmds.all.includes(w)) || (line.includes("=") && (!tools || w in tools))) return false;
  rpc("cmd", {line}).then((r) => {
    if (r.unknown) orElse();
    else if (r.text) chatLine(r.text, r.ok ? "note sys" : "note bad");
    else if (!r.ok) chatLine(r.detail || r.error || "No answer", "note bad");
    if (r.ok && (w === "op" || w === "deop")) askCmds();
  });
  return true;
}
const mineCmd = (name) => serverCmds && serverCmds.cmds.find((c) => c.name === name);
// What can be the k-th word after one of them: [{put, hint}]
function cmdValues(c, k) {
  const kind = c.args[k] || "", out = [];
  if (kind.startsWith("player")) {
    const names = [...agents].sort((a, b) => b.online - a.online || a.name.localeCompare(b.name));
    out.push(...names.map((a) => ({put: a.name, hint: a.online ? "" : "asleep"})));
    if (kind.endsWith("@e")) out.push({put: "@e", hint: "creatures near you"});
  } else if (kind === "creature") out.push(...serverCmds.creatures.map((n) => ({put: n, hint: ""})));
  else if (kind === "item") out.push(...serverCmds.items.map((n) => ({put: n, hint: ""})));
  else if (kind === "time") out.push(...serverCmds.times.filter((t) => t !== "set").map((n) => ({put: n, hint: ""})));
  else if (kind === "set") out.push({put: "set", hint: ""});
  return out;
}
// The list for a line begun with one of them (complete.js), or null when it is not one
function cmdCompletions(head, word, from) {
  const words = head.slice(1).split(/\s+/), c = mineCmd(words[0].toLowerCase());
  if (!c || (head.includes("=") && tools && c.name in tools)) return null;
  const items = matching(cmdValues(c, words.length - 2).map((v) => ({...v, show: v.put, put: v.put + " "})), word);
  return {from, items, note: items.length ? "" : c.usage};
}
