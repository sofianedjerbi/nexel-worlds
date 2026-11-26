// Building, as a plan and then the work. Placing was one tile at a time, the one you faced: to raise a wall you
// walked a step, turned, pressed, and again, and walled yourself in. Now you plan first and your character builds:
//   Z          build mode, and out of it (by place: W on an AZERTY; B too, its first key: "'b' key is a bad choice. switching takes time from
//              WASD": Z is under A, the hand stays; every other key round WASD was taken, and a held Ctrl or Alt is
//              the browser's: Ctrl W shuts the page). What is in your hand is the piece: the bar's numbers.
//   arrows     move the cursor, a tile at a time (it is not you who walks: the view goes with the cursor)
//   Space      plan the piece here. Held while you move: a row. A door on a wall, a gate on a fence: in its place
//   X          break what is at the cursor: a plan back; a thing, a tree, a rock, a wall, a step, a floor: down; bare
//              ground: a hole, a layer deeper each time (a pickaxe digs faster); in the ground: that block. Held: a row
//   Q E        the cursor a layer down, and up (also PgDn, PgUp); Q by place: the key over A (A on an AZERTY)
//   Esc        drop every plan (with none: out of the mode)
// The cursor has a height. It starts on the block in front of you, at your own height ("show the most pertinent block first: in front of the player, direction where he's facing at his exact level"): a wall there, the block in front of your eyes ("default block to dig should be the one at player eye-level"; that one gone, the one in front of your legs); else the ground there (at your height, not the top of the land over the wall, a mountain's seventeen
// layers up). It rides the ground nearest your own (the floor you stand on); E lifts it a storey, into the air over a room or onto the floor above, and there it stays as it moves, until Q brings it down. Below your
// own floor Q sinks it to what is under it: the floor under yours (the ground floor from upstairs), a cave's floor,
// or, in the ground, a layer at a time: there it is on a block, and X digs that block and no other, where air is beside it; what is over it stays ("like minecraft ... this enforce me to dig huge columns": it dug the whole column over it; then the room to stand in, two blocks at once from the lower one: "why am i unable to break block at my eye level ? why do i
// need to target the one down to dig both at once ?"). Blocks are planned as far ahead as you like: each where the one before it will have made room (a plan counts the ones before it as dug). The block you stand on is dug from on it: you come down with it ("i should be able to break this block by putting myself in top of it then digging under my
// feets"). How deep is written beside it. (Q, E: after R F and Shift ↑ ↓, "not natural".) What you plan
// goes where the cursor is: a thing (a wall, a door, a bed) on what the cursor is on; a block (planks, a roof) on
// top of it, or, the cursor in the air, in the cell it is in, where a wall under it or a block beside it holds it.
// Planks on bare ground are a floor laid in it, as ever; a roof goes a storey over what the cursor is on (over your
// head, not at your feet), so a house is roofed without a key more. All that is over the cursor's level is faint.
// Every plan is a ghost on the ground. In build mode your character goes to the nearest, stands within reach of it
// and builds it (the game's own moves: walk there, place; the server checks each as it always did), then the next,
// block by block. Out of the mode it is yours to walk again, and the plans wait where they are till you come back.
// A plan that cannot be done (no way there, someone standing on it) turns red, says why, and goes.
// By mouse, in build mode: the cursor is where you point, a click plans, a drag plans a row, shift or the right
// button takes. The whole of it by keys alone. A piece bigger than a tile (a well, a coop) is still put by hand.
const Build = (() => {
  const REACH = 10, FIRST_MS = 230, STEP_MS = 75, BAD_MS = 2600;   // how far from you the cursor goes; a held arrow: its wait, then its pace; how long a failed plan shows
  const SWAP = {door: ["wood_wall", "stone_wall"], gate: ["fence"]};   // a piece that goes in the place of another: a door in a wall, a gate in a fence
  const swaps = (it, c) => !!SWAP[it] && SWAP[it].some((n) => CHAR[n] === c);
  const S = {on: false, at: null, plane: null, deep: null, plans: new Map(), hold: null, working: false, dir: null, timer: 0, pan: {x: 0, y: 0}};
  const now = () => performance.now(), UPMOST = 9, DEEPEST = 12, LOWEST = LOW;   // (how far over your own height the cursor goes: three floors; under it, layers; the deepest ground there is: the top of the bottom cell, sim/underground.py)
  const K = {S, REACH, FIRST_MS, STEP_MS, UPMOST, DEEPEST, LOWEST, swaps, now, toggle};   // (the parts, each its own file, look each other up here when called)
  for (const part of [BuildCursor, BuildPlans, BuildSays, BuildWork, BuildDo, BuildKeys]) Object.assign(K, part(S, K));
  const {ride, level, stops, todo, taking, plan, take, landFits, hint, work, held, onKey} = K;
  function toggle(on = !S.on) {
    if (on === S.on || (on && !me)) return;
    S.on = on; S.hold = null; S.plane = null; S.deep = null; held(null); document.body.classList.toggle("building", on);
    if (on) { S.at = facingTile() || myPos(); const s = myPos(), z = s ? myZ(s.x, s.y) : 0, c = s ? [z + 2, z + 1].find((t) => landSolid(S.at.x, S.at.y, t)) : undefined, r = ride(S.at); if (c < r) S.deep = c; else if (c > r) S.plane = c; work(); }   // (in front of you, at your own height: see above; its keys are by the cursor: prompts.js)
    else { S.pan = {x: 0, y: 0}; if (todo().length && !TOUCH) toast(`${todo().length} plans wait: ${capOf("build")} to go on building`); }      // (a phone has no B: its Build button stays up while plans wait, touch.js; the plans stay where they are)
  }
  function point(p) { if (S.on && tile(p.x, p.y)) { S.at = {x: p.x, y: p.y}; if (p.z !== undefined && p.z !== ride(S.at)) S.at.z = p.z; if (p.side) Object.assign(S.at, {side: p.side, cz: p.cz}); } }      // (the mouse: the cursor is where it points, the block under it (z, when not the ground nearest you there: it follows the land as it is dug and built), or at the cursor's height: mouse.js)
  function click(p, alt) { point(p); S.row = undefined; if (alt) take(S.at); else plan(S.at); }

  // Once a frame (render.js): a plan that could not be done is shown red a while, then goes; out of the mode when you are gone.
  // (What is planned, and the cursor, are drawn by the HD look in the land: hd.js written, pieces; target.js)
  function tick() {
    for (const [k, j] of S.plans) if (j.state === "bad" && now() - j.t > BAD_MS) S.plans.delete(k);
    if (S.on && !me) { S.plans.clear(); toggle(false); }                    // (you fell, or the game went: out of the mode)
  }
  // The view, in build mode: half way from you to the cursor, eased (both stay on the screen)
  function pan(dt) {
    const s = myPos(), to = S.on && S.at && s ? {x: (S.at.x - s.x) / 2, y: (S.at.y - s.y) / 2} : {x: 0, y: 0}, k = Math.min(1, dt * 6);
    S.pan.x += (to.x - S.pan.x) * k; S.pan.y += (to.y - S.pan.y) * k;
    return S.pan;
  }
  // What the keys do just now, for the corner of the screen (keyboard.js): the mode's name first, then each key
  // that does something here, in a few words
  const LAYER_CAP = () => keyCap("keyq") + " E";      // (the key over A, as this keyboard types it, and E)
  function rows() {
    const it = hint(S.at), n = todo().length, hit = taking(S.at), s = myPos(), up = s ? Keyhole.rel(level() - myZ(s.x, s.y)) : 0, sign = (v) => (v > 0 ? "+" : "") + v;
    const out = [[capOf("build"), up ? `BUILD · ${sign(up)} · leave` : "BUILD MODE · leave", "head"]];
    if (!it.far) out.push([it.key || "Space", it.text, it.ok === false && !it.key ? "bad" : ""]);
    out.push([LAYER_CAP(), "A layer down, up"]);
    if (hit && !hit.shut) out.push(["X", hit.plan ? "Take the plan back" : hit.dig ? "Break" : hit.verb || `Break ${hit.what}`]);   // (out of reach yet: no row, its box is dotted)
    if (n) out.push(["Esc", `Drop the ${n} plan${n > 1 ? "s" : ""}`]);
    return out;
  }
  const waiting = () => (!S.on && todo().length ? todo().length : 0);        // plans left on the ground, out of the mode
  return {S, LAYER_CAP, toggle, onKey, ways: () => { const L = level(), all = S.at && myPos() ? stops(S.at) : []; return {up: all.some((z) => z > L), down: all.some((z) => z < L)}; }, click, point, tick, pan, rows, hint, taking, waiting, level, landFits, get on() { return S.on; }, aim: () => { const it = hint(S.at); return {p: S.at, it: it.ghost || it.z !== undefined ? it : {...it, z: level()}}; }};
})();
