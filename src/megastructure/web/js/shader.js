// Shaders (the settings' Shaders page): "add nice shaders in the settings menu, like minecraft shaders". The game is
// painted on a 2D canvas; a shader takes that finished picture each frame and repaints it on a WebGL canvas laid
// exactly over it (#fx): bright things glow (lamps and fires at night, water's light, snow), the colours are graded,
// cloud shadows drift over the land, the corners darken. The 2D canvas under it is untouched: Off, and it is as before.
// The interface is not on the canvas, so no shader touches it.
//   A shader is a row of SHADERS: how much of each effect. Strength takes all of it from none (0) to as written (100).
//   The passes: bright parts to a quarter-size picture, blurred twice (a tight glow, then a wide one), then the final one.

const SHADERS = {       // glow: how much; from: how bright a thing must be to glow (0 to 1); sat, con: colour and contrast (1: as is);
  //                       tint: red, green, blue; vig: dark corners; lift: a haze; scan: an old screen's lines
  natural: {name: "Natural", glow: .5, from: .8, sat: 1, con: 1, tint: [1, 1, 1], vig: 0, lift: 0, scan: 0},      // (shadows, reflections, a little glow: the colours as they are)
  soft: {name: "Soft glow", glow: .7, from: .8, sat: 1.08, con: 1.04, tint: [1, 1, 1], vig: .2, lift: 0, scan: 0},
  golden: {name: "Golden hour", glow: .75, from: .78, sat: 1.12, con: 1.05, tint: [1.06, 1, .9], vig: .3, lift: 0, scan: 0},
  vivid: {name: "Vivid", glow: .4, from: .84, sat: 1.32, con: 1.12, tint: [1, 1, 1], vig: .15, lift: 0, scan: 0},
  dream: {name: "Dreamy", glow: 1.3, from: .7, sat: 1.05, con: .97, tint: [1.02, 1, 1.04], vig: .32, lift: .02, scan: 0},
  moody: {name: "Moody", glow: .6, from: .76, sat: .86, con: 1.14, tint: [.93, .98, 1.09], vig: .45, lift: 0, scan: 0},
  screen: {name: "Old screen", glow: .7, from: .74, sat: 1.1, con: 1.08, tint: [1, 1.02, .98], vig: .38, lift: 0, scan: .12},
  // "add old school shaders, lines": screens of other years. More of each has: curve: the glass bulges; mask: the
  // red, green and blue stripes of a tube; shift: red and blue slide apart (px); tape: a video tape's wobble, tear and
  // snow; grid: a dark line between art pixels both ways (a handheld's cells); pal: 1 a handheld's four greens, 2 a
  // terminal's one green
  crt: {name: "Tube TV", glow: 1, from: .7, sat: 1.12, con: 1.1, tint: [1, 1, 1], vig: .5, lift: .01, scan: .34, curve: .16, mask: .2, shift: .7},
  arcade: {name: "Arcade", glow: .8, from: .72, sat: 1.3, con: 1.14, tint: [1, 1, 1], vig: .35, lift: 0, scan: .26, curve: .07, mask: .3},
  tape: {name: "Video tape", glow: .6, from: .74, sat: .9, con: 1.02, tint: [1.02, 1, 1.03], vig: .3, lift: .025, scan: .14, shift: 1.8, tape: 1},
  handheld: {name: "Handheld", glow: 0, from: .9, sat: 1, con: 1.1, tint: [1, 1, 1], vig: 0, lift: 0, scan: 0, grid: .2, pal: 1},
  terminal: {name: "Green terminal", glow: 1.3, from: .55, sat: 1, con: 1.15, tint: [1, 1, 1], vig: .45, lift: 0, scan: .36, curve: .12, pal: 2},
};
const Shader = (() => {
  const VERT = "attribute vec2 p; varying vec2 uv; void main() { uv = p * .5 + .5; gl_Position = vec4(p, 0., 1.); }";
  const HEAD = "precision mediump float; varying vec2 uv; uniform sampler2D uA; ";
  const BRIGHT = HEAD + `uniform vec2 uPx; uniform float uFrom;
    void main() { vec3 c = (texture2D(uA, uv + uPx * vec2(-1., -1.)).rgb + texture2D(uA, uv + uPx * vec2(1., -1.)).rgb + texture2D(uA, uv + uPx * vec2(-1., 1.)).rgb + texture2D(uA, uv + uPx).rgb) * .25;
      float l = dot(c, vec3(.299, .587, .114)); gl_FragColor = vec4(c * smoothstep(uFrom, uFrom + .2, l), 1.); }`;
  const BLUR = HEAD + `uniform vec2 uStep;
    void main() { vec3 c = texture2D(uA, uv).rgb * .227;
      c += (texture2D(uA, uv + uStep * 1.385).rgb + texture2D(uA, uv - uStep * 1.385).rgb) * .316;
      c += (texture2D(uA, uv + uStep * 3.231).rgb + texture2D(uA, uv - uStep * 3.231).rgb) * .0703;
      gl_FragColor = vec4(c, 1.); }`;
  const FINAL = HEAD + `uniform sampler2D uB, uC; uniform vec2 uRes, uOrigin; uniform vec3 uTint;
    uniform float uGlow, uSat, uCon, uVig, uLift, uScan, uCloud, uTile, uT, uArt, uCurve, uMask, uShift, uTape, uGrid, uPal, uPalK;
    float hash(vec2 q) { return fract(sin(dot(q, vec2(127.1, 311.7))) * 43758.5453); }
    float noise(vec2 q) { vec2 i = floor(q), f = fract(q); f = f * f * (3. - 2. * f);
      return mix(mix(hash(i), hash(i + vec2(1., 0.)), f.x), mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), f.x), f.y); }
    void main() {
      vec2 q = uv, mid = uv - .5;
      // the glass of a tube bulges: the picture is pushed out towards its corners, and past its edge there is none
      q = .5 + mid * (1. + uCurve * dot(mid, mid) - uCurve * .25);
      // a tape: each line a little off, and a tear that climbs the screen
      float row = floor((1. - q.y) * uRes.y / 2.);
      q.x += uTape * ((hash(vec2(row, floor(uT * 24.))) - .5) * .0016 + .012 * (1. - smoothstep(0., .035, abs(fract(uT * .09) - (1. - q.y)))));
      vec2 off = vec2(uShift / uRes.x, 0.);
      vec3 c = vec3(texture2D(uA, q + off).r, texture2D(uA, q).g, texture2D(uA, q - off).b), g = texture2D(uB, q).rgb * .6 + texture2D(uC, q).rgb * .7;
      vec2 px = vec2(q.x, 1. - q.y) * uRes;
      if (uCloud > 0.) {                                       // cloud shadows: fixed to the land, an art pixel at a time, drifting east
        vec2 w = floor((px - uOrigin) / uTile * 16.) / 16. * .055 + vec2(-uT * .011, uT * .004);
        float n = noise(w) * .55 + noise(w * 2.1 + 7.3) * .3 + noise(w * 4.3 + 1.7) * .15;
        c *= mix(vec3(1.), vec3(.74, .78, .9), smoothstep(.5, .64, n) * uCloud);
      }
      c = 1. - (1. - c) * (1. - g * uGlow);                    // the glow, laid on as light is
      float l = dot(c, vec3(.299, .587, .114));
      c = (mix(vec3(l), c, uSat) - .5) * uCon + .5;
      c = c * uTint + uLift;
      l = clamp(dot(c, vec3(.299, .587, .114)), 0., 1.);
      // a handheld's four greens (the shade a pixel falls in), or a terminal's one green
      vec3 four = mix(mix(vec3(.06, .22, .06), vec3(.19, .38, .19), step(.3, l)), mix(vec3(.55, .67, .06), vec3(.61, .74, .06), step(.78, l)), step(.55, l));
      if (uPal > .5) c = mix(c, uPal < 1.5 ? four : vec3(.12, 1., .38) * pow(l, 1.7) * 1.25, uPalK);
      c += uTape * (hash(px + uT) - .5) * .07;
      c *= 1. - uVig * smoothstep(.42, .9, distance(uv, vec2(.5)) * 1.25);
      // a dark line under each art pixel; a handheld's cells have one beside each too
      float lineY = step(uArt - 1.5, mod(gl_FragCoord.y, uArt)), lineX = step(uArt - 1.5, mod(gl_FragCoord.x, uArt));
      c *= (1. - uScan * lineY) * (1. - uGrid * max(lineX, lineY)) * (1. + uScan * .4 + uMask * .45);
      // a tube's stripes: each screen pixel shows mostly one of red, green, blue
      float stripe = mod(floor(gl_FragCoord.x), 3.);
      c *= 1. - uMask + uMask * 1.6 * vec3(step(stripe, .5), step(.5, stripe) * step(stripe, 1.5), step(1.5, stripe));
      if (q.x < 0. || q.x > 1. || q.y < 0. || q.y > 1.) c = vec3(0.);
      gl_FragColor = vec4(c, 1.);
    }`;
  let el = null, gl = null, bad = false, P = null, scene = null, targets = [], size = "";
  function program(frag) {
    const mk = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const p = gl.createProgram(); gl.attachShader(p, mk(gl.VERTEX_SHADER, VERT)); gl.attachShader(p, mk(gl.FRAGMENT_SHADER, frag)); gl.bindAttribLocation(p, 0, "p"); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    const u = {}; for (let i = 0; i < gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS); i++) { const n = gl.getActiveUniform(p, i).name; u[n] = gl.getUniformLocation(p, n); }
    return {p, u};
  }
  function texture(w, h) {
    const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    if (w) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    return t;
  }
  function start() {
    el = document.createElement("canvas"); el.id = "fx"; cv.after(el);
    el.addEventListener("webglcontextlost", (e) => { e.preventDefault(); bad = true; el.style.display = "none"; });
    gl = el.getContext("webgl", {alpha: false, antialias: false, depth: false, stencil: false, preserveDrawingBuffer: false});
    if (!gl) throw new Error("no WebGL");
    P = {bright: program(BRIGHT), blur: program(BLUR), final: program(FINAL)};
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    scene = texture();
  }
  function pass(prog, from, to, w, h, set) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, to ? to.fb : null); gl.viewport(0, 0, w, h); gl.useProgram(prog.p);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, from); gl.uniform1i(prog.u.uA, 0);
    set(prog.u); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
  // Called at the end of each frame (render.js): ox, oy where the world's corner is on the screen, S a tile's size, t seconds
  function frame(ox, oy, S, t) {
    const look = SHADERS[opt("shader")];
    if (!look || bad) { for (const c of [el, words]) if (c && c.style.display !== "none") c.style.display = "none"; return; }
    try {
      if (!el) start();
      const w = cv.width, h = cv.height, qw = Math.max(2, w >> 2), qh = Math.max(2, h >> 2);
      if (size !== w + "x" + h) {                              // the window changed: the picture's size, and the quarter-size ones'
        size = w + "x" + h; el.width = w; el.height = h; el.style.width = cv.style.width; el.style.height = cv.style.height;
        for (const q of targets) { gl.deleteFramebuffer(q.fb); gl.deleteTexture(q.tex); }
        targets = [0, 1, 2].map(() => { const tex = texture(qw, qh), fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0); return {tex, fb}; });
      }
      if (el.style.display !== "block") el.style.display = "block";
      const k = opt("shaderk") / 100, [a, b, c] = targets, on = (v) => 1 + (v - 1) * k;
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, scene); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv);
      pass(P.bright, scene, a, qw, qh, (u) => { gl.uniform2f(u.uPx, 1 / w, 1 / h); gl.uniform1f(u.uFrom, look.from); });
      pass(P.blur, a.tex, b, qw, qh, (u) => gl.uniform2f(u.uStep, 1 / qw, 0));               // a tight glow, in a
      pass(P.blur, b.tex, a, qw, qh, (u) => gl.uniform2f(u.uStep, 0, 1 / qh));
      pass(P.blur, a.tex, b, qw, qh, (u) => gl.uniform2f(u.uStep, 3 / qw, 0));               // and a wide one from it, in c
      pass(P.blur, b.tex, c, qw, qh, (u) => gl.uniform2f(u.uStep, 0, 3 / qh));
      const tint = lightAt(clock.phase || 0), day = 1 - Math.min(1, (1 - (.3 * tint[0] + .59 * tint[1] + .11 * tint[2]) / 255) / .36);
      const under = typeof myAt !== "undefined" && myAt && typeof coveredAt === "function" && coveredAt(myAt.x, myAt.y, myAt.z);
      pass(P.final, scene, null, w, h, (u) => {
        gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, a.tex); gl.uniform1i(u.uB, 1);
        gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, c.tex); gl.uniform1i(u.uC, 2);
        gl.uniform2f(u.uRes, W, H); gl.uniform2f(u.uOrigin, ox, oy); gl.uniform1f(u.uTile, S); gl.uniform1f(u.uT, t); gl.uniform1f(u.uArt, zoom * DPR);
        // (by day the whole meadow is bright: a full glow there is a white-out; it is for the dark)
        gl.uniform1f(u.uGlow, look.glow * k * opt("glow") / 100 * (1 - .65 * day)); gl.uniform1f(u.uSat, on(look.sat)); gl.uniform1f(u.uCon, on(look.con));
        gl.uniform3f(u.uTint, on(look.tint[0]), on(look.tint[1]), on(look.tint[2])); gl.uniform1f(u.uLift, look.lift * k);
        gl.uniform1f(u.uVig, opt("corners") ? look.vig * k : 0); gl.uniform1f(u.uScan, look.scan * k);
        for (const [name, v] of [["uCurve", look.curve], ["uMask", look.mask], ["uShift", look.shift], ["uTape", look.tape], ["uGrid", look.grid]]) gl.uniform1f(u[name], (v || 0) * k);
        gl.uniform1f(u.uPal, look.pal || 0); gl.uniform1f(u.uPalK, k);
        gl.uniform1f(u.uCloud, opt("clouds") && !under ? .85 * k * day : 0);
      });
    } catch (e) { bad = true; if (el) el.style.display = "none"; console.warn("shader: off (" + e.message + ")"); }
  }
  // What is written in the world (names, what people say, hearts lost, the small faces over heads) is not for a shader:
  // "your shaders make text bubble unreadable and too bright" (a white bubble glowed, its letters went with it). With a
  // shader on, the frame draws them on a third canvas over the shader's (render.js: Shader.over(true) before them,
  // Shader.over(false) after; `ctx` is pointed at it meanwhile), as they are with no shader.
  let words = null, wg = null, home = null;
  function over(on) {
    if (home) { ctx = home; home = null; }                   // (always back first, whatever happened in between)
    if (!on || !SHADERS[opt("shader")] || bad || !el) return;
    if (!words) { words = document.createElement("canvas"); words.id = "fxwords"; el.after(words); wg = words.getContext("2d"); }
    if (words.width !== cv.width || words.height !== cv.height) { words.width = cv.width; words.height = cv.height; words.style.width = cv.style.width; words.style.height = cv.style.height; }
    if (words.style.display !== "block") words.style.display = "block";
    wg.setTransform(1, 0, 0, 1, 0, 0); wg.globalAlpha = 1; wg.clearRect(0, 0, words.width, words.height);
    wg.setTransform(DPR, 0, 0, DPR, 0, 0); wg.imageSmoothingEnabled = false;
    home = ctx; ctx = wg;
  }
  const layers = () => [el, words].filter((c) => c && c.style.display === "block");      // (zoom.js: they glide with the picture)
  return {frame, over, layers, get el() { return el; }, get words() { return words; }, get works() { return !bad; }};
})();
