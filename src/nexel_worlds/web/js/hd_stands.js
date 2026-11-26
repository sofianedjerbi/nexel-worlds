// WHAT STANDS in the HD look (hd.js), the list a frame draws over the land, north to south: things and furniture, a
// ladder about to be put, what lies on the ground, every body in view, a creature dying, and the effects (hd_fx.js).
//   HdStands(K) (K: the look's H) -> {stands(F)}: F the frame's own {p, tx, ty, L, Lf, w, h, now, dt, list, roof, wet, H0, fill, until, left, nw};
//   left and nw (the first screen's: hd.js) come back on F

"use strict";
const HdStands = (K) => {
  let cand = null, candKey = "";   // (what stands round you, looked for again when you or the land move: ck)
  const lads = new Map(), piles = new Map(), stoodOf = new Map();   // (a ladder's picture, a pile's, a thing's last entry)
  // things and furniture round you, and a ladder about to be put (its standing face where it will stand)
  function things(F) {
    const {p, tx, ty, L, Lf, w, h, now, dt, list, roof, wet, H0, fill, until} = F;
    let {left, nw} = F;
    const {api, eng, ent, seen, solidAt, south, sprs, standAt, thing, topAt, warm, R, gen, EDGE, byY, cutOff, winMap, winRect} = K;
    const stood = (c, x, y, z, gh, m) => {      // a thing that stands: furniture as its card (hd_things.js: px for px, its top leaning with where it is on the screen), the rest a billboard
      if (c === "l") { const k = [x, y, z, landVer, Floors.ver].join(), ln = Climb.lean(x, y, z); let lc = lads.get(k); if (!lc) { if (lads.size > 60) lads.clear(); const LH = Math.ceil((shOf(ln ? ln.top - z : 2) + 48) / 16) * 16, R0 = LH - 32, a = HdThings.painted(48, LH, () => Climb.drawLadder(x, y, z, (X) => 16 + (X - x) * 16, (Y) => R0 + (Y - y) * 16 + shOf(z), 16, 1)); lc = document.createElement("canvas"); lc.width = 48; lc.height = LH;
        const q = lc.getContext("2d"); q.drawImage(a, 0, 0, 48, R0 - 10, 0, 12, 48, R0 - 10); q.drawImage(a, 0, R0 + 2, 48, LH - R0 - 2, 0, R0 + 2, 48, LH - R0 - 2); lads.set(k, lc); }   // (the game's picture of it runs 12 px on, a tile's depth in the classic picture: here it stood over the rim. Three rungs taken out of its middle; its canvas as tall as the wall it leans on: a deep shaft's ladder was cut at 128 px)   // (a ladder: a standing face of the land, a px of it a px of the land's own fronts: as tall as the wall it leans on at any pitch. Upright px for px it stood three tiles over the rim of a shaft)
        list.push({canvas: lc, fx: 24, fy: lc.height - 16, x: x + .5, y: HdLevel.foot(ln && ln.dy < 0 ? "ladderN" : ln && ln.dy > 0 ? "ladderS" : "ladder", x, y)[1], z, flat: true, still: true, d: true, tx: x, ty: y, ghost: gh}); return; }
      const o = m || {}, s0 = objectSprite(c, x, y, now / 1000, o.out || (o.out = [])); if (!s0 || !s0[0] || !s0[0].width) return;   // (written into the thing's own array: seven numbers a thing a frame were made)
      if (o.it && o.img === s0[0] && o.sx === s0[1] && o.sy === s0[2] && o.sw === s0[3] && o.sh === s0[4] && o.dx === s0[5] && o.dy === s0[6]) { o.it.fade = undefined; list.push(o.it); return; }   // (m: what this thing was last drawn as (cand): the same picture, the same entry. Its card, foot, bounds and canvas were looked for again for every thing, every frame: a fifth of a still frame's script)
      const s = s0.slice(), cd = HdThings.card(c, x, y, s);   // (a copy of its own for what keeps it)
      const r2 = cd || c === "g" ? 0 : HdThings.foot(c, s), plain = cd || c === "g" ? null : {fy: r2, card: {b: spriteBounds(s[0], s[1], s[2], s[3], s[4]) || [0, 0, s[3], s[4]]}};   // (each stands where its foot is in its tile, as the game has it: they stood at the tile's south edge, their feet half a tile north of their shadow)
      const it = Object.assign(cd ? {} : thing(s), cd, {x: x + .5, y: y + (cd ? cd.y : plain ? (s[6] + r2) / 16 : 1), z, lamp: Light.lamp(c), flat: c === "g", tx: x, ty: y, card: cd}, plain);   // (flat: a gate: a standing face of the land a tile wide, vox_style.js)
      Object.assign(o, {img: s[0], sx: s[1], sy: s[2], sw: s[3], sh: s[4], dx: s[5], dy: s[6], it}); list.push(it);
    };
    const memo = (c, x, y, z) => { const k = c + "," + x + "," + y + "," + z; let o = stoodOf.get(k); if (!o) { if (stoodOf.size > 6000) stoodOf.clear(); stoodOf.set(k, o = {}); } return o; };   // (a thing's last entry, found when what stands is looked for, not each frame)
    const ck = [tx, ty, L, landVer, Floors.ver, api.builds, !!gen, Math.floor(now / 250)].join();   // (what stands: looked for four times a second and when you or the land move, not on 2400 tiles every frame)
    if (ck !== candKey) { candKey = ck; cand = []; for (let y = ty - R; y <= ty + south; y++) for (let x = tx - R; x <= tx + R; x++) {
      const c = combAt(x, y), up = Floors.any(x, y) ? HdThings.loose(x, y) : null; if (up) for (const [ch, z] of up) if (!cutOff(x, y, z)) cand.push([ch, x, y, z, memo(ch, x, y, z)]);   // (what stands on a built block)
      if (c && isObject(c) && !HdThings.is(c, x, y)) { const z = standAt(c, x, y); if (!cutOff(x, y, z)) cand.push([c, x, y, z, memo(c, x, y, z)]); }      // (not the boxes of the land: hd_things.js)
    } }
    { const wmp = winMap(); HdEase.frame(now); for (const [c, x, y, z, m] of cand) { const n0 = list.length, a = z > floorAt(x, y) ? HdEase.of(m.ek || (m.ek = x + "," + y), !wmp.has(m.ek)) : 1; if (a > 0) { if (fill && warm < 2 && !m.it && (warm < 1 || (nw && performance.now() > until))) left = true; else { nw += fill && !m.it ? 1 : 0; stood(c, x, y, z, false, m); } } if (a < 1) for (let i = n0; i < list.length; i++) list[i].fade = a; } }   // (what grows on ground the window leaves out is left out with it: one px in two of a flower hung over your room's floor; it goes and comes over 120 ms, hd_ease.js: a tree over your room was gone in one frame)
    // a ladder that would be put (the aim's, on your own tile in a shaft; build mode's plans): the ladder's own standing face where it will stand, as tall as its wall, pale (it was an upright picture laid over the frame: at 68 degrees two tiles over the shaft's rim, and not where the ladder comes)
    { const a = Build.on ? Build.aim() : aimedTile(), it = a && a.it, q = it && (it.own || a.p); if (q && it.ghost === "ladder" && it.z !== undefined && it.ok !== false && !it.info) stood("l", q.x, q.y, it.z, true);
      if (Build.on) for (const j of Build.S.plans.values()) if (j.item === "ladder" && !j.take && j.state !== "bad") stood("l", j.x, j.y, j.z, true); }
    F.left = left; F.nw = nw;
  }
  // what lies on the ground: a pile of up to three things
  function ground(F) {
    const {p, tx, ty, L, Lf, w, h, now, dt, list, roof, wet, H0, fill, until} = F;
    let {left, nw} = F;
    const {api, eng, ent, seen, solidAt, south, sprs, standAt, thing, topAt, warm, R, gen, EDGE, byY, cutOff, winMap, winRect} = K;
    for (const [ix, iy, pile] of groundItems) if (Math.abs(ix - tx) <= R && iy >= ty - R && iy <= ty + south && !lootAt(ix, iy)) {   // (its drops still hopping in: the pile once they have landed, hd_fx.js)   // what lies on the ground: its small icons as the game lays them (loot.js), a px a px (they were not drawn in this look)
      const names = Object.keys(pile).slice(0, 3), k = names.join(); let c = piles.get(k);
      if (!c) { c = document.createElement("canvas"); c.width = 24; c.height = 16; const g = c.getContext("2d"); names.forEach((n, i) => { const [dx, dy] = pileAt(i, names.length); g.drawImage(ghostIcon(n), 7 + dx, 3 + dy); }); piles.set(k, c); }
      list.push({canvas: c, fx: 12, fy: 14 + Math.round(Math.sin(now / 1000 * 2.4 + ix * 1.3 + iy) + 1), still: true, d: true, pile: true, x: ix + .5, y: HdLevel.foot("pile", ix, iy)[1], z: floorAt(ix, iy)});   // (it hovers, as in the classic picture: 0 to 2 px, a whole px at a time)
    }
    F.left = left; F.nw = nw;
  }
  // every body in view, a creature dying, what moves by itself (hd_fx.js); then all of it north to south
  function bodies(F) {
    const {p, tx, ty, L, Lf, w, h, now, dt, list, roof, wet, H0, fill, until} = F;
    let {left, nw} = F;
    const {api, eng, ent, seen, solidAt, south, sprs, standAt, thing, topAt, warm, R, gen, EDGE, byY, cutOff, winMap, winRect} = K;
    const wmB = winMap(), wr = wmB.size ? winRect() : null;   // UNDER A ROOF nobody up on the land over you is seen: over the window, or over the land round it (in the window's box on the screen); only who is in your space (like Minecraft: no mob through the ceiling)
    // (who is drawn: whoever's feet are on the picture, or EDGE art px off it (in view a step before it comes in), where it stands as the land is drawn: the bend sinks both alike, so past the horizon the land in front
    //  hides it as it hides its land. It was a box: 16 across, then the land's; 12 rows north whatever the screen: on a hill's side 26 rows off, on a phone held upright 17, a mob went out of being in view)
    for (const q of ents.values()) if (q.x !== undefined && Math.abs(q.x - p.x) <= R + 40 && q.y - p.y >= -R - 40 && q.y - p.y <= south + 8) {
      if (fill && warm < 2) continue; if (fill && !sprs.has(q) && nw && performance.now() > until) { left = true; continue; } if (fill && !sprs.has(q)) nw++;   // (the first screen's people: after what stands, 8 ms of new ones a frame)
      const qx = Math.round(q.x), qy = Math.round(q.y), pl = BodyPlace.of(q), z = q === p ? Lf : Floors.standOf(q, qx, qy);   // (the ground of the tile it is drawn on, as the game has it (floors.js standOf): on a built floor, in a cave, off a hill's foot. They were put on the land's top: a friend in your room stood on the grass over it)
      if (q !== p && seen) { const a = eng.at(q.x + .5, q.y + .5, z); if (!a || a[0] < -EDGE || a[0] > w + EDGE || a[1] < -EDGE || a[1] > h + 2 * EDGE) continue; }
      if (q !== p && z < topAt(qx, qy)) { const c = H0.column(qx, qy), b = winMap().get(qx + "," + qy); let over = false; for (let zz = z + 1; zz <= topAt(qx, qy) && !over; zz++) over = solidAt(c, zz); if (over && !(b && z >= b[0] - 1 && z <= b[1])) continue; }
      if (q !== p && wmB.size) { const b = wmB.get(qx + "," + qy), a = !b && eng.at(q.x + .5, q.y + .5, z); if (!(b ? z >= b[0] - 1 && z <= b[1] : Math.abs(z - L) <= 1) && (b || (a && wr && a[0] + 6 > wr[0] && a[0] - 6 < wr[2] && a[1] > wr[1] && a[1] - 14 < wr[3]))) continue; }   // (not in your space: on the window's tile at another level, or its body in the window's box: hidden, its name with it. It was drawn, the ground under its feet kept one px in two: a hen over your head read as in the cave with you)   // (under land the window is not on: not seen, nor their name)
      const [bx, by] = HdLevel.foot("body", q.x, q.y), s = ent(q, now, z);   // (another: its body on its own line (body_place.js), its ground the tile it is nearest. The server's level for it came at once, a level up as a step began)
      list.push({canvas: s.canvas, fx: s.fx, fy: s.fy, fo: s.fo, air: s.air, x: bx, y: by, z: q === p ? z : pl.line, zs: q === p ? (Leap.on() ? Leap.level()[0] : L) : z, d: q !== p, top: q === p, on: true, q, lamp: q.e && q.e.kind === "agent" ? Light.lamp("person", q === p && roof) : 0});   // (under the land your lantern is the light)   // (you: never hidden by land)
      const wk = q.wake && q.wake.length && wakePicture(q, now);   // (a swimmer's wake: a picture of its own lying on the water, no shadow)
      if (wk) list.push({canvas: wk.canvas, fx: wk.fx, fy: wk.fy, x: bx, y: by, z, lie: true});
    }
    // A CREATURE DYING (effects.js dying, state.js: its body as it was when it died): its own picture, white for a moment, lifting a third of a tile and fading inside its puff of smoke. (Only the classic
    // picture drew it: here the body was gone in one frame, the smoke alone left)
    for (const d of dying) { const k = Math.max(0, Math.min(1, (now - d.t0) / DIE_MS)), q = d.p, qx = Math.round(q.x), qy = Math.round(d.y0), z = typeof q.e.z === "number" && !H0.water(qx, qy) ? q.e.z : Math.max(topAt(qx, qy), wet(qx, qy)), s = ent(q, now, z, k < .3 ? .8 : .35);
      list.push({canvas: s.canvas, fx: s.fx, fy: s.fy + Math.round(k * .35 * 16), x: HdLevel.foot("body", q.x, d.y0)[0], y: HdLevel.foot("body", q.x, d.y0)[1], z, d: true, on: true, fade: 1 - k * k, dying: true}); }
    HdFx.add(list, p, now, dt);   // (what moves by itself: chips, smoke, drops, orbs, flames, a tree falling: hd_fx.js)
    byY(list);   // (north to south, as Array sort by y did, its order kept among equals)
    F.left = left; F.nw = nw;
  }
  function stands(F) { things(F); ground(F); bodies(F); }
  return {stands};
};
