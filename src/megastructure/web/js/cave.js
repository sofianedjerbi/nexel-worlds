// Underground (layers.py): each level below the surface is a region far east of the one above. Down there it's
// dark: you see a little way around you, around fires and torches, and under the ladders where daylight falls in.
// Changing level fades through black, like stepping through a door.

const LAYER = 1000000;
const depthOf = (x) => Math.max(0, Math.floor((x + LAYER / 2) / LAYER));
let caveDark = null, lastDepth = null, levelFade = 0;

function drawCave(vis, sx, sy, S, t, now) {
  const d = depthOf(cam.x);
  if (lastDepth !== null && d !== lastDepth) levelFade = now;
  lastDepth = d;
  if (d) {
    if (!caveDark) caveDark = document.createElement("canvas");
    if (caveDark.width !== W || caveDark.height !== H) { caveDark.width = W; caveDark.height = H; }
    const g = caveDark.getContext("2d");
    g.globalCompositeOperation = "source-over";
    g.clearRect(0, 0, W, H);
    g.fillStyle = `rgba(14,10,18,${Math.min(.94, .82 + d * .02)})`;          // darker deeper down
    g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = "destination-out";
    const light = (x, y, r) => {
      const gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, "rgba(0,0,0,1)"); gr.addColorStop(.55, "rgba(0,0,0,.75)"); gr.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2);
    };
    for (const p of ents.values()) if (p.e && p.e.kind === "agent") light(sx(p.x) + S / 2, sy(p.y) + S / 2, S * 4.5);
    for (const b of vis) for (const [i, c] of b.objs) {
      const x = b.bx * B + i % B, y = b.by * B + (i / B | 0);
      if (c === "^" || c === "x") light(sx(x) + S / 2, sy(y) + S / 2, S * (5 + .3 * Math.sin(t * 13 + x)));
      if (c === "l") light(sx(x) + S / 2, sy(y) + S / 2, S * 2.5);       // daylight falling down the hole
    }
    for (const f of fireAt) light(sx(f.x) + S / 2, sy(f.y) + S / 2, S * 4);
    ctx.drawImage(caveDark, 0, 0, W, H);
  }
  const k = (now - levelFade) / 700;                                    // through black when changing level
  if (levelFade && k < 1) { ctx.fillStyle = `rgba(10,7,12,${1 - k * k})`; ctx.fillRect(0, 0, W, H); }
  return d;
}
