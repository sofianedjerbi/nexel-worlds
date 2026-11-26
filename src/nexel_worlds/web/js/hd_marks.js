// THE MARKS AND THE WORDS of the HD look (hd.js): what is pointed at and planned, and the letters, over the land's picture.
//   HdMarks(K) (K: the look's {api, seen, topAt, standAt, thing, under, shown, boxed}) -> {written(p, now, words)}

"use strict";
const HdMarks = (K) => {
  // what is written and pointed at, over the picture, by the game's own painters (names, a health bar, an emote, what is said, a progress bar): they were
  // drawn at the classic picture's places, under this one. Their sx, sy: someone's own place as this camera has it (found by its x, its y), else measured from you.
  // (two parts. marks: what is pointed at and planned (corners, ghosts, the build cursor), all in whole art px: on the world's own canvas with the land (hd_view.js marks): they move with every step you take,
  // and the game's canvas, the screen's size, was wiped and painted again for them each frame. words: the letters, on the game's canvas: yours stand still while you walk)
  function written(p, now, words) {
    const {api, seen, topAt, standAt, thing, under, shown, boxed} = K;   // (the look's own: hd.js H)
    if (p.free && !words) return;
    // (a body's place: View.of, by the body itself; one the frame did not draw (who speaks from past the picture's edge): where the camera has its tile's top. `sx.of`, `sy.of`: relief.js bodyX, bodyY)
    const S = 16 * View.u, F = (seen.me && View.of(seen.me.q)) || View.at(seen.at[0], seen.at[1], seen.at[2]).map(View.snap), place = (q) => View.of(q) || (View.at(q.x + .5, q.y + .5, topAt(Math.round(q.x), Math.round(q.y))) || F).map(View.snap);
    const sx = Object.assign((x) => F[0] - S / 2 + (x - p.x) * 16 * View.u, {of: (q) => place(q)[0] - S / 2}), fy = (y) => F[1] - S / 2 + (y - p.y) * 16 * View.u, sy = Object.assign(fy, {up: fy, out: fy, of: (q) => place(q)[1] - S / 2});
    const px = View.u, t = now / 1000, snap = View.snap, quad = (x, y, z) => [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => api.markOf(x + a, y + b, z));
    // (all of it in whole art px) corners: a quad's four corners, a third of each side; fill: a tile's face, row by row; ghost: a thing's own sprite where it would stand; rectOf: the px its picture takes
    const corners = (c, col) => { for (const [cl, o] of [["#5b3f36", px], [col, 0]]) { ctx.fillStyle = cl; c.forEach((a, i) => { for (const b of [c[(i + 1) % 4], c[(i + 3) % 4]]) { const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) * .3 / px)); for (let j = 0; j <= n; j++) ctx.fillRect(snap(a[0] + (b[0] - a[0]) * j / n * .3), snap(a[1] + (b[1] - a[1]) * j / n * .3) + o, px, px); } }); } };
    const fill = (c, col) => { ctx.fillStyle = col; const at = (a, b, y) => a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) || 1); for (let y = snap(c[0][1]); y < c[3][1]; y += px) { const l = snap(at(c[0], c[3], y)), r = snap(at(c[1], c[2], y)); ctx.fillRect(l, y, r - l, px); } };
    const rectOf = (spr, x, y, z = shown(x, y)) => { const f = api.screenOf(x + .5, y + 1, z), k = px; return [snap(f[0] - (8 - spr[5]) * k), snap(f[1] - (16 - spr[6]) * k), spr[3] * k, spr[4] * k]; };
    const edge = (a, b, col, dot) => { if (!a || !b) return; const n = Math.max(1, Math.ceil(Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) / px)); for (const [cl, o] of [["#5b3f36", px], [col, 0]]) { ctx.fillStyle = cl; for (let i = 0; i <= n; i++) if (!dot || (i >> 1) % 2 === 0) ctx.fillRect(snap(a[0] + (b[0] - a[0]) * i / n), snap(a[1] + (b[1] - a[1]) * i / n) + o, px, px); } };   // (a line in whole art px; dot: two on, two off)
    const ghost = (ch, x, y, a) => { const spr = ch && objectSprite(ch, x, y, t); if (!spr || !spr[0] || !spr[0].width) return; const r = rectOf(spr, x, y); ctx.globalAlpha = a; ctx.imageSmoothingEnabled = false; ctx.drawImage(spr[0], spr[1], spr[2], spr[3], spr[4], ...r); ctx.globalAlpha = 1; };
    // a cell of the land that would be dug into (keyboard.js `cell`: the wall beside you, at your level): its top, one level over your floor. (The corners sat on the wall's top: up at its ceiling, or on the meadow over it)
    const box = (r) => [[r[0], r[1]], [r[0] + r[2] - px, r[1]], [r[0] + r[2] - px, r[1] + r[3] - px], [r[0], r[1] + r[3] - px]], bound = (c) => { const xs = c.map((v) => v[0]), ys = c.map((v) => v[1]); return {x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys)}; };
    if (!words) { ctx.save(); const m = seen.me; if (m) HdLevel.cut(ctx, m, api.screenOf(m.x, m.y, m.z), zoom / seen.k); }   // (no mark lies on your body: hd_level.js cut)
    if (words) { const at = Build.on && Build.S.at, s = at && myPos(), r = at && Build.S.rect; if (s && r) { const L1 = Build.level(); Keyhole.mark(r.x, r.y, r.h, L1 - myZ(s.x, s.y), landSolid(at.x, at.y, L1) && landSolid(at.x, at.y, L1 + 1), sx, sy, r.right); } }
    else if (Build.on) {   // build mode: what is planned, each on its own tile at its own height as this camera has it, and the cursor (the game drew them at the classic picture's places)
      for (const j of Build.S.plans.values()) { const c = quad(j.x, j.y, j.z); if (c.some((v) => !v)) continue;
        if (j.item !== "ladder" && !j.take && !j.dig && !HdThings.pieced(j.item, j.steps, j.up ? j.z : undefined)) ghost(PLACEABLE_BLOCK[j.item], j.x, j.y, j.state === "doing" ? .75 : .5);   // (pieces: in the land, see-through: pieces())
        fill(c, j.state === "bad" ? "rgba(230,80,70,.4)" : j.take ? "rgba(255,150,60,.3)" : j.state === "doing" ? "rgba(255,241,168,.35)" : "rgba(140,190,255,.28)"); if (j.dig) fill(c.map((v, i) => [v[0] + (c[(i + 2) % 4][0] - v[0]) * .2, v[1] + (c[(i + 2) % 4][1] - v[1]) * .2]), "rgba(60,36,30,.5)"); }
      const at = Build.S.at; if (at) { const c = quad(at.x, at.y, Build.level()), it = Build.aim().it, mx = (myPos() || at).x; if (it && it.ghost && it.ghost !== "ladder" && it.ok !== false && !HdThings.pieced(it.ghost, it.steps, it.draw ? undefined : it.z)) ghost(PLACEABLE_BLOCK[it.ghost], at.x, at.y, .7);
        Build.S.rect = Object.assign(bound(c), {under: mx !== at.x, right: mx < at.x}); Prompts.build(); Target.paint(ctx, api.art());   // (the cursor's cell, the block X takes: boxes in the land, target.js)
        }
    } else {          // the aim: what stands there, round its picture; a ghost of what would be put; else the corners of the tile as the land shows it; its keys beside it (prompts.js)
      const aim = aimedTile(), it = aim && aim.it, a = aim && aim.p, on = a && tile(a.x, a.y) && it && !it.info && !it.walk; let r = null, thing = false;
      if (on && it.ghost && it.ghost !== "ladder" && !HdThings.pieced(it.ghost, it.steps, it.draw ? undefined : it.z)) ghost(PLACEABLE_BLOCK[it.ghost], a.x, a.y, .7);
      if (on) { const e = it.ent && seen.list.find((s) => s.q && s.q.e === it.ent || s.q === it.ent), c0 = combAt(a.x, a.y), spr = !e && c0 && isObject(c0) && objectSprite(c0, a.x, a.y, t), f = e && api.screenOf(e.x, e.y, e.z);
        const cs = !e && seen.list.find((s) => s.card && s.tx === a.x && s.ty === a.y), cf = cs && api.screenOf(cs.x, cs.y, cs.z), pb = !e && !cs && c0 && HdThings.is(c0, a.x, a.y) ? boxed(a.x, a.y, seen.L * RELIEF_STEP) || boxed(a.x, a.y) : null;   // (round the piece as it is drawn: a card's own px, the boxes' corners)
        const c = e ? box([snap(f[0] - 8 * px), snap(f[1] - 12 * px), 16 * px, 16 * px]) : cs && cf ? box([snap(cf[0] - (cs.fx - cs.card.b[0]) * px), snap(cf[1] - (cs.fy - cs.card.b[1]) * px), (cs.card.b[2] - cs.card.b[0]) * px, (cs.card.b[3] - cs.card.b[1]) * px])
          : pb ? box([snap(pb.x), snap(pb.y), snap(pb.w) + px, snap(pb.h) + px]) : spr && spr[0] ? box(rectOf(spr, a.x, a.y, standAt(c0, a.x, a.y) > floorAt(a.x, a.y) ? standAt(c0, a.x, a.y) : undefined)) : null; thing = !!c;
        if (c) corners(c, it.ok === false ? "#e8554a" : aim.brk ? "#ff9d3c" : "#fff8e8"); r = bound(c || quad(a.x, a.y, it.cell !== undefined ? it.cell : shown(a.x, a.y))); }
      Target.paint(ctx, api.art(), {thing, shown});   // (a cell of the land, what Space, X and R act on: boxes in the land, target.js; what stands keeps its brackets)
      WayShow.paint(ctx, api.markOf, px, now, 1, api.art().wall); Prompts.show(r, WayShow.rows(faceRows)); api.aim = r;   // (the way out of the ground, shown: wayshow.js)
    }
    if (!words) { ctx.restore(); Target.top(ctx); return; }   // (the selected cell at your body or over it: drawn over you, out of the cut: target.js)
    const nsy = {of: (q) => sy.of(q) - Math.max(0, 12 - 3 * zoom)};   // (a name: higher where an art px is small, a phone's 2 px: the letters are 18 px whatever the zoom, and seen from behind a body's ears were in its name)
    for (const s of seen.list) if (s.q && s.q.e && (s.q.e.kind === "agent" || s.q.e.name) && (s.top || !api.hidden(s.q.x + .5, s.q.y + .5, s.z))) drawNameplate(s.q, sx, nsy, S);   // (not over a roof its body is behind)
    for (const s of seen.list) if (s.q && s.q.e && (ANIMALS[s.q.e.kind] || !bubbles.some((b) => b.name === s.q.e.name))) drawEmote(s.q, sx, sy, S);
    drawProgress(sx, sy, S); HdFx.words(seen, api.screenOf); drawBubbles(sx, sy, S, t); ctx.textAlign = "start";   // (hearts lost, things gained: over heads, hd_fx.js)
  }
  return {written};
};
