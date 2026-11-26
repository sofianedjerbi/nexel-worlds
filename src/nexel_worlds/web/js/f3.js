// F3: the debug screen. ONE readout for everything that tells what the game and the machine are doing, laid out as
// a sandbox game's debug screen: the world on the left (where you are, what you face, the tile, the hour, who is
// near, the server), what a frame costs on the right (frames, script, the HD look's draws and land, ticks, memory).
// There were three boxes made apart, each in its own style: the HD look's ?perf=1 box (a brown web box, monospace),
// /coords and /perf top right, and F3's line of server numbers bottom right. Each is now a section of this one:
//   F3.add(name, fn, side)   fn() -> lines (strings); side "game" (left) or "perf" (right). Asked 4 times a second.
//   F3.sample(now, ms, land) a frame: when it began and the script's ms (twice in a frame: the larger is kept)
// Opened by F3, ?perf=1, ?debug=1, /coords, /perf, the menu's "Debug screen" row, or holding the goals chip on a
// phone. Kept between visits. Off, it costs a test of one flag a frame. The GPU's ms a frame: gpu_time.js.
// Drawn in the game's pixel font: each line on a strip of dark see-through, its text with a shadow one art px down
// and right (the font's px is 2 CSS px at 18 px), no rounded box. On a phone at 9 px, the font's own size: the two
// columns one under the other, on the left.
// A phone's budget (#10): what a player waits and what a frame takes while you move, against PERF_BUDGET, in the
// section "budget": the owner reads it on the phone. F3.report() gives the same numbers (tests/e2e/test_e2e_demo.py).
//   paint  ms from the visit's start to the first thing painted (the browser's first-contentful-paint)
//   world  ms from the visit's start to the land drawn round you, less the time you spent on a usable first screen
//          before Wake up: what a player who taps it at once waits
//   frame  ms between two frames while you move (walk, sprint, swim): their p95, over the last MOVED frames
//          (counted while the debug screen is open, as its other frame numbers are)

const PERF_BUDGET = {paint: 1500, world: 6000, frame: 33};

const F3 = (() => {
  const q = new URLSearchParams(location.search), was = (k) => localStorage.getItem("nexel-" + k) === "1";
  const RANK = {you: 0, server: 1, frames: 0, budget: .5, look: 1, machine: 2};      // (the order the sections are read in, whatever order their files came in)
  const parts = [], S = {gaps: [], js: [], land: 0, n: 0, last: 0, at: 0, cost: 0, now: -1, moved: [], px: null, py: null};
  const MOVED = 300, L = {title: null, wake: null, world: null};       // (L: ms from the visit's start to each step of it)
  // the first screen usable: shown (`scene`) and no longer waiting on the world (`booting`)
  const usable = () => { if (L.title === null && document.body.classList.contains("scene") && !document.body.classList.contains("booting")) { L.title = performance.now(); seen.disconnect(); } };
  const seen = new MutationObserver(usable); seen.observe(document.body, {attributes: true, attributeFilter: ["class"]}); usable();
  let on = q.get("perf") === "1" || q.get("debug") === "1" || was("f3") || was("perf") || was("coords"), el = null, painted = 0;
  function add(name, fn, side = "game") { const i = parts.findIndex((p) => p.name === name); if (i >= 0) parts.splice(i, 1); parts.push({name, fn, side}); }
  function set(v) {
    on = !!v; localStorage.setItem("nexel-f3", on ? "1" : "0");
    for (const k of ["perf", "coords"]) localStorage.removeItem("nexel-" + k);   // (the two old switches: one now)
    if (!on) GpuTime.stop();
    const playing = typeof me !== "undefined" && !!me; document.body.classList.toggle("f3", on && playing); if (el) el.style.display = on && playing ? "" : "none"; S.gaps = []; S.js = []; S.moved = []; S.last = S.at = 0; painted = 0;
  }
  function sample(now, ms, land = 0) {
    if (!on) return;
    if (typeof me === "undefined" || !me) { if (el && el.style.display !== "none") { el.style.display = "none"; document.body.classList.remove("f3"); } return; }   // (the home screen: no debug screen over it, only in the game: "why does the F3 menu appear in the homescreen?")
    if (now === S.now) { S.js[S.js.length - 1] = Math.max(S.js[S.js.length - 1], ms); }      // (the classic frame inside the HD look's: one frame)
    else {
      const p = typeof myId !== "undefined" && myId !== null ? ents.get("agent" + myId) : null, moved = !!p && S.px !== null && (p.x !== S.px || p.y !== S.py);
      if (S.last) { S.gaps.push(now - S.last); if (moved) { S.moved.push(now - S.last); if (S.moved.length > MOVED) S.moved.shift(); } }
      if (p) { S.px = p.x; S.py = p.y; }
      S.last = S.now = now; S.js.push(ms); S.land += land; S.n++;
    }
    GpuTime.frame(now);                                                    // (the GPU's clock: one query a frame, gpu_time.js)
    if (now - painted >= 250) { painted = now; paint(now); }                // (the text 4 times a second)
  }
  function lines(side) {
    const out = [];
    const mine = parts.filter((p) => p.side === side).sort((a, b) => (RANK[a.name] ?? 9) - (RANK[b.name] ?? 9));
    for (const p of mine) { let l = []; try { l = p.fn() || []; } catch (e) { l = [p.name + ": " + e.message]; } l = l.filter((x) => x !== null && x !== undefined); if (l.length && out.length) out.push(""); out.push(...l); }   // (a gap between two sections)
    return out;
  }
  function make() {
    el = document.createElement("div"); el.id = "f3";
    el.innerHTML = '<div class="f3c f3game"></div><div class="f3c f3perf"></div>';
    el.addEventListener("click", () => set(false));   // (a phone: the goals' chip that opened it is hidden under it: a tap on its lines closes it)
    document.body.appendChild(el);
  }
  function write(col, ls) {
    while (col.children.length > ls.length) col.lastChild.remove();
    ls.forEach((t, i) => { let d = col.children[i]; if (!d) { d = document.createElement("div"); col.appendChild(d); } if (d.textContent !== (t || " ")) d.textContent = t || " "; d.style.visibility = t ? "" : "hidden"; });
  }
  function paint(now) {
    const t0 = performance.now();
    if (!el) make();
    el.style.display = ""; document.body.classList.add("f3");
    write(el.children[0], lines("game")); write(el.children[1], lines("perf"));
    // the top left corner, always (the owner: "goal shouldn't push everything down": it was put under the goals and the chat); what it covers there (goals, chat) is hidden while it is open: body.f3 (style.css)
    S.cost = performance.now() - t0; S.at = now;
  }
  // a phone: hold the goals' chip (or card) for half a second
  let hold = 0, held = false;
  addEventListener("pointerdown", (e) => { if (!e.target.closest || !e.target.closest("#goalhint, #goals")) return; clearTimeout(hold); held = false; hold = setTimeout(() => { held = true; set(!on); if (on) paint(performance.now()); }, 500); }, true);
  for (const k of ["pointerup", "pointercancel", "pointerleave"]) addEventListener(k, () => clearTimeout(hold), true);
  addEventListener("click", (e) => { if (held && e.target.closest && e.target.closest("#goalhint, #goals")) { held = false; e.stopPropagation(); e.preventDefault(); } }, true);   // (the hold is not also a tap on the goals)
  const at = (l, k) => { if (!l.length) return 0; const s = l.slice().sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.floor(s.length * k))]; };
  // what the frames cost since the last time the text was written
  add("frames", () => {
    const g = S.gaps, n = S.js.length, secs = g.reduce((a, b) => a + b, 0) / 1000;
    const r = [`${secs ? Math.round(g.length / secs) : "-"} fps  frame ${at(g, .5).toFixed(1)} / ${at(g, .95).toFixed(1)} ms (median / p95)`,
      `script ${at(S.js, .5).toFixed(1)} / ${at(S.js, .95).toFixed(1)} ms  land ${(n ? S.land / n : 0).toFixed(1)} ms`,
      GpuTime.ms === null ? `GPU n/a${GpuTime.ok ? " (waiting)" : "  (no timer on this GPU)"}` : `GPU ${GpuTime.ms.toFixed(1)} ms a frame (mean, ${GpuTime.contexts} canvases)`];
    S.gaps = []; S.js = []; S.land = 0; S.n = 0;
    return r;
  }, "perf");
  // the steps of the visit: Wake up pressed (agent.js joinGame), and each frame (debug.js perfFrame, F3 on or off) the land drawn round you
  function woke() { if (L.wake === null) L.wake = performance.now(); }
  function arrived(now) { if (L.wake !== null && L.world === null && meObs && myPos() && (!HdLook.on || HdLook.faces > 500)) L.world = now; }
  function report() {
    const fcp = performance.getEntriesByType("paint").find((e) => e.name === "first-contentful-paint"), m = S.moved;
    const world = L.world === null ? null : L.world - (L.title !== null && L.wake > L.title ? L.wake - L.title : 0);
    return {paint: fcp ? fcp.startTime : null, title: L.title, wake: L.wake, world, moved: m.length, frame: m.length ? at(m, .95) : null, over: m.filter((g) => g > PERF_BUDGET.frame).length};
  }
  add("budget", () => {
    const r = report(), s = (v) => (v === null ? "-" : (v / 1000).toFixed(1)), over = (v, k) => (v !== null && v > PERF_BUDGET[k] ? " OVER" : "");
    return [`load: paint ${s(r.paint)} s${over(r.paint, "paint")}, in the world ${s(r.world)} s${over(r.world, "world")} (budget ${PERF_BUDGET.paint / 1000} / ${PERF_BUDGET.world / 1000} s)`,
      `moving: frame p95 ${r.frame === null ? "-" : r.frame.toFixed(1) + " ms"}${over(r.frame, "frame")}, ${r.over}/${r.moved} over ${PERF_BUDGET.frame} ms (budget p95 ${PERF_BUDGET.frame})`];
  }, "perf");
  return {add, set, sample, woke, arrived, report, toggle: () => set(!on), get on() { return on; }, get el() { return el; }, lines, get cost() { return S.cost; }};
})();
