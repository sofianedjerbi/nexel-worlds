// Debugging aids, typed in the chat line (Enter, or /):
//   /coords, /perf   the debug screen (f3.js: F3 opens it too): where you are and what a frame costs
// Any other /word is an action sent to the server
// (/dig dir=N). The chat line lists the ones a player needs; the others once written in full (complete.js).
// Here too: the debug screen's sections about you and the world, and the machine's.

const COMMANDS = {
  coords: () => debugScreen("coords"),
  perf: () => debugScreen("perf"),
};
function debugScreen(word) { F3.toggle(); toast(`Debug screen ${F3.on ? "on" : "off"} (F3 or /${word})`); }
// A /word typed in the chat line that is one of ours: done here. -> was it?
function localCommand(word) {
  const run = COMMANDS[String(word || "").toLowerCase()];
  if (run) run();
  return !!run;
}

// Where you are (caves.js keeps your tile and height: myAt), what you face, the tile, the hour, who is near
const FACING = {"0,-1": "north", "0,1": "south", "-1,0": "west", "1,0": "east"};
F3.add("you", () => {
  const p = myId !== null ? ents.get("agent" + myId) : null; if (!myAt || !p) return ["Nexel Worlds  web " + webStamp, "(not in the world)"];
  const x = myAt.x, y = myAt.y, g = gndAt(x, y), top = topAt(x, y), aim = me && aimedTile();
  const h = ((clock.phase || 0) * 24 + 6) % 24, near = {people: 0, creatures: 0};
  for (const q of ents.values()) if (q !== p && q.e && Math.abs(q.x - p.x) <= 16 && Math.abs(q.y - p.y) <= 16) near[q.e.kind === "agent" ? "people" : "creatures"]++;
  return ["Nexel Worlds  web " + webStamp,
    `XYZ ${p.x.toFixed(2)} / ${p.y.toFixed(2)} / ${myAt.z}`,
    `Facing ${FACING[(p.fx || 0) + "," + (p.fy || 0)] || "-"}` + (aim ? `  aim ${aim.p.x}, ${aim.p.y} z ${topAt(aim.p.x, aim.p.y)}` : ""),
    `Tile ${x}, ${y}  ${g === null ? "not loaded" : label(CH[g] || g)}`,
    `Land top ${top}` + (top > myAt.z ? `  you are ${top - myAt.z} under it` : ""),
    `Chunk ${Math.floor(x / B)}, ${Math.floor(y / B)}  (${B} tiles)`,
    `Time ${String(Math.floor(h)).padStart(2, "0")}:${String(Math.floor((h % 1) * 60)).padStart(2, "0")}  ${clock.night ? "night" : "day"}`,
    `Near ${near.people} people, ${near.creatures} creatures`];
});
// The machine: the world's ticks reaching the screen, what a tick costs the world, the canvas, memory
const TICKS = {clock: null, n: 0, at: 0, gap: 0, since: 0};
F3.add("machine", () => {
  const now = performance.now(), s = TICKS.since ? (now - TICKS.since) / 1000 : 0, m = performance.memory;
  const r = [`ticks ${s ? (TICKS.n / s).toFixed(1) : "-"}/s  longest wait ${Math.round(TICKS.gap)} ms`,
    `world ${metrics.tick_ms_p50 ?? "?"} ms a tick, worst ${metrics.tick_ms_max ?? "?"}`,
    `canvas ${cv.width}x${cv.height} (x${DPR})  ${blocks.size} blocks  ${ents.size} bodies`,
    m ? `heap ${Math.round(m.usedJSHeapSize / 1048576)} / ${Math.round(m.jsHeapSizeLimit / 1048576)} MB` : null,
    `this screen ${F3.cost.toFixed(2)} ms`];
  TICKS.n = 0; TICKS.gap = 0; TICKS.since = now;
  return r;
}, "perf");
// Called at the end of each frame (render.js) with when it began, what the script did in it and how much of that was
// building land
function perfFrame(now, js, land) {
  if (!F3.on) return;
  if (clock !== TICKS.clock) { TICKS.clock = clock; TICKS.n++; if (TICKS.at) TICKS.gap = Math.max(TICKS.gap, now - TICKS.at); TICKS.at = now; }
  F3.sample(now, js, land);
}
