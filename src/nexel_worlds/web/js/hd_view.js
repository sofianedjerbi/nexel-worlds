// The HD look's picture on the page (hd.js makes the scene, vox_style.js draws the land): where it is shown, and what a frame costs.
// ONE canvas for the world, #hd, at the art's own size (a px of it an art px), under the game's canvas and made zoom times bigger by the page
// (image-rendering: pixelated). It was laid on the game's canvas (#c, the screen's size at its density: 1.3 million px on a phone) every frame,
// over a classic frame painted there for nothing. Now, with this look on:
//   - the game's canvas holds only what is written (names, bubbles): painted again only when it changed (words); what is pointed at and planned (the aim's corners, ghosts:
//     whole art px) is on the world's canvas with the land (marks): it moves with every step, and wiped the screen-size canvas each frame;
//   - the sky is the engine's own (vox_sky.js) made at the art's size, not the screen's, and only when its clouds, its hour or its line moved (skyOf);
//   - the backdrop and the land's picture are put together here only when one of them changed (show).
// perf: each frame to the debug screen (f3.js: F3, ?perf=1), and its section about this look: its ms, the longest
// piece of land made, draw calls, how many frames were drawn at all, the pictures' sizes. (It had a box of its own.)
const HdView = (() => {
  let el = null, g = null, sk = null, skyKey = "", skyVer = 0, lastKey = "", wordsKey = null, wordsAt = 0, tmp = null;
  const Z = () => artPx() * DPR, PAINT = new Set(["fillRect", "clearRect", "strokeRect", "fillText", "strokeText", "drawImage", "fill", "stroke", "putImageData"]), ids = new WeakMap(), strs = new Map(); let nid = 0;
  // a 2D context that notes what is asked of it: a number for all of it (hash), and the calls themselves. dry: nothing is painted (what sets a state is passed on: a text is measured as it will be drawn); play() paints them
  const call = (t, k, n, a, b, c, d, e, f, g, h, i) => { const m = t[k];   // (t's method k with its first n args: no array made)
    switch (n) { case 0: return m.call(t); case 1: return m.call(t, a); case 2: return m.call(t, a, b); case 3: return m.call(t, a, b, c); case 4: return m.call(t, a, b, c, d); case 5: return m.call(t, a, b, c, d, e);
      case 6: return m.call(t, a, b, c, d, e, f); case 7: return m.call(t, a, b, c, d, e, f, g); case 8: return m.call(t, a, b, c, d, e, f, g, h); default: return m.call(t, a, b, c, d, e, f, g, h, i); } };
  function recorder(real, dry) {
    const ops = [], fns = {}; let h = 0, on = 0;   // (ops: one flat list, kept and written over (on: how much of it is this frame's): a call [its args + 1, name, args...], a set [0, name, value]. It was an array of args a call, and a name made a set, each frame: 4 MB in 3 s)
    const mix = (v) => { h = Math.imul(h ^ v, 16777619) | 0; }, str = (s) => { let n = strs.get(s); if (n === undefined) { if (strs.size > 4000) strs.clear(); n = 0; for (let i = 0; i < s.length; i++) n = Math.imul(n ^ s.charCodeAt(i), 16777619) | 0; strs.set(s, n); } mix(n); };   // (a string's own number, kept: a colour, a font, a call's name were hashed a char at a time, each of them each frame)
    const val = (a) => { if (typeof a === "number") mix((a * 64) | 0); else if (typeof a === "string") str(a); else if (a && typeof a === "object") { let id = ids.get(a); if (!id) ids.set(a, id = ++nid); mix(id); mix(a._v || a.naturalWidth || a.width || 0); } else mix(a ? 1 : 2); };
    const proxy = new Proxy(real, {
      get(t, k) { const v = t[k]; if (typeof v !== "function") return v; const paints = PAINT.has(k);
        return fns[k] || (fns[k] = function (a0, a1, a2, a3, a4, a5, a6, a7, a8) { const n = Math.min(9, arguments.length); str(k);   // (a canvas call takes 9 at the most: drawImage)
          if (n > 0) val(a0); if (n > 1) val(a1); if (n > 2) val(a2); if (n > 3) val(a3); if (n > 4) val(a4); if (n > 5) val(a5); if (n > 6) val(a6); if (n > 7) val(a7); if (n > 8) val(a8);
          if (dry) { ops[on++] = n + 1; ops[on++] = k; if (n > 0) ops[on++] = a0; if (n > 1) ops[on++] = a1; if (n > 2) ops[on++] = a2; if (n > 3) ops[on++] = a3; if (n > 4) ops[on++] = a4; if (n > 5) ops[on++] = a5; if (n > 6) ops[on++] = a6; if (n > 7) ops[on++] = a7; if (n > 8) ops[on++] = a8; }
          if (!dry || !paints) return call(t, k, n, a0, a1, a2, a3, a4, a5, a6, a7, a8); }); },
      set(t, k, v) { str(k); val(v); if (dry) { ops[on++] = 0; ops[on++] = k; ops[on++] = v; } if (k !== "font" || t[k] !== v) t[k] = v; return true; }});   // (a font set again to itself was parsed again: each name and bubble, each frame)
    return {proxy, reset() { ops.fill(undefined, 0, on); on = 0; h = 0; }, get hash() { return h; },
      get ops() { const l = []; for (let i = 0; i < on;) { const n = ops[i++], k = ops[i++]; if (!n) l.push("=" + k, ops[i++]); else { l.push(k, ops.slice(i, i + n - 1)); i += n - 1; } } return l; },   // (as it was: name, args; "=name", value: dump)
      play() { for (let i = 0; i < on;) { const n = ops[i++], k = ops[i++]; if (!n) real[k] = ops[i++]; else { call(real, k, n - 1, ops[i], ops[i + 1], ops[i + 2], ops[i + 3], ops[i + 4], ops[i + 5], ops[i + 6], ops[i + 7], ops[i + 8]); i += n - 1; } } }};
  }
  // what is written over the picture, on the game's canvas: fn paints it with `ctx`. It is asked each frame, painted only when it is not what is there (and four times a second whatever)
  let rec = null;
  function words(fn, now) {
    const real = ctx; rec = rec || recorder(real, true); rec.reset();
    real.setTransform(DPR, 0, 0, DPR, 0, 0); drawOn(rec.proxy, zoom, fn);
    const k = rec.hash + "|" + cv.width + "x" + cv.height; if (k === wordsKey && now - wordsAt < 250) return false;
    wordsKey = k; wordsAt = now; real.setTransform(1, 0, 0, 1, 0, 0); real.globalAlpha = 1; real.clearRect(0, 0, cv.width, cv.height); real.setTransform(DPR, 0, 0, DPR, 0, 0); real.imageSmoothingEnabled = false; rec.play(); return true;
  }
  // what is pointed at and planned, in whole art px: on the world's canvas, over the land: fn paints it with `ctx` in the game's own px (artPx() of them an art px) -> a number for all of it; show() paints it when it puts the picture together
  let recM = null;
  function marks(fn) {
    if (!g) return 0; recM = recM || recorder(g, true); recM.reset(); const u = artPx(); g.setTransform(1 / u, 0, 0, 1 / u, 0, 0);
    try { drawOn(recM.proxy, zoom, fn); } finally { g.setTransform(1, 0, 0, 1, 0, 0); } return recM.hash;
  }
  function fit(w, h) {
    if (!el) { el = document.createElement("canvas"); el.id = "hd"; cv.before(el); g = el.getContext("2d"); }
    if (el.width !== w || el.height !== h) { el.width = w; el.height = h; lastKey = ""; }
    const u = artPx(), sw = w * u + "px", sh = h * u + "px";   // (an art px a whole number of the screen's px: state.js artPx)
    if (el.style.width !== sw || el.style.height !== sh) { el.style.width = sw; el.style.height = sh; el.style.transformOrigin = W / 2 + "px " + H / 2 + "px"; }
    if (el.style.display !== "block") { el.style.display = "block"; lastKey = ""; wordsKey = null; }
  }
  function hide() { if (el && el.style.display !== "none") { el.style.display = "none"; wordsKey = null; } }
  // the game's sky with the hour's light the game lays over its frame: made w x h px, when it is not the one there. line: the sky's (the eye's horizon); edge: where the land ends,
  // under it from a hill top: the far hills on it, the sky's lowest colour down to it, under it the far land's own colour, as vox_sky.js has it (it was the air's pale haze, or the whole sky moved down to the land)
  function skyOf(w, h, line, sky, edge = line) {
    const {wash: ws, lit: light} = Light.now(), step = sky.stars > 0 ? .1 : .5, tq = Math.floor(sky.t / step);   // (clouds drift a px in 2.5 s: twice a second; stars twinkle: ten times)
    const c8 = (q) => q.map((v) => Math.round(v * 255)), k = [w, h, line, edge, W, zoom, tq, Math.floor(sky.shift), Math.floor(sky.shift * .6), Math.floor(sky.shift * .3), c8(sky.top), c8(sky.low), c8(sky.cloud), c8(sky.far), c8(sky.near), c8(sky.orb), sky.at.map((v) => Math.round(v * 500)), Math.round(sky.stars * 50), ws.map((v) => Math.round(v * 100) / 100), light].join();
    if (k === skyKey) return; const gl = VoxGL.gl; if (!gl) return; skyKey = k; skyVer++;
    sk = sk || document.createElement("canvas").getContext("2d"); if (sk.canvas.width !== w || sk.canvas.height !== h) { sk.canvas.width = w; sk.canvas.height = h; }
    VoxGL.fit(w, h); gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, w, h); gl.disable(gl.BLEND);
    VoxSky.draw(Object.assign({}, sky, {line, edge, t: tq * step}), W / artPx(), h, W / artPx(), 1);   // (a px of it a px of the paint: as the picture the screen's size had them, zoom x density px each)
    sk.globalAlpha = 1; sk.globalCompositeOperation = "source-over"; sk.imageSmoothingEnabled = false; sk.drawImage(VoxGL.el, 0, 0);
    sk.globalAlpha = ws[3]; sk.fillStyle = `rgb(${ws.slice(0, 3).join()})`; sk.fillRect(0, 0, w, h); sk.globalAlpha = 1; sk.globalCompositeOperation = "multiply"; sk.fillStyle = `rgb(${light.join()})`; sk.fillRect(0, 0, w, h); sk.globalCompositeOperation = "source-over";
  }
  // (NO LENS: the far rows were blurred 1 px and a 4 px bloom of the light parts laid over all of it, on a desktop: every rim and every far wall a soft smear, pixel art
  //  no longer whole art px: "cheap 3D". The haze of the far land is the land's own painter's, in its own px; nothing here blurs the picture)
  let chk = null, chkOf = "", chkPat = null, bk = null, pic = null;
  function checker(col) { if (col === chkOf) return chkPat; chk = chk || document.createElement("canvas").getContext("2d"); chk.canvas.width = chk.canvas.height = 4; chk.fillStyle = col; chk.fillRect(0, 0, 2, 2); chk.fillRect(2, 2, 2, 2); chkOf = col; return chkPat = g.createPattern(chk.canvas, "repeat"); }
  // the picture of this frame on #hd: the backdrop (under the horizon, past the bend: the air's haze; the sea's tint only over the columns where the sea is really there, past the last land
  // you see; the sky's rows), the land's picture over it. Only when one of them is new.
  //   o: {w, h, pic, fresh: the land's picture was drawn again, sky, runs: [[x0, x1]...] the sea's columns, marks}
  function show(o) {
    const {w, h} = o, line0 = o.sky ? Math.round(o.sky.line / zoom) : 0, line = o.sky ? Math.max(line0, Math.round((o.sky.edge || 0) / zoom)) : 0, low = o.sky ? o.sky.low : [.62, .78, .86]; fit(w, h);   // (line: the land's edge, the sky's own line or under it: hd.js api.sky)
    if (line0 > 0) skyOf(w, h, line0, o.sky, line);
    const key = [line0 > 0 ? skyVer : 0, line, low.map((v) => Math.round(v * 255)), o.runs, o.marks, zoom].join("|");
    if (!o.fresh && key === lastKey) return false; lastKey = key;
    const tint = (c, a) => `rgb(${low.map((v, i) => Math.round((v * (1 - a) + c[i] * a) * 255)).join()})`; bk = [[.8, .84, .8, .45], [.36, .64, .8, .65]].map((c) => low.map((v, i) => Math.round((v * (1 - c[3]) + c[i] * c[3]) * 255)));   // (bk: the backdrop's two colours, the air's and the sea's: where no land is drawn; tests count them)
    g.globalAlpha = 1; g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false; g.fillStyle = tint([.8, .84, .8], .45); g.fillRect(0, 0, w, h);
    if (line > 0 && sk) g.drawImage(sk.canvas, 0, 0);
    g.fillStyle = tint([.36, .64, .8], .65); for (const [run, px] of o.runs) { g.fillRect(run, line, px - run, h - line); for (const ex of [run - 8, px]) { g.save(); g.translate(ex, 0); g.fillStyle = checker(g.fillStyle); g.fillRect(0, line, 8, h - line); g.restore(); } }   // (under the sky's line only: the sky over the sea is the sky)   // (its two ends: a 2x2 checker, 8 px: one fill of a pattern; it was 400 small ones)
    g.drawImage(o.pic, 0, 0); pic = o.pic;   // (the land's picture as it is: nothing over it but the marks)
    if (recM && o.marks) { const u = artPx(); g.setTransform(1 / u, 0, 0, 1 / u, 0, 0); recM.play(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; }
    return true;
  }
  // what the screen shows there, px of the game's canvas (x, y, w, h): the world's canvas made as big, the game's canvas over it (tests; hd.js catSeen)
  function read(x, y, w, h) {
    tmp = tmp || document.createElement("canvas").getContext("2d", {willReadFrequently: true}); if (tmp.canvas.width !== cv.width || tmp.canvas.height !== cv.height) { tmp.canvas.width = cv.width; tmp.canvas.height = cv.height; }
    tmp.imageSmoothingEnabled = false; tmp.clearRect(0, 0, cv.width, cv.height); if (el && el.style.display === "block") tmp.drawImage(el, 0, 0, el.width * Z(), el.height * Z()); tmp.drawImage(cv, 0, 0);
    return tmp.getImageData(x, y, w, h);
  }
  // the debug screen (f3.js): this look's share of a frame, from one time its text is written to the next
  const PF = {n: 0, drawn: 0, calls: 0, slice: 0, words: 0, ms: 0};
  function perf(now, js, drawn, calls, slice, wrote) {
    if (!F3.on) return;
    PF.n++; if (drawn) { PF.drawn++; PF.calls = calls; } if (wrote) PF.words++; PF.slice = Math.max(PF.slice, slice); PF.ms += HdLook.ms || 0;
    F3.sample(now, js);
  }
  F3.add("look", () => {
    if (!HdLook.live) return [];
    const n = PF.n || 1, r = [`HD look ${(PF.ms / n).toFixed(1)} ms  land ${PF.slice.toFixed(1)} ms  made ${HdLook.made || 0} chunks`,
      `${PF.calls} draws  ${HdLook.faces || 0} faces  drawn ${PF.drawn}/${PF.n}  words ${PF.words}/${PF.n}`, `picture ${el ? el.width + "x" + el.height : "-"} x${zoom}`];
    PF.n = PF.drawn = PF.slice = PF.words = PF.ms = 0;
    return r;
  }, "perf");
  return {recorder, words, marks, dump: () => (rec ? rec.ops.map((v) => (Array.isArray(v) ? v.map((x) => (typeof x === "object" ? "#" : x)).join() : String(v))).join(" ") : ""), show, hide, read, perf, get el() { return el; }, get backdrop() { return bk; }, get pic() { return pic; }};
})();
