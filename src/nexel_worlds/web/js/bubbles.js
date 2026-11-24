// What people say, over their heads. A bubble is drawn in the pixel of its text (the 18 px font's is 2 px): stepped
// corners, a dark edge, a shade along its foot, a stepped tail. A long line is wrapped (seven rows hold all a chat line can be: 200 letters). Someone who says
// several things keeps them in a pile: the oldest lowest, by the head, with the tail; newer ones above it. When
// one goes the ones above come down onto its place. Two people's piles never cover each other: the later one is
// raised over the other. While someone speaks their name is not written over their head (characters.js): the tail
// points at the head itself and the name is a small dark tab on the top of the pile, as the label of a speech box.
// state.js adds to `bubbles`; render.js calls drawBubbles last, over everything.

const BUBBLE = {q: 2, life: 7, after: 3.5, most: 3, wide: 400, lines: 7, pitch: 10, padX: 4, padY: 3, gap: 1, fall: 12, fade: .25,
  ink: "#5b3f36", paper: "#fff6e2", shout: "#ffe3a3", foot: "#ecd7b0", footShout: "#f2c877", shade: "rgba(60,40,30,.25)", edge: 16};
// THE BUBBLE'S PIXEL (q, its letters' own: the 18 px font's is 2 CSS px) is a whole number of the screen's px: 2 x density, rounded (a density of 1.25: 3 px, the letters 21.6 CSS px).
// Everything of a bubble is a number of them (pitch, padX, padY, gap: in q). At 1.25 its 2 CSS px were 2.5 px of the screen: its edges and letters soft, and another raster each place it was drawn at
const bubbleQ = () => { const d = window.devicePixelRatio || 1; return Math.max(1, Math.round(BUBBLE.q * d)) / d; };

// The line as the rows it is written in (at most BUBBLE.lines, the last ending in … if there was more), and its size.
function bubbleShape(b, q = bubbleQ()) {
  if (b.rows && b.q === q) return b;
  const words = b.text.trim().split(/\s+/), rows = [""];
  const fits = (s) => ctx.measureText(s).width <= BUBBLE.wide;
  for (let w of words) {
    while (!fits(w)) {                                       // a word wider than a bubble: broken where it fills the row
      let n = w.length; while (n > 1 && !fits(w.slice(0, n))) n--;
      if (rows[rows.length - 1]) rows.push(""); rows[rows.length - 1] = w.slice(0, n); w = w.slice(n);
    }
    const last = rows[rows.length - 1], more = last ? last + " " + w : w;
    if (fits(more)) rows[rows.length - 1] = more; else rows.push(w);
  }
  if (rows.length > BUBBLE.lines) {
    rows.length = BUBBLE.lines; let s = rows[BUBBLE.lines - 1];
    while (s && !fits(s + "…")) s = s.slice(0, -1);
    rows[BUBBLE.lines - 1] = s.trimEnd() + "…";
  }
  const even = (v) => Math.ceil(v / q) * q;
  b.q = q; b.rows = rows; b.w = Math.max(even(Math.max(...rows.map((r) => ctx.measureText(r).width))) + 2 * BUBBLE.padX * q, 16 * q);   // (as wide as its words; no narrower than its tail needs. It was as wide as the name's tab: a short line in a mostly empty box)
  b.h = (rows.length * BUBBLE.pitch + 2 * BUBBLE.padY - 2) * q;
  b.life = Math.max(BUBBLE.life, b.text.length * BABBLE.letter + BUBBLE.after);     // (long enough to be written, then read)
  return b;
}
// One bubble: its box at (x, y), its tail's middle at tx if it has one.
function bubbleBox(b, x, y, tx) {
  const q = b.q, {w, h} = b, r = (c, X, Y, W_, H_) => { ctx.fillStyle = c; ctx.fillRect(X, Y, W_, H_); };
  const paper = b.shout ? BUBBLE.shout : BUBBLE.paper;
  r(BUBBLE.shade, x + q, y + h, w - 2 * q, q);
  r(BUBBLE.ink, x + q, y, w - 2 * q, h); r(BUBBLE.ink, x, y + q, w, h - 2 * q);
  r(paper, x + 2 * q, y + q, w - 4 * q, h - 2 * q); r(paper, x + q, y + 2 * q, w - 2 * q, h - 4 * q);
  r(b.shout ? BUBBLE.footShout : BUBBLE.foot, x + 2 * q, y + h - 2 * q, w - 4 * q, q);
  if (tx != null) {                                          // the tail: three steps down to a point
    // (the paper runs down into it: the shade along the bubble's foot stops at it, and is at the tail's own foot.
    // It ran across over the tail: a line between the bubble and its tail)
    r(paper, tx - 3 * q, y + h - 2 * q, 6 * q, 2 * q);
    r(BUBBLE.ink, tx - 3 * q, y + h, 6 * q, q); r(paper, tx - 2 * q, y + h, 4 * q, q);
    r(BUBBLE.ink, tx - 2 * q, y + h + q, 4 * q, q); r(b.shout ? BUBBLE.footShout : BUBBLE.foot, tx - q, y + h + q, 2 * q, q);
    r(BUBBLE.ink, tx - q, y + h + 2 * q, 2 * q, q);
  }
}
// The speaker's name: a dark tab standing on the top left of the pile's highest bubble.
function bubbleTab(name, x, y, mine, q, bw) {
  const w = Math.ceil(ctx.measureText(name).width / q) * q + 6 * q, h = 11 * q;
  if (w + 6 * q > bw) x += Math.round((bw - w - 6 * q) / 2 / q) * q;     // (wider than a short bubble: centred over it)
  ctx.fillStyle = BUBBLE.ink; ctx.fillRect(x + 3 * q, y - h, w, h); ctx.fillRect(x + 2 * q, y - h + q, w + 2 * q, h - q);
  ctx.fillStyle = mine ? "#fff1a8" : BUBBLE.paper; ctx.fillText(name, x + 6 * q, y - 2 * q);
}
const speaking = (name) => bubbles.some((b) => b.name === name && b.at);     // (their name is on their bubbles)
let bubbleT = 0, bubbleBoxes = [];
// Is a box of the screen under a bubble drawn last frame (with its name's tab)? Another's name there is not written: it was
// written under the bubble, a few letters of it showing past its edge ("Tobi" over "Nell": "Tobi ell"). (characters.js)
const underBubble = (x, y, w, h) => bubbleBoxes.some((o) => x < o.r && x + w > o.l && y < o.b && y + h > o.t);
function drawBubbles(sx, sy, S, t) {
  bubbleBoxes = [];
  if (!opt("bubbles")) { bubbles = []; bubbleT = t; return; }
  const dt = Math.min(.1, Math.max(0, t - bubbleT)), q = bubbleQ(), snap = (v) => Math.round(v / q) * q; bubbleT = t;
  ctx.font = 9 * q + "px SproutPixel"; ctx.textAlign = "left";
  bubbles = bubbles.filter((b) => t - b.t < bubbleShape(b, q).life);
  const by = new Map();                                      // each speaker's, oldest first
  for (const b of bubbles) { if (!by.has(b.name)) by.set(b.name, []); by.get(b.name).push(b); }
  const piles = [];
  for (const [name, mine] of by) {
    while (mine.length > BUBBLE.most) bubbles.splice(bubbles.indexOf(mine.shift()), 1);      // a fourth line: the oldest goes at once
    const p = [...ents.values()].find((e) => e.e && e.e.kind === "agent" && e.e.name === name); if (!p) continue;
    let up = 0;
    for (const b of mine) {                                  // where each rests, as px above the lowest's foot; it comes down to it
      b.up = b.up === undefined || b.up < up ? up : Math.max(up, b.up - Math.max(q, (b.up - up) * dt * BUBBLE.fall));
      up += b.h + BUBBLE.gap * q;
    }
    const o = BodyPlace.over(p, S), tx = onArt(bodyX(p, sx) + S / 2 + o[0]), foot = onArt(bodyY(p, sy) + o[1] - (p.e.hp < HP_MAX ? 9 * artPx() + 4 : 4 * artPx())) - 3 * q,     // (the tail's point: over the head, or over the health bar)
      // (ON THE LAND'S PIXEL, as the body it is over (state.js onArt): it went by the bubble's own 2 px, the body by the land's (3 at zoom 3): walking, the bubble went 1 px off the head and back each step, "blurry")
      w = Math.max(...mine.map((b) => b.w));
    const top = foot - Math.max(...mine.map((b) => b.up + b.h)) - 11 * q, mid = bodyY(p, sy) + o[1] + S / 2;     // (with the name's tab; mid: the middle of the body)
    // Said only by someone on the screen, a margin in from its edges ("dialogue shows even off-screen": a bubble was
    // pushed in at the edge, or hung over nobody, its speaker below the screen or behind its side)
    // (nor someone the eye does not see, behind a house: hd.js hidden)
    const hid = name !== me && HdLook.live && HdLook.hidden(p.x + .5, p.y + .5, p.e.z !== undefined ? p.e.z : floorAt(Math.round(p.x), Math.round(p.y)));
    if (hid || tx < BUBBLE.edge || tx > W - BUBBLE.edge || foot + 3 * q < BUBBLE.edge || mid > H - BUBBLE.edge) { for (const b of mine) b.at = b.up = undefined; continue; }
    piles.push({mine, tx, foot, w, top, y: p.y, name, mid});
  }
  piles.sort((a, b) => b.y - a.y);                           // the nearest to the bottom of the screen keep their place
  const placed = [];
  for (const pile of piles) {
    const x0 = (b) => Math.max(4, Math.min(W - 4 - b.w, pile.tx - onArt(b.w / 2)));   // (the tail's point less half the bubble on the land's pixel: it goes as the body does, px for px)
    for (let n = 0; n < 8; n++) {                            // raised over any pile it would cover
      const l = Math.min(...pile.mine.map(x0)), hit = placed.find((o) => l < o.r + 4 && l + pile.w > o.l - 4 && pile.top < o.b + 4 && pile.foot + 3 * q > o.t - 4);
      if (!hit) break;
      const lift = pile.foot + 3 * q - (hit.t - 4); pile.foot -= lift; pile.top -= lift;
    }
    // (the first screen: not under its name, its line, its window, title_scene.js, nor said by someone the window hides. Asked HERE, where the pile will be drawn: asked before it was raised over another's, a pile clear of the line was then lifted under it)
    // (and whole on the screen: a pile raised over the top edge is not drawn cut)
    const l0 = Math.min(...pile.mine.map(x0)), l = Math.min(l0, pile.tx - S / 2), r = Math.max(l0 + pile.w, pile.tx + S / 2);
    if (pile.top < 4 || (typeof TitleScene !== "undefined" && TitleScene.hides(l, pile.top, r - l, pile.mid - pile.top))) { for (const b of pile.mine) b.at = b.up = undefined; continue; }
    placed.push({l: Math.min(...pile.mine.map(x0)), r: Math.min(...pile.mine.map(x0)) + pile.w, t: pile.top, b: pile.foot + 3 * q});
    { const o = placed[placed.length - 1]; bubbleBoxes.push({l: o.l, r: Math.max(o.r, o.l + ctx.measureText(pile.name).width + 10 * q), t: o.t, b: o.b}); }   // (the tab can be wider than a short bubble)
    pile.mine.forEach((b, n) => {
      const since = t - b.t, jolt = b.shout && since < .5 ? (Math.floor(since * 30) % 2 ? q : -q) : 0;      // (a shout: its bubble shakes as it lands)
      const x = x0(b) + jolt, y = pile.foot - snap(b.up) - b.h;
      ctx.globalAlpha = Math.max(0, Math.min(1, (b.life - since) / BUBBLE.fade));
      bubbleBox(b, x, y, n ? null : Math.max(x + 5 * q, Math.min(x + b.w - 5 * q, pile.tx)));
      ctx.fillStyle = BUBBLE.ink;
      let left = written(b.text, since).length;              // written out as it is said (babble.js), row after row
      // (the letters in the middle of the paper: 4 px over a capital, 4 under it to the foot's shade, where a g or a y
      // comes down to. They were a font pixel higher: 2 px over, 6 under, and a line of capitals looked hung from the top)
      b.rows.forEach((row, i) => { if (left > 0) ctx.fillText(row.slice(0, left), x + BUBBLE.padX * q, y + (BUBBLE.padY + 7 + i * BUBBLE.pitch) * q); left -= row.length + 1; });
      b.at = [x, y];                                          // (where it was drawn: for the tests)
      if (n === pile.mine.length - 1) { ctx.globalAlpha = pile.mine.length > 1 ? 1 : ctx.globalAlpha; bubbleTab(pile.name, x, y, me && pile.name === me, q, b.w); }
    });
  }
  ctx.globalAlpha = 1; ctx.textAlign = "start";
}
