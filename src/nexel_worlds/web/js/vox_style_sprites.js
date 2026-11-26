// VOX's sprites (vox_style.js draw): what stands and walks, drawn px for px. Their pictures have places in one sheet
// (shelves), each sent when it is new or changed; this frame's sprites are one list of vertices and its runs.
//   VoxStyleSprites.create(K) -> {list(v, m, mp, last) -> the frame's list, or null: the sheet is full (reset(), then
//     ask again), reset(): every place given again (a lost context, a full sheet)}
//   K: {projTo, PJ: a place's clip coordinates into PJ (vox_style.js), up: a level's px of paint (cfg.up),
//       wmap, wrim: the x-ray window's boxes and the level of the land round your hole (a sprite in it is as dim as its floor)}
//   v: draw's view; m: its matrix; mp: your px (what stands south of you over it is drawn one px in two); last: the
//   list the last frame drawn (the one not to write into)
// the sprites' sheet: each canvas has a place in it (shelves), its picture sent there when it is new or changed (canvas._v); full: all places given again
// a sprite that stands in the window (a body, a chest, a mushroom in your room): as dim as the floor under it (the painter's own numbers for a floor, vox_style_glsl.js: by how deep it lies under the rim, and past 2.5 and 4.5 tiles from you); you: never
// (in a dim deep room they glowed: full day's colours on a floor at .6)
// this frame's sprites as one list of vertices (x, y, z, u, v, sil, dim, fade: how much of it is there, 0..1: a 2x2 dither in four steps) and its runs: [first vertex, count, how: 0 as the land hides it, 1 you: whole where nothing hides you, one px in two where land does]
// (TWO BUFFERS, swapped: a frame's vertices go into the one the last frame drawn (lastS) is not, grown only when too small; the lists, runs and corners are kept and written over.
//  not a new Float32Array and a few small arrays a sprite, each frame: 8 to 11 MB in 3 s standing still for the collector to take back, a phone's stutter)
const VoxStyleSprites = (() => {
  const C = 16, SW = 1024, SV6 = 8;   // (C: art px a tile; SW: the sheet's side; SV6: numbers a vertex)
  function create(K) {
    const {projTo, PJ, up} = K;
    const shelf = {x: 0, y: 0, h: 0, ep: 1};
    function place(c) {
      let a = c._a; if (a && a.ep === shelf.ep && a.w === c.width && a.h === c.height) return a;
      if (shelf.x + c.width + 1 > SW) { shelf.x = 0; shelf.y += shelf.h + 1; shelf.h = 0; }
      if (shelf.y + c.height + 1 > SW) return null;
      a = c._a = {x: shelf.x, y: shelf.y, w: c.width, h: c.height, ep: shelf.ep, v: -1}; shelf.x += c.width + 1; shelf.h = Math.max(shelf.h, c.height); return a;
    }
    function dimOf(s, v) { if (!K.wmap.size) return 1; const b = K.wmap.get(s.tx === undefined ? Math.floor(s.x) + "," + Math.floor(s.y) : s.tx + "," + s.ty); if (!b || s.z < b[0] - 1 || s.z > b[1]) return 1; const D = Math.max(0, Math.min(16, K.wrim - s.z)), pd = Math.hypot(s.x - v.at[0], s.y - v.at[1]); return Math.max(.7, (1 - .025 * Math.min(6, D)) * (1 - .25 * Math.max(0, Math.min(1, (D - 3) / 9)) * (pd < 2.5 ? 0 : pd < 4.5 ? .5 : 1))); }   // (never under .7: it is still read)
    const SB = [new Float32Array(4096), new Float32Array(4096)], ORD = [[], [], [], []], ON = [0, 0, 0, 0], RUN = [[], [], [], []], UPS = [], QX = new Float64Array(4), QY = new Float64Array(4), QZ = new Float64Array(4), BX = new Float64Array(4);
    const S6 = [0, 1, 2, 0, 2, 3], CU = [0, 1, 1, 0], CV = [0, 0, 1, 1], QA = [-1, 1, 1, -1], QB = [1, 1, -1, -1], SR = {d: SB[0], n: 0, runs: RUN, rn: [0, 0, 0, 0], ups: UPS, un: 0, quad: 0, me: null};
    function list(v, m, mp, last) {
      const RW = v.w, RH = v.h, all = v.sprites || []; let me = null; for (const s of all) if (s.top) { me = s; break; }
      const late = (s) => !!me && (s.ty !== undefined && !s.flat ? s.ty > Math.floor(me.y) : s.y > me.y);
      ON[0] = ON[1] = ON[2] = ON[3] = 0; for (const s of all) { const g = s.lie ? 3 : s.top ? 1 : late(s) ? 2 : 0; ORD[g][ON[g]++] = s; }   // (?hd: you (top) are drawn after the water: you stand in it, not under it; what stands south of you after you, and where it covers you a checker of it)   // (lie: on the water's face: after it (not tinted by it), before you (you are over it))
      const need = (ON[0] + ON[1] + ON[2] + ON[3] + 1) * 6 * SV6, bi = last === SB[0] ? 1 : 0; if (SB[bi].length < need) SB[bi] = new Float32Array(Math.ceil(need * 1.5));
      const d = SB[bi], rn = SR.rn; rn[0] = rn[1] = rn[2] = rn[3] = 0; let n = 0, un = 0;
      for (let g = 0; g < 4; g++) for (let si = 0; si < ON[g]; si++) { const s = ORD[g][si];
        const a = place(s.canvas); if (!a) return null; const dm = s.top ? 1 : dimOf(s, v), ver = s.canvas._v !== undefined ? s.canvas._v : s.still ? 0 : NaN; if (a.v !== ver) { UPS[un++] = s.canvas; a.v = ver; }   // (a still billboard is sent once; one with no _v and not still: each frame)
        projTo(m, s.x, s.y, s.z); const fx = Math.round((PJ[0] * .5 + .5) * RW), fy = Math.round((.5 - PJ[1] * .5) * RH), f2 = PJ[2], w = s.canvas.width, h = s.canvas.height;
        const x0 = fx - s.fx, y0 = fy - s.fy, z = s.d ? f2 - .0004 : projTo(m, s.x, s.y + .4, (s.zh ?? s.z) + 2)[2];   // (one depth, your head's a hair south: what is not you; you: below, as you stand)
        const xa = x0 / RW * 2 - 1, xb = (x0 + w) / RW * 2 - 1, ya = 1 - y0 / RH * 2, yb = 1 - (y0 + h) / RH * 2;
        QX[0] = xa; QY[0] = ya; QX[1] = xb; QY[1] = ya; QX[2] = xb; QY[2] = yb; QX[3] = xa; QY[3] = yb; QZ[0] = QZ[1] = QZ[2] = QZ[3] = z; BX[0] = x0; BX[1] = y0; BX[2] = x0 + w; BX[3] = y0 + h;
        if (s.top && !s.d && !s.flat && !s.lie) for (let c = 0; c < 4; c++) QZ[c] = projTo(m, s.x, s.y + .6, (s.zh ?? s.z) + (CV[c] ? s.fy - h : s.fy) / up)[2];   // (you STAND: your px as deep as their height over your feet, just south of your own tile (its floor and its edge never hide you). As one depth, your head's, a block a level up right south of you hid you only where its top is nearer than your head: you were drawn over the rest of it, its edge across you: "player and block fused", #281)
        if (s.flat || s.lie) { const lie = !!s.lie;   // (flat: a standing face in the land, its sprite a px of paint an art px of the land, as the land's own fronts; lie: lying on the land at level z, as its own tops: a swimmer's wake on the water)
          for (let c = 0; c < 4; c++) { const i = CU[c] ? w - s.fx : -s.fx; if (lie) projTo(m, s.x + i / C, s.y + (CV[c] ? h - s.fy : -s.fy) / C, s.z); else projTo(m, s.x + i / C, s.y, s.z + (CV[c] ? s.fy - h : s.fy) / up); QX[c] = PJ[0]; QY[c] = PJ[1]; QZ[c] = PJ[2] - (lie ? .0002 : .0004); }
          BX[0] = (QX[0] * .5 + .5) * RW; BX[1] = (.5 - QY[0] * .5) * RH; BX[2] = (QX[2] * .5 + .5) * RW; BX[3] = (.5 - QY[2] * .5) * RH; }
        const over = mp && s !== me && !s.lie && late(s) && BX[0] < mp[0] + 6 && BX[2] > mp[0] - 6 && BX[1] < mp[1] - 2 && BX[3] > mp[1] - 15, how = s.top ? 1 : 0;
        const r = RUN[g], k = rn[g]; if (k && r[k - 1] === how) r[k - 2] += 6; else { r[k] = n / SV6; r[k + 1] = 6; r[k + 2] = how; rn[g] = k + 3; }   // (runs: first vertex, count, how: three numbers a run)
        for (let t = 0; t < 6; t++) { const i = S6[t]; d[n++] = QX[i]; d[n++] = QY[i]; d[n++] = QZ[i]; d[n++] = (a.x + CU[i] * a.w) / SW; d[n++] = (a.y + CV[i] * a.h) / SW; d[n++] = s.ghost ? 3 : over ? 2 : 0; d[n++] = dm; d[n++] = s.fade === undefined ? 1 : s.fade; }
      }
      const quad = n / SV6; for (let t = 0; t < 6; t++) { const i = S6[t]; d[n++] = QA[i]; d[n++] = QB[i]; d[n++] = 0; d[n++] = CU[i]; d[n++] = CV[i]; d[n++] = 0; d[n++] = 1; d[n++] = 1; }   // (the last six: the whole picture, for the hour's light)
      for (let g = 0; g < 4; g++) ORD[g].fill(null, ON[g]); UPS.fill(null, un);   // (nothing of an earlier frame held on to)
      SR.d = d; SR.n = n; SR.un = un; SR.quad = quad; SR.me = me; return SR;
    }
    return {list, reset() { shelf.x = shelf.y = shelf.h = 0; shelf.ep++; }};
  }
  return {create, SW, SV6};
})();
