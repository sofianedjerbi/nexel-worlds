// THE LAMPS of the HD look (hd.js): the hour's light on the land, and each lamp's light in it, as daylight.js Light says them.
//   HdLamps(K) (K: the look's {api, eng, winMap, topAt}) -> hour(w, h, list, k: the eye's climb a tile, relief.js eyeRise)
const HdLamps = (K) => {
  let lit = null;
  // the hour's light on the land: the game's own (daylight.js Light: its tint, its wash, a lamp on each of you and each fire, in whole steps), put where this camera
  // puts them. (Not the shader's `day` alone: that leaves the night's land as bright as noon under a night sky.) -> {wash, lit: the light's picture}
  // for the land's own painter to lay over what it draws (vox_style.js `hour`), or nothing at plain day
  const SOFT = Array(24).fill(.01);   // (a lantern under the sky: 24 rings of a hundredth each: none is seen, the light fades out)
  function hour(w, h, list, k) {
    const H = Light.now(), {wash, dark} = H;   // (the hour's light: daylight.js Light)
    if (wash[3] <= .004 && dark <= .01) return null;
    if (!H.lamps) return {wash, tint: H.lit};   // (no lamp shows: one colour, a px of it, not a picture the screen's size sent to the GPU every frame of a morning)
    lit = lit || document.createElement("canvas"); if (lit.width !== w || lit.height !== h) { lit.width = w; lit.height = h; lit._k = ""; }
    // (a lamp under the open sky that the land south of it hides from the eye lights nothing: a campfire behind a hill lit the hill's face and the meadow in front, a round glow
    //  through the land read as the moon's. HdLevel.over: as a body there is hidden, hd.js. You are never hidden (the window); one under the land is cut to the window, below)
    const on = list.filter((s) => { if (!s.lamp || s.top) return !!s.lamp; const x = Math.floor(s.x), y = Math.floor(s.y), z = s.zs ?? s.z; return K.topAt(x, y) > z || HdLevel.over(x, y, z, k) < 1; });
    const lamps = []; for (const s of on) { const a = K.eng.at(s.x, s.y, s.z); if (a) lamps.push(Math.round(a[0] * 4), Math.round(a[1] * 4), s.lamp); }
    self.__litCanvas = lit;
    self.__lampsDbg = {n: list.filter((s) => s.lamp).length, on: on.map((s) => [s.lamp, s.top ? 1 : 0, s.top ? +!!HdLevel.cover.roof : +(K.topAt(Math.floor(s.x), Math.floor(s.y)) > (s.zs ?? s.z))]), at: lamps.slice(), lit: H.lit.join(), open: +H.open.toFixed(2), k: +H.k.toFixed(2), v: lit._v || 0};
    const lk = [H.lit, dark.toFixed(3), lamps, K.api.builds].join(), out = {wash, lit}; if (lk === lit._k) return out; lit._k = lk; lit._v = (lit._v || 0) + 1;   // (the same lamps at the same places: the picture there is this frame's: not painted, not sent again)
    const q = lit.getContext("2d"); q.globalAlpha = 1; q.globalCompositeOperation = "source-over"; q.fillStyle = `rgb(${H.lit.join()})`; q.fillRect(0, 0, w, h); q.globalCompositeOperation = "lighter";
    for (const s of on) { const a = K.eng.at(s.x, s.y, s.z), cl = s.top ? HdLevel.cover.roof : K.topAt(Math.floor(s.x), Math.floor(s.y)) > (s.zs ?? s.z); if (s.top) K.api.youLit = !cl || !!K.winMap().size;   // (zs: the ground's level. A step up or down drew you between two levels: the tile's top over that, your lantern was cut to a window there was none of: gone the time of the step)
      if (!a) continue; if (cl) { q.save(); winPath(q, Math.floor(s.x), Math.floor(s.y)); q.clip(); }   // (a light under the land, your lantern, a fire in your room, lights what the window shows, not the grass over it: a campfire 14 levels down lit a ring on the meadow)
      if (s.lamp > 1 || cl) lamp(q, a[0], a[1] - 8, s.lamp > 1 ? 64 : 42, s.lamp > 1 ? "rgb(255,176,96)" : "rgb(255,222,170)", (s.lamp > 1 ? 1.15 : .45) * H.k, [0, 0]);
      else if (H.open > 0) lamp(q, a[0], a[1] - 8, 72, "rgb(255,232,200)", H.open, [0, 0], SOFT);   // (a lantern under the sky: only once the night is in (the sun down), less with "Light at night", in 24 steps of a hundredth: the land by you a little lighter, no ring, no disc. Not rings from a fifth of dark on: a yellow halo on a meadow still in the sunset's light)
      if (cl) q.restore(); }
    q.globalAlpha = 1; return out;
  }
  // the px of the picture the window shows round (tx, ty): each of its tiles' floor, and the walls north and beside it up to its ceiling: a path on q
  function winPath(q, tx, ty) {
    q.beginPath(); const quad = (l) => { const a = l.map((v) => K.eng.at(...v)); let ar = 0; for (let i = 0; i < 4; i++) ar += a[i][0] * a[(i + 1) % 4][1] - a[(i + 1) % 4][0] * a[i][1]; if (ar < 0) a.reverse(); q.moveTo(...a[0]); for (let i = 1; i < 4; i++) q.lineTo(...a[i]); q.closePath(); };
    for (const [x, y, lo, hi] of K.eng.win.tiles) if (Math.abs(x - tx) <= 9 && Math.abs(y - ty) <= 9) { quad([[x, y, lo], [x + 1, y, lo], [x + 1, y + 1, lo], [x, y + 1, lo]]);
      for (const e of [[[x, y], [x + 1, y]], [[x, y], [x, y + 1]], [[x + 1, y], [x + 1, y + 1]]]) quad([[...e[0], lo], [...e[1], lo], [...e[1], hi], [...e[0], hi]]); }
  }
  return {hour};
};
