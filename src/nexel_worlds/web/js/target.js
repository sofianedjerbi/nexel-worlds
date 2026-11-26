// What a key will act on, shown as the CELL it is ("block selection / placing looks confusing: i dont know which level
// am i interacting with. eye-level ? feet level ? air ? real block ?"). The marks were flat: brackets round a tile,
// a flat cursor, dashes at one place of the screen: the ground before you, a wall's top, the cell at your head and
// an empty cell in the air looked the same. One language now, out of build mode and in it (the HD look's marks pass,
// hd.js; the classic picture keeps its own):
//   - a cell is the BLOCK it is on the screen: the art px the land paints it with (its faces turned to the eye, by the
//     land's own rule, `pxOf`); a 1 px line in the key's colour on its outermost px and on its top/front seam, ink
//     inside that line, its faces its own paint faintly tinted (`outline`): nothing of it outside the block;
//   - Space puts a block there ("place"): cream; the block itself in it at 60 % (buildghost.js); red where it cannot go;
//   - orange: a key takes that block ("break": X, R or a pickaxe's Space), the block itself, not air.
//   - Space does something to that block ("use": till it, lay a floor in it, a thing put on it): cream, its top;
//   - DOTTED means one thing: out of reach yet (build mode: a block in the ground with no air beside it nor a dig planned
//     beside it; a block to place that nothing holds yet, built or planned beside or under it); reachable is a whole line. Behind land a box is not drawn, unless all of it is: then its whole line, seen through;
//   - a cell nothing stands under: a dotted line down to the ground under it and its shadow there, one px in two;
// `cells()` is the one answer to "which cell": what is drawn is what the key sends (tests: the drawn cell is the
// cell that changes). X's block under you: its own mark, round your feet (`feet`). `target(key)`: the cell of Space ("use"), X ("alt") or R ("up").
const Target = (() => {
  const api = {drew: [], opts: {}};
  // -> [{key: "use" | "alt" | "up", kind: "place" | "break" | "use", x, y, z: the level of its top, h: levels tall, ok, item}]
  function cells() {
    const s = typeof me !== "undefined" && me && meObs ? myPos() : null, out = [];
    if (!s) return out;
    if (api.show) return api.show.map((c) => ({key: "use", h: 1, ok: true, ...c}));   // (tests: these cells drawn, not the keys')
    const add = (key, kind, x, y, z, more) => { if (!out.some((c) => c.x === x && c.y === y && c.z === z && c.kind === "break")) out.push({key, kind, x, y, z, h: 1, ok: true, ...more}); };
    if (Build.on) {
      const p = Build.S.at, it = Build.hint(p), hit = Build.taking(p), L = Build.level();
      if (hit && !hit.plan) add("alt", "break", p.x, p.y, hit.dig || hit.up ? hit.z : hit.z + 1, hit.shut ? {far: true} : hit.dig || hit.up ? {} : {h: 1, thing: true});   // (a thing that stands: a block high, hd_things.js. far: out of reach yet, no air beside it nor a dig planned beside it (build.js `open`, the rule the work goes by): its box dotted)
      const q = it.at || p, far = it.far ? {far: true, ok: true} : {ok: it.ok !== false};      // (q: the cell beside the face the mouse is on, build.js; far: nothing holds it yet: dotted, no ghost in it)
      if (it.ghost && it.z !== undefined && !it.steps && it.ghost !== "ladder") add("use", solidAt(q.x, q.y, it.z) ? "use" : "place", q.x, q.y, it.z, {item: LAND_BLOCKS.has(it.ghost) && !it.far ? it.ghost : null, drawn: LAND_BLOCKS.has(it.ghost), ...far});
      else add("use", solidAt(p.x, p.y, L) ? "use" : "place", p.x, p.y, L, {flat: !!it.ghost && solidAt(p.x, p.y, L), ...far});
      return out;
    }
    // (the keys act whether the way out is shown or not: what each would take is drawn; the way's own block is drawn by wayshow.js: one mark. keyboard.js `useFacing`, digup.js `route`)
    const keys = byKeys(), h = myZ(s.x, s.y), way = keys ? WayShow.offer() : null, wc = WayShow.cur, nx = wc && wc.next, now = wc && wc.now;
    const ways = (x, y, z) => !!nx && nx.x === x && nx.y === y && nx.z === z;
    const at = !keys && mouse.in ? tileAtScreen(mouse.x, mouse.y) : null;      // (the mouse: E's box on what a right click uses, X's on what a left click breaks)
    const a = keys ? facedOnly(facingIntent(false)) : at && clickIntent(at, "use"), it = a && a.it, p = a && a.p, up = keys ? DigUp.aim() : null;
    const x0 = keys ? facingIntent(true) : at && clickIntent(at, "break"), alt = x0 && !x0.it.info && !x0.it.walk && x0.it.ok !== false && !x0.it.gather ? x0 : null;
    if (way && way.key === "alt" && now && now.down) add("alt", "break", s.x, s.y, h, {mine: true});      // the way out's X: the block you stand on
    if (up) add("up", "break", up.x, up.y, up.z, {way: ways(up.x, up.y, up.z)});                                   // R: the block it cuts
    if (way && way.key === "alt" && now && !now.down) add("alt", "break", now.x, now.y, now.z, {way: ways(now.x, now.y, now.z)});      // the way out's X: the wall in front
    if (it && p && tile(p.x, p.y) && !it.info && !it.walk) {
      const wetFill = !!it.ghostGround && wet(gndAt(p.x, p.y) || "");
      if (wetFill) add("use", "use", p.x, p.y, topAt(p.x, p.y) - WaterBed.would(p.x, p.y, it.ghostGround), {ok: it.ok !== false, flat: true});   // (earth into water: the tile's water gets shallower: the mark lies where its bed will be, seen through the water; the face when no bed is seen)
      else if (LAND_BLOCKS.has(it.ghost)) add("use", "place", p.x, p.y, it.z !== undefined ? it.z : topAt(p.x, p.y) + 1, {ok: it.ok !== false, item: it.ghost});
      else if (!api.opts.thing && !it.ent && !it.steps) add("use", "use", p.x, p.y, it.z !== undefined ? it.z : api.opts.shown ? api.opts.shown(p.x, p.y) : settleNear(p.x, p.y, h), {ok: it.ok !== false, flat: true});
    }
    if (!(way && way.key === "alt") && alt && alt.it.cell !== undefined) add("alt", "break", alt.p.x, alt.p.y, alt.it.cell);   // X: the block you face, its box (keyboard.js digAhead)
    else if (!(way && way.key === "alt") && alt && !alt.it.ent && !alt.it.self) {      // X: the thing it takes apart (a rock, a tree, a chest, a wall), the block it stands in; a path: its own block
      const z = alt.it.z !== undefined ? alt.it.z : alt.it.at !== undefined ? alt.it.at : floorAt(alt.p.x, alt.p.y);
      add("alt", "break", alt.p.x, alt.p.y, alt.it.ground ? z : z + 1, alt.it.ground ? {} : {thing: true});
    }
    return out;
  }
  api.cells = cells;
  api.target = (key = "use") => { const c = cells().find((q) => q.key === key); return c ? {x: c.x, y: c.y, z: c.z, kind: c.kind, ok: c.ok} : null; };

  // WHAT IS KEPT OF A CELL's box from frame to frame (its px, its outline's px, its place and box on the screen), while nothing it is made from changes: where the land is drawn (view: HdLook.art, the
  // camera's numbers), the land and what is built (landVer, Floors.ver), behind-land on or off, the cell itself. Worked out again each frame, it would make 5 MB in 3 s standing still for the collector
  const keep = new Map();
  function kept(view, behind, c) {
    const k = view + "|" + landVer + "|" + Floors.ver + "|" + (behind ? 1 : 0) + "|" + c.kind + "|" + c.x + "," + c.y + "," + c.z + "," + (c.h || 1) + (c.flat ? "f" : "") + (c.ok === false ? "n" : "") + (c.far ? "d" : "");
    let K = keep.get(k); if (!K) { if (keep.size > 24) keep.clear(); keep.set(k, K = {}); } return K;
  }
  // a rect (the canvas's units) lies on a box drawn, or on the way's block (your own name is not written there: characters.js)
  api.over = (x, y, w, h) => [...api.drew.map((d) => d.r), typeof WayShow !== "undefined" && WayShow.block].some((r) => r && x < r.x + r.w && r.x < x + w && y < r.y + r.h && r.y < y + h);
  // once a frame, in the marks pass: g, what a painter of marks needs (HdLook.art()), opts: {thing: what is aimed at stands (its own brackets), shown(x, y): a tile's level as the picture has it}
  // THE SELECTED CELL (the one the key in focus acts on: build mode the cursor's, else E's when it puts a block, else X's, else E's): its box always whole
  // ("which level am I interacting with?": a box at your body's cell or over your head was cut out of your sprite, or not drawn). At your body or over it:
  // drawn over you, your sprite seen through it (top()); under you: a box under your feet, your sprite in front of it whole. And your body aims at it (aim_art.js)
  // (an empty paw: E's only, what it would use: X's ground before you is always there, and you looked down at the grass wherever you stood)
  const pick = (cs) => (Build.on ? cs.find((c) => c.z === Build.level()) || cs.find((c) => c.key === "use") || cs.find((c) => c.key === "alt")
    : cs.find((c) => c.key === "use" && c.kind === "place") || (typeof selected !== "undefined" && selected ? cs.find((c) => c.key === "alt") : null) || cs.find((c) => c.key === "use")) || null;
  // -> "up" | "ahead" | "down" | null: the selected cell against your body's cell (one over your floor)
  function aimOf(c) { const s = c && myPos(); if (!s) return null; const lv = c.z - (myZ(s.x, s.y) + 1); return lv > 0 ? "up" : lv < 0 ? "down" : "ahead"; }
  api.aim = null; api.sel = null; api.late = null;
  api.top = (g) => { const L = api.late; api.late = null; if (!L) return; api.drew.push({...TargetBox.box(L.Q, L.c, L.K), key: L.c.key, px: L.px, u: L.Q.u, r: L.r, over: true}); };
  api.paint = (g, art, opts = {}) => {
    api.opts = opts; api.drew = []; api.late = null; api.sel = null; api.aim = null;
    if (!art || api.off) return;   // (off: tests that count a ghost's own px)
    const s = myPos(), open = HdLook.win && HdLook.win.n && HdLook.win.a > 0, P = {g, u: art.u, at: art.at, behind: open ? null : art.behind, ex: s ? s.x + .5 : 0}, B = art.body;
    // (your sprite's box: nothing of a box is drawn in it, and out of build mode a box that shares much of it (40 % of the smaller of the two) is not drawn at all: the cell north of you, under your head from above, was a square round your head)
    const inB = (r) => (B && r ? Math.max(0, Math.min(r.x + r.w, B.x + B.w) - Math.max(r.x, B.x)) * Math.max(0, Math.min(r.y + r.h, B.y + B.h) - Math.max(r.y, B.y)) / Math.max(1e-6, Math.min(r.w * r.h, B.w * B.h)) : 0);
    const all = cells(), sel = pick(all), me0 = myPos(), own = !!sel && !!me0 && sel.x === me0.x && sel.y === me0.y, after = [];
    api.sel = sel; api.aim = aimOf(sel);
    g.save(); if (B) { g.beginPath(); g.rect(-1e5, -1e5, 2e5, 2e5); g.rect(B.x, B.y, B.w, B.h); g.clip("evenodd"); }
    for (const c of all.sort((a, b) => a.y - b.y || (a.kind === "break") - (b.kind === "break") || a.z - b.z)) {
      const W = art.wall && art.wall(c.x, c.y, c.z), Q = W ? {...P, at: W, behind: null} : P, K = W || !art.view ? null : kept(art.view, !!P.behind, c), px = K ? K.px || (K.px = Q.at(c.x, c.y, c.z)) : Q.at(c.x, c.y, c.z);   // (a cell in the wall between the eye and you: drawn as its face folded into the opening, seen: hd_level.js wallAt)
      const r = K ? (K.r === undefined ? (K.r = TargetBox.boxRect(Q, c)) : K.r) : TargetBox.boxRect(Q, c);
      if (c.mine) { api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, mine: true, px, u: P.u}); continue; }
      if (c.way) { api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, way: true, px, u: P.u}); continue; }   // (wayshow.js draws that block)
      // (a block to put where you stand, your body's cell or your head's: it cannot go, you are in it. Not an error: cream dotted, "can't" (not red, the
      // first thing seen in a shaft); red is for a place that is wrong)
      if (c === sel && !c.mine && !c.way) { const you = own && c.kind === "place" && c.ok === false && c.z - myZ(me0.x, me0.y) <= 2 ? {far: true, item: null} : {};
        if (own && api.aim !== "down") api.late = {Q, c: {...c, over: true, ...you}, K, r, px}; else after.push([Q, c, K, r, px]); continue; }   // (yours: no cut, no skip)
      if (!Build.on && inB(r) > .4) { api.drew.push({x: c.x, y: c.y, z: c.z, kind: c.kind, key: c.key, under: true, px, u: P.u}); continue; }
      if (c.kind === "place" && c.item && !c.drawn) BuildGhost.block(g, Q.at, Q.u, c.x, c.y, c.z, c.item, .6, c.ok === false, Q.behind);
      api.drew.push({...TargetBox.box(Q, c, K), key: c.key, px, u: P.u, r});
    }
    g.restore();
    for (const [Q, c, K, r, px] of after) { if (c.kind === "place" && c.item && !c.drawn) BuildGhost.block(g, Q.at, Q.u, c.x, c.y, c.z, c.item, .6, c.ok === false, Q.behind); api.drew.push({...TargetBox.box(Q, c, K), key: c.key, px, u: P.u, r, sel: true}); }
  };
  return api;
})();
