// The first screen's background: a small island made by hand, with its own little life, instead of the world you
// are about to wake in. It is part of the page (title_map.js: six blocks of land baked by tools/build_title_scene.py,
// and one of open sea used for everything round them), so it is there as soon as the pictures are: no server to
// answer, no world to load (the demo's takes many seconds to start).
// It is drawn by the game itself, as any land is: the blocks are handed over as the server would hand them, far
// from where anyone lives, and a small cast is said to be there ten times a second, as a server's tick would say:
// Mira walks from her door to the field, waters it and comes back; Tobi chops at a tree and rests; Pip sails round
// the island; Lou, a duck, swims the pond; hens and a chick in their pen, two cows in the meadow. The hours go by in
// a little over three minutes a day, so the light, the dusk and the fire at night all pass; the view drifts slowly.
// It stops when you wake up or choose to watch: the land is forgotten and the world's own is asked for.

const TitleScene = (() => {
  const OX = -8000, OY = -8000, M = typeof TITLE_MAP === "undefined" ? null : TITLE_MAP, DAY = 2000, S = {on: false, tick: 0, timer: 0, cast: []};
  let seed = 7;
  const rnd = () => (seed = (seed * 1103515245 + 12345) >>> 0) / 4294967296, pick = (n) => Math.floor(rnd() * n);     // (its own dice: the same little play each time)
  const DIRS = [[0, -1, "N"], [1, 0, "E"], [0, 1, "S"], [-1, 0, "W"]];
  const open = (x, y) => { const t = tile(OX + x, OY + y); return !!t && GROUND.has(t[0]) && !"~=()".includes(t[0]); };       // bare ground, not water

  function cast() {
    const C = M.cast, there = C.mira, back = [...there].reverse();
    const person = (id, name, race, worn, more) => ({id, kind: "agent", name, race, worn, x: 0, y: 0, doing: null, dir: "S", ...more});
    const herd = (kind, n, id0, box, every) => [...Array(n)].map((_, i) => ({id: id0 + i, kind, box, every, wait: pick(every), x: box[0] + pick(box[2] - box[0] + 1), y: box[1] + pick(box[3] - box[1] + 1)}));
    return [
      // Mira: a way there, a while at the field with the can, the way back, a while at her door
      person(9001, "Mira", "bunny", {head: "straw_hat"}, {x: there[0][0], y: there[0][1], play: [[there, 2], [{doing: "water", with: "watering_can", dir: "N"}, 34], [back, 2], [{dir: "S"}, 30]], at: 0, i: 0, wait: 0}),
      person(9002, "Tobi", "bear", null, {x: C.tobi[0], y: C.tobi[1], play: [[{doing: "dig", with: "axe", dir: "N"}, 42], [{dir: "S"}, 26]], at: 0, i: 0, wait: 0}),
      person(9003, "Pip", "frog", {head: "bandana"}, {x: C.sailor[0][0], y: C.sailor[0][1], sail: true, loop: C.sailor, i: 0, every: 2}),
      person(9004, "Lou", "duck", null, {x: C.duck[0][0], y: C.duck[0][1], swim: true, loop: C.duck, i: 0, every: 4}),
      ...herd("chicken", 3, 9101, C.pen, 14), ...herd("chick", 1, 9111, C.pen, 9), ...herd("cow", 2, 9121, C.meadow, 26),
    ];
  }
  // One of them, a tenth of a second on
  function act(a) {
    if (a.loop) {                                            // round and round: the boat, the duck
      if (S.tick % a.every === 0) { a.i = (a.i + 1) % a.loop.length; [a.x, a.y] = a.loop[a.i]; }
      a.doing = "walk";
    } else if (a.play) {                                     // a play of scenes: a way to walk, or something to do for a while
      const [what, n] = a.play[a.at];
      if (Array.isArray(what)) {
        a.doing = "walk";
        if (S.tick % n === 0) { a.i++; if (a.i >= what.length) { a.at = (a.at + 1) % a.play.length; a.i = 0; a.wait = 0; } else [a.x, a.y] = what[a.i]; }
      } else {
        a.doing = what.doing || null; a.with = what.with || null; a.dir = what.dir;
        if (++a.wait >= n) { a.at = (a.at + 1) % a.play.length; a.i = 0; a.wait = 0; a.doing = a.with = null; }
      }
    } else if (--a.wait <= 0) {                              // an animal: a step now and then, inside its field, where the ground is bare
      a.wait = a.every + pick(a.every);
      const [dx, dy] = DIRS[pick(4)], x = a.x + dx, y = a.y + dy;
      if (x >= a.box[0] && x <= a.box[2] && y >= a.box[1] && y <= a.box[3] && open(x, y) && !S.cast.some((o) => o !== a && o.x === x && o.y === y)) { a.x = x; a.y = y; }
    }
  }
  const said = (a) => a.kind === "agent"
    ? {kind: "agent", name: a.name, id: a.id, x: OX + a.x, y: OY + a.y, hp: HP_MAX, doing: a.doing, weapon: null, dir: a.doing && a.doing !== "walk" ? a.dir : null, tid: null, at: null, with: a.with || null, item: null, run: false,
       sail: !!a.sail, z: levelAt(OX + a.x, OY + a.y) || 0, race: a.race, ...(a.worn ? {worn: a.worn} : {}), ...(a.swim ? {swim: true} : {})}
    : {kind: a.kind, id: a.id, x: OX + a.x, y: OY + a.y, z: levelAt(OX + a.x, OY + a.y) || 0, hp: 10, love: false, scared: false};
  function sea() {                                           // open sea wherever the screen looks past the island's blocks
    const [x, y, w, h] = viewRect(8);
    for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++) for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++)
      if (!blocks.has(bkey(bx, by))) onRegion({x: bx * B, y: by * B, w: B, h: B, ...M.sea});
  }
  function step() {
    S.tick++;
    for (const a of S.cast) act(a);
    const phase = (.3 + S.tick / DAY) % 1, hm = Math.floor(phase * 1440), two = (n) => String(n).padStart(2, "0");
    onTick({type: "tick", tick: S.tick, time: `day 1, ${two(Math.floor(hm / 60))}:${two(hm % 60)}${phase >= .75 ? " (night)" : ""}`, night: phase >= .75, phase, entities: S.cast.map(said), items: [], mail: [], troughs: [], fires: []});
    camT.x = OX + M.cast.centre[0] + 9 * Math.sin(S.tick / 300); camT.y = OY + M.cast.centre[1] + 4 * Math.sin(S.tick / 190 + 1);      // the view drifts, slowly
    sea();
  }
  function start() {
    if (S.on || !M || me) return;
    S.on = true; S.tick = 0; seed = 7;
    for (const b of M.blocks) onRegion({...b, x: b.x + OX, y: b.y + OY});
    cam.x = camT.x = OX + M.cast.centre[0]; cam.y = camT.y = OY + M.cast.centre[1] + 4 * Math.sin(1);
    S.cast = cast(); sea(); step();
    S.timer = setInterval(step, 100);
  }
  function stop() {                                          // you wake up, or watch: the island is forgotten, the world's land is asked for
    if (!S.on) return;
    S.on = false; clearInterval(S.timer);
    ents.clear(); blocks.clear(); dirtyTiles.length = 0; requested.clear(); lastWatch = ""; arrivingNow = true; fireAt = [];
    if (!me) { cam.x = camT.x = 0; cam.y = camT.y = 0; }
  }
  return {start, stop, get on() { return S.on; }, S};
})();
// It plays from the moment the pictures are loaded, while the first screen shows (not when you came to follow someone)
ready.then(() => { if ($("joinbox").style.display !== "none" && !new URLSearchParams(location.search).get("follow")) TitleScene.start(); });
new MutationObserver(() => { if ($("joinbox").style.display === "none") TitleScene.stop(); }).observe($("joinbox"), {attributes: true, attributeFilter: ["style"]});
