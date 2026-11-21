// THE WAIT FOR THE ISLAND: while the game's script and pictures come (the demo: js/game.*.js and the pack, a phone's
// line: seconds), the still picture of the island is not alone: over it, above the window, a small pixel scene in the
// window's own colours, edges and px (--q): a strip of the meadow and the game's cat walking along it; as far as the cat
// has walked is how much has come (real bytes: the pack's as they arrive, web_bundle.py; in development the pictures,
// assets.js). The owner: "the placeholder waiting screen unanimated looks bad". It goes when the island is painted
// (body.scene, title_scene.js). No game global: it runs before the game's script has come.
(() => {
  if (new URLSearchParams(location.search).get("follow")) return;
  const W = 132, H = 34, cv = document.createElement("canvas"), g = cv.getContext("2d"), cat = new Image();
  cv.id = "loading"; cv.width = W; cv.height = H; document.body.appendChild(cv);
  // the game's one cat sheet (its walk to the east: row 6, 8 frames of 48 px): in the demo the pack's first bytes, as soon as they are in (web_bundle.py)
  const sheet = () => { const P = window.ASSET_PACK, at = P && P.files["character.png"];
    if (!at) cat.src = "assets/character.png"; else if (P.parts && P.got >= at[0] + at[1]) cat.src = URL.createObjectURL(new Blob(P.parts).slice(at[0], at[0] + at[1], "image/png")); };
  const C = {edge: "#6b4a3a", panel: "#e8cfa6", lit: "#fbf0d6", dim: "#c49a6c", well: "#d9bd90", wellDark: "#b8946a", grass: "#a9c85c", grassLit: "#c0d470",
    tuft: "#8fb04f", path: "#d9b27a", pathDark: "#bf9462", pathLit: "#ecd09a", gold: "#e0b84e", goldLit: "#fff1a8"};
  // how much has come, 0..1: the script and the pack by their bytes (the demo), else the pictures loaded
  const got = () => {
    const P = window.ASSET_PACK;
    if (P && P.size) return Math.min(1, ((P.got || 0) + (typeof titleDraw === "function" ? P.js : 0)) / (P.size + P.js));
    return window.ASSETS_OF ? (window.ASSETS_IN || 0) / window.ASSETS_OF : 0;
  };
  let shown = 0, t0 = performance.now(), gone = false, last = -1e9;
  const rect = (x, y, w, h, c) => { g.fillStyle = c; g.fillRect(x, y, w, h); };
  const place = () => {                                             // above the window, on its middle, a whole screen px an art px
    const m = document.querySelector("#joinbox .menu");
    if (!m) return;
    const r = m.getBoundingClientRect(), d = devicePixelRatio || 1, px = Math.max(1, Math.round(r.width / 150 * d)) / d;   // (the window is 150 of its px wide: title.css)
    cv.style.width = W * px + "px"; cv.style.height = H * px + "px";
    cv.style.left = Math.round((r.left + r.width / 2 - W * px / 2) * d) / d + "px";
    cv.style.top = Math.round((r.top - (H + 6) * px) * d) / d + "px";
  };
  function draw(now) {
    if (gone) return;
    if (!document.body.classList.contains("title") || document.body.classList.contains("scene")) { gone = true; cv.classList.add("out"); setTimeout(() => cv.remove(), 600); return; }
    if (now - last < 90) { requestAnimationFrame(draw); return; }   // (11 pictures a second, the walk's own pace: the page's thread is busy making the game)
    last = now;
    if (!cat.src) sheet();
    shown += (got() - shown) * .3;                                  // (eased, never ahead of what has come)
    place();
    const t = (now - t0) / 1000;
    // the panel: the window's own edge, light and shade
    rect(0, 0, W, H, C.edge); rect(1, 1, W - 2, H - 2, C.panel); rect(1, 1, W - 2, 1, C.lit); rect(1, 1, 1, H - 2, C.lit); rect(1, H - 2, W - 2, 1, C.dim); rect(W - 2, 1, 1, H - 2, C.dim);
    // the strip of meadow (a well in the panel): grass, the path walked so far behind the cat
    const X = 4, Y = 4, SW = W - 8, SH = H - 8, ground = Y + SH - 10;
    rect(X - 1, Y - 1, SW + 2, SH + 2, C.wellDark); rect(X, Y, SW, SH, "#9fd3e6");     // (a little sky over the meadow)
    g.save(); g.beginPath(); g.rect(X, Y, SW, SH); g.clip();           // (nothing past the well: the clouds come in from its edge)
    rect(X, Y, SW, 3, "#bfe3ee");
    for (const [cx0, cy, cw] of [[14, 8, 12], [62, 6, 16], [100, 9, 10]]) { const cx = X + ((cx0 + Math.floor(t * 2)) % (SW + 20)) - 20; rect(cx, cy, cw, 3, "#f4fbfd"); rect(cx + 3, cy - 2, cw - 7, 2, "#f4fbfd"); rect(cx, cy + 3, cw, 1, "#d6ecf3"); }
    rect(X, ground, SW, Y + SH - ground, C.grass); rect(X, ground, SW, 1, C.grassLit);
    for (let i = 0; i < SW; i += 7) { const k = (i * 37) % 5; rect(X + i + k, ground + 2 + (i % 3), 1, 1, C.tuft); rect(X + i + k + 1, ground + 1 + (i % 3), 1, 1, C.tuft); }
    const walked = Math.round(shown * (SW - 14));
    rect(X, ground + 3, walked + 7, 4, C.path); rect(X, ground + 3, walked + 7, 1, C.pathLit); rect(X, ground + 6, walked + 7, 1, C.pathDark);
    // flowers ahead, a sunflower at the end: where the cat is going
    for (const [fx, fc] of [[30, "#e98aa0"], [58, "#9bb8f0"], [86, "#e98aa0"], [104, "#f2d36b"]]) if (fx > walked + 10) { rect(X + fx, ground - 2, 1, 2, C.tuft); rect(X + fx - 1, ground - 3, 3, 1, fc); rect(X + fx, ground - 4, 1, 1, fc); }
    rect(X + SW - 6, ground - 12, 1, 12, "#6f9a44"); rect(X + SW - 8, ground - 15, 5, 5, "#f2c14e"); rect(X + SW - 7, ground - 14, 3, 3, "#8a5a33");
    // the cat: its walk, 8 frames at 10 a second, its feet on the path (the sheet's frame: the body's 16 px in its middle)
    if (cat.complete && cat.naturalWidth) {
      const f = Math.floor(t * 10) % 8, cx = X + walked - 12;
      g.drawImage(cat, f * 48, 6 * 48, 48, 48, cx, ground + 5 - 31, 48, 48);
    }
    g.restore();
    requestAnimationFrame(draw);
  }
  cv.classList.add("in"); requestAnimationFrame(draw);
})();
