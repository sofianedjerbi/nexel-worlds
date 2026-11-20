// The HD look's picture on the page (hd.js makes the scene, vox_style.js draws the land): where it is shown, and what a frame costs.
// ONE canvas for the world, #hd, at the art's own size (a px of it an art px), under the game's canvas and made zoom times bigger by the page
// (image-rendering: pixelated). It was laid on the game's canvas (#c, the screen's size at its density: 1.3 million px on a phone) every frame,
// over a classic frame painted there for nothing. Now, with this look on:
//   - the game's canvas holds only what is written (names, bubbles): painted again only when it changed (words); what is pointed at and planned (the aim's corners, ghosts:
//     whole art px) is on the world's canvas with the land (marks): it moves with every step, and wiped the screen-size canvas each frame;
//   - the sky is the engine's own (vox_sky.js) made at the art's size, not the screen's, and only when its clouds, its hour or its line moved (skyOf);
//   - the backdrop and the land's picture are put together here only when one of them changed (show).
// ?perf=1 (or /perf in the chat): a small readout, top left: frames a second, the wait between frames and the script's time (ms, middle and worst of a hundred), the longest
// piece of land made, draw calls, how many frames were drawn at all.
const HdView = (() => {
  let el = null, g = null, sk = null, skyKey = "", skyVer = 0, art = null, fx = null, one = null, lastKey = "", wordsKey = null, wordsAt = 0, tmp = null;
  const Z = () => zoom * DPR, PAINT = new Set(["fillRect", "clearRect", "strokeRect", "fillText", "strokeText", "drawImage", "fill", "stroke", "putImageData"]), ids = new WeakMap(); let nid = 0;
  const sink = () => one || (one = document.createElement("canvas").getContext("2d"));   // (a canvas of one px: what the classic frame still paints goes there)
  // a 2D context that notes what is asked of it: a number for all of it (hash), and the calls themselves. dry: nothing is painted (what sets a state is passed on: a text is measured as it will be drawn); play() paints them
  function recorder(real, dry) {
    const ops = [], fns = {}; let h = 0;
    const mix = (v) => { h = Math.imul(h ^ v, 16777619) | 0; }, str = (s) => { for (let i = 0; i < s.length; i++) mix(s.charCodeAt(i)); };
    const val = (a) => { if (typeof a === "number") mix((a * 64) | 0); else if (typeof a === "string") str(a); else if (a && typeof a === "object") { let id = ids.get(a); if (!id) ids.set(a, id = ++nid); mix(id); mix(a._v || a.naturalWidth || a.width || 0); } else mix(a ? 1 : 2); };
    const proxy = new Proxy(real, {
      get(t, k) { const v = t[k]; if (typeof v !== "function") return v; return fns[k] || (fns[k] = (...a) => { str(k); for (const x of a) val(x); if (dry) ops.push(k, a); if (!dry || !PAINT.has(k)) return t[k].apply(t, a); }); },
      set(t, k, v) { str(k); val(v); if (dry) ops.push("=" + k, v); t[k] = v; return true; }});
    return {proxy, reset() { ops.length = 0; h = 0; }, get hash() { return h; }, get ops() { return ops; }, play() { for (let i = 0; i < ops.length; i += 2) { const k = ops[i]; if (k[0] === "=") real[k.slice(1)] = ops[i + 1]; else real[k].apply(real, ops[i + 1]); } }};
  }
  // what is written over the picture, on the game's canvas: fn paints it with `ctx`. It is asked each frame, painted only when it is not what is there (and four times a second whatever)
  let rec = null;
  function words(fn, now) {
    const real = ctx; rec = rec || recorder(real, true); rec.reset();
    ctx = rec.proxy; try { real.setTransform(DPR, 0, 0, DPR, 0, 0); fn(); } finally { ctx = real; }
    const k = rec.hash + "|" + cv.width + "x" + cv.height; if (k === wordsKey && now - wordsAt < 250) return false;
    wordsKey = k; wordsAt = now; real.setTransform(1, 0, 0, 1, 0, 0); real.globalAlpha = 1; real.clearRect(0, 0, cv.width, cv.height); real.setTransform(DPR, 0, 0, DPR, 0, 0); real.imageSmoothingEnabled = false; rec.play(); return true;
  }
  // what is pointed at and planned, in whole art px: on the world's canvas, over the land: fn paints it with `ctx` in the game's own px (zoom of them an art px) -> a number for all of it; show() paints it when it puts the picture together
  let recM = null;
  function marks(fn) {
    if (!g) return 0; recM = recM || recorder(g, true); recM.reset(); const keep = ctx; g.setTransform(1 / zoom, 0, 0, 1 / zoom, 0, 0);
    ctx = recM.proxy; try { fn(); } finally { ctx = keep; g.setTransform(1, 0, 0, 1, 0, 0); } return recM.hash;
  }
  function fit(w, h) {
    if (!el) { el = document.createElement("canvas"); el.id = "hd"; cv.before(el); g = el.getContext("2d"); }
    if (el.width !== w || el.height !== h) { el.width = w; el.height = h; lastKey = ""; }
    const sw = w * zoom + "px", sh = h * zoom + "px"; if (el.style.width !== sw || el.style.height !== sh) { el.style.width = sw; el.style.height = sh; el.style.transformOrigin = W / 2 + "px " + H / 2 + "px"; }
    if (el.style.display !== "block") { el.style.display = "block"; lastKey = ""; wordsKey = null; }
  }
  function hide() { if (el && el.style.display !== "none") { el.style.display = "none"; wordsKey = null; } }
  // the game's sky, the rows over the horizon, with the hour's light the game lays over its frame: made w x line px, when it is not the one there
  function skyOf(w, line, sky) {
    const ph = clock.phase || 0, ws = washAt(ph), lf = opt("night") / 100 * .6, light = lightAt(ph).map((v) => Math.round(v + (255 - v) * lf)), step = sky.stars > 0 ? .1 : .5, tq = Math.floor(sky.t / step);   // (clouds drift a px in 2.5 s: twice a second; stars twinkle: ten times)
    const c8 = (q) => q.map((v) => Math.round(v * 255)), k = [w, line, W, zoom, tq, Math.floor(sky.shift), Math.floor(sky.shift * .6), Math.floor(sky.shift * .3), c8(sky.top), c8(sky.low), c8(sky.cloud), c8(sky.far), c8(sky.near), c8(sky.orb), sky.at.map((v) => Math.round(v * 500)), Math.round(sky.stars * 50), ws.map((v) => Math.round(v * 100) / 100), light].join();
    if (k === skyKey) return; const gl = VoxGL.gl; if (!gl) return; skyKey = k; skyVer++;
    sk = sk || document.createElement("canvas").getContext("2d"); if (sk.canvas.width !== w || sk.canvas.height !== line) { sk.canvas.width = w; sk.canvas.height = line; }
    VoxGL.fit(w, line); gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, w, line); gl.disable(gl.BLEND);
    VoxSky.draw(Object.assign({}, sky, {line, t: tq * step}), W / zoom, line, W / zoom, 1);   // (a px of it a px of the paint: as the picture the screen's size had them, zoom x density px each)
    sk.globalAlpha = 1; sk.globalCompositeOperation = "source-over"; sk.imageSmoothingEnabled = false; sk.drawImage(VoxGL.el, 0, 0);
    sk.globalAlpha = ws[3]; sk.fillStyle = `rgb(${ws.slice(0, 3).join()})`; sk.fillRect(0, 0, w, line); sk.globalAlpha = 1; sk.globalCompositeOperation = "multiply"; sk.fillStyle = `rgb(${light.join()})`; sk.fillRect(0, 0, w, line); sk.globalCompositeOperation = "source-over";
  }
  // the lens: far rows (the 48 art px under the horizon, hy) a little soft, the rest crisp; a faint bloom of the light parts; no vignette
  // (it was the top three tenths of the screen, wherever the horizon: looked at from close, or on a screen held upright, the land near you was a blur)
  function post(pic, w, h, hy, blur, near) {
    art = art || document.createElement("canvas"); fx = fx || document.createElement("canvas");
    for (const c of [art, fx]) if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    const a = art.getContext("2d"), f = fx.getContext("2d"); a.globalCompositeOperation = "source-over"; a.clearRect(0, 0, w, h); a.drawImage(pic, 0, 0);
    const span = Math.min(48, near - hy); if (blur > 0 && hy + span > 0 && span >= 4) {   // (near: the row ten tiles north of you: nothing nearer is ever soft. Zoomed in, or with the eye steep, the band reached the land round you)
      f.globalCompositeOperation = "source-over"; f.clearRect(0, 0, w, h); f.filter = `blur(${blur}px)`; f.drawImage(pic, 0, 0); f.filter = "none";
      f.globalCompositeOperation = "destination-in"; const gr = f.createLinearGradient(0, hy, 0, hy + span);
      gr.addColorStop(0, "rgba(0,0,0,.85)"); gr.addColorStop(1, "rgba(0,0,0,0)"); f.fillStyle = gr; f.fillRect(0, 0, w, h);
      a.globalCompositeOperation = "source-atop"; a.drawImage(fx, 0, 0);
    }
    f.globalCompositeOperation = "source-over"; f.clearRect(0, 0, w, h); f.filter = "brightness(.55) contrast(8) blur(4px)"; f.drawImage(pic, 0, 0); f.filter = "none";
    a.globalCompositeOperation = "lighter"; a.globalAlpha = .07; a.drawImage(fx, 0, 0); a.globalAlpha = 1; a.globalCompositeOperation = "source-over";
    return art;
  }
  let chk = null, chkOf = "", chkPat = null;
  function checker(col) { if (col === chkOf) return chkPat; chk = chk || document.createElement("canvas").getContext("2d"); chk.canvas.width = chk.canvas.height = 4; chk.fillStyle = col; chk.fillRect(0, 0, 2, 2); chk.fillRect(2, 2, 2, 2); chkOf = col; return chkPat = g.createPattern(chk.canvas, "repeat"); }
  // the picture of this frame on #hd: the backdrop (under the horizon, past the bend: the air's haze; the sea's tint only over the columns where the sea is really there, past the last land
  // you see; the sky's rows), the land's picture over it. Only when one of them is new.
  //   o: {w, h, pic, fresh: the land's picture was drawn again, sky, runs: [[x0, x1]...] the sea's columns, hy, blur, lens}
  function show(o) {
    const {w, h} = o, line = o.sky ? Math.round(o.sky.line / zoom) : 0, low = o.sky ? o.sky.low : [.62, .78, .86]; fit(w, h);
    if (line > 0) skyOf(w, line, o.sky);
    const key = [line > 0 ? skyVer : 0, line, low.map((v) => Math.round(v * 255)), o.runs, o.blur, o.lens, o.marks, zoom].join("|");
    if (!o.fresh && key === lastKey) return false; lastKey = key;
    const tint = (c, a) => `rgb(${low.map((v, i) => Math.round((v * (1 - a) + c[i] * a) * 255)).join()})`;
    g.globalAlpha = 1; g.globalCompositeOperation = "source-over"; g.imageSmoothingEnabled = false; g.fillStyle = tint([.8, .84, .8], .45); g.fillRect(0, 0, w, h);
    g.fillStyle = tint([.36, .64, .8], .65); for (const [run, px] of o.runs) { g.fillRect(run, 0, px - run, h); for (const ex of [run - 8, px]) { g.save(); g.translate(ex, 0); g.fillStyle = checker(g.fillStyle); g.fillRect(0, 0, 8, h); g.restore(); } }   // (its two ends: a 2x2 checker, 8 px: one fill of a pattern; it was 400 small ones)
    if (line > 0 && sk) g.drawImage(sk.canvas, 0, 0);
    const pic = o.lens ? (o.fresh || !art || art.width !== w || art.height !== h ? post(o.pic, w, h, o.hy, o.blur, o.near === undefined ? 1e9 : o.near) : art) : o.pic;   // (a phone: no lens: two blurs of the whole picture a frame)
    g.drawImage(pic, 0, 0);
    if (recM && o.marks) { g.setTransform(1 / zoom, 0, 0, 1 / zoom, 0, 0); recM.play(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; }
    return true;
  }
  // what the screen shows there, px of the game's canvas (x, y, w, h): the world's canvas made as big, the game's canvas over it (tests; hd.js catSeen)
  function read(x, y, w, h) {
    tmp = tmp || document.createElement("canvas").getContext("2d", {willReadFrequently: true}); if (tmp.canvas.width !== cv.width || tmp.canvas.height !== cv.height) { tmp.canvas.width = cv.width; tmp.canvas.height = cv.height; }
    tmp.imageSmoothingEnabled = false; tmp.clearRect(0, 0, cv.width, cv.height); if (el && el.style.display === "block") tmp.drawImage(el, 0, 0, el.width * Z(), el.height * Z()); tmp.drawImage(cv, 0, 0);
    return tmp.getImageData(x, y, w, h);
  }
  // ?perf=1: what the frames cost, read off the screen (a phone has no console)
  const PF = {url: new URLSearchParams(location.search).get("perf") === "1", get on() { return this.url || DEBUG.perf; }, box: null, gaps: [], js: [], last: 0, since: 0, drawn: 0, calls: 0, slice: 0, words: 0};
  function perf(now, js, drawn, calls, slice, wrote) {
    if (!PF.on) { if (PF.box) { PF.box.remove(); PF.box = null; PF.since = PF.last = 0; } return; } if (PF.last) PF.gaps.push(now - PF.last); PF.last = now; PF.js.push(js); if (drawn) { PF.drawn++; PF.calls = calls; } if (wrote) PF.words++; PF.slice = Math.max(PF.slice, slice); if (!PF.since) PF.since = now;
    if (now - PF.since < 1000 || PF.gaps.length < 2) return;
    if (!PF.box) { PF.box = document.createElement("div"); PF.box.id = "hdperf"; document.body.appendChild(PF.box); }
    const at = (l, q) => { const s = l.slice().sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.floor(s.length * q))].toFixed(1); }, n = PF.js.length;
    PF.box.textContent = `${Math.round(PF.gaps.length * 1000 / (now - PF.since))} fps  frame ${at(PF.gaps, .5)} / ${at(PF.gaps, .99)} ms\nscript ${at(PF.js, .5)} / ${at(PF.js, .99)} ms  land ${PF.slice.toFixed(1)} ms\n${PF.calls} draws  drawn ${PF.drawn}/${n}  words ${PF.words}/${n}\n${el ? el.width + "x" + el.height : "-"} x${zoom}  screen ${cv.width}x${cv.height}`;
    PF.gaps = []; PF.js = []; PF.since = now; PF.drawn = 0; PF.slice = 0; PF.words = 0;
  }
  return {sink, recorder, words, marks, dump: () => (rec ? rec.ops.map((v) => (Array.isArray(v) ? v.map((x) => (typeof x === "object" ? "#" : x)).join() : String(v))).join(" ") : ""), show, hide, read, perf, get el() { return el; }};
})();
