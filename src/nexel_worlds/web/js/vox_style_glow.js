// VOX's light of your space (vox_style.js draw): a picture of a px a tile the land's painter reads for each floor
// under the land (stx), each floor warm, dim or neither, eased over 300 ms.
//   VoxStyleGlow.create(K) -> {light(now, way): the picture made again and sent if it changed, poke(): look again next
//     frame (a new land, a new space), lost(): the picture sent is gone (a lost context), sorg: where the picture is
//     [x, y, D], sver: goes up as it is sent, cdv: how dim the floors off a way shown are, eased}
//   K: {gl, stx: the context and the picture's texture (new after a lost context), near(): its filter, space: the last
//       land's space (vox_style_land.js), sameN (vox_style.js)}
const VoxStyleGlow = (() => {
  function create(K) {
    let sorg = [0, 0, 1], sAt = 0, sBusy = false, sWay = null, cdv = 0, cdAt = 0, sPx = null, sOrg = null, sver = 0;
    const glow = new Map(), LP = [null, null];
    // THE LIGHT OF YOUR SPACE: a number a tile (glow: tile -> [its floor's level, warm 0..1, dim 0..1]) the land's painter reads for each floor under the land (a small picture, a px a tile: stx). It goes to what the last land found
    // (space.cls: 1 walked to: warm; 2 dropped to: warm and dim; else cold) over 300 ms in six steps: a floor that joins your space warms, one that leaves it cools. Not baked in the faces: every floor would flip in one frame
    // view.way (a way shown through the land, its floors "x,y" -> level): they are lit as your space's; way.dim: the floors off it that are not your space, darker (cdv, over 300 ms)
    function light(now, way) {
      { const tg = way ? way.dim || 0 : 0, d = Math.min(.1, Math.max(0, now - cdAt)) / .3; cdAt = now; cdv += Math.max(-d, Math.min(d, tg - cdv)); } if ((way && way.key) !== sWay) { sWay = way && way.key; sBusy = true; }
      if (!sBusy) return; const k = Math.min(.1, Math.max(0, now - sAt)) / .3, sp = K.space, first = !glow.size, D = sp ? sp.D : sorg[2]; sAt = now; sBusy = false; if (sp) sorg = [sp.x, sp.y, D];
      const cls = (i, j, lv) => { if (!sp || i < 0 || j < 0 || i >= D || j >= D) return 0; const c = sp.cls[j * D + i]; return (c === 1 || c === 2) && sp.lvl[j * D + i] === lv ? c : 0; };
      // (each tile's name worked out once a space (sp._keys), each glow's place kept in it ([lv, warm, dim, x, y]), the picture into the one of two kept buffers not sent last, and sent only when
      //  it is not that one: tile names, split names and a string of the whole picture were made again each frame the light moved, walking: 2 MB in 2 s)
      if (sp) { const K = sp._keys || (sp._keys = new Array(D * D)); for (let i = 0; i < D * D; i++) { const lv = sp.lvl[i], c = cls(i % D, i / D | 0, lv); if (!c) continue; const key = K[i] || (K[i] = (sp.x + i % D) + "," + (sp.y + (i / D | 0))), g = glow.get(key); if (!g || g[0] !== lv) glow.set(key, [lv, first ? 1 : 0, first && c === 2 ? 1 : 0, sp.x + i % D, sp.y + (i / D | 0)]); } }
      if (way) for (const [key, lv] of way.on) { const g = glow.get(key), [x, y] = key.split(",").map(Number); if (!g || (g[0] !== lv && !cls(x - sorg[0], y - sorg[1], g[0]))) glow.set(key, [lv, 0, 0, x, y]); }
      const lb = LP[0] === sPx ? 1 : 0; if (!LP[lb] || LP[lb].length !== D * D * 4) LP[lb] = new Uint8Array(D * D * 4); else LP[lb].fill(0); const px = LP[lb];
      glow.forEach((g, key) => { const i = g[3] - sorg[0], j = g[4] - sorg[1], on = cls(i, j, g[0]) || (way && way.on.get(key) === g[0] ? 1 : 0), w = on ? 1 : 0, d = on === 2 ? 1 : 0;
        g[1] += Math.max(-k, Math.min(k, w - g[1])); g[2] += Math.max(-k, Math.min(k, d - g[2])); if (g[1] !== w || g[2] !== d) sBusy = true; if (!on && g[1] <= 0) { glow.delete(key); return; }
        if (i >= 0 && j >= 0 && i < D && j < D) { const o = (j * D + i) * 4; px[o] = Math.round(g[1] * 6) * 42.5; px[o + 1] = (g[0] + 1024) % 256; px[o + 2] = Math.round(g[2] * 6) * 42.5; } });
      if (sPx && sPx.length === px.length && sOrg && sOrg[0] === sorg[0] && sOrg[1] === sorg[1] && sOrg[2] === sorg[2] && K.sameN(px, px.length, sPx, sPx.length)) return; sPx = px; sOrg = sorg; sver++;   // (the picture sent last, and where)
      const gl = K.gl; gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, K.stx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, D, D, 0, gl.RGBA, gl.UNSIGNED_BYTE, px); K.near(); gl.activeTexture(gl.TEXTURE0);
    }
    return {light, poke() { sBusy = true; }, lost() { sPx = null; sBusy = true; }, get sorg() { return sorg; }, get sver() { return sver; }, get cdv() { return cdv; }};
  }
  return {create};
})();
