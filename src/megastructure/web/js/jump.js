// Up or down a layer (or several, down): a hop, for a person or a creature alike (sim/bodies.py: one way to stand on
// the land). Between two tiles a body is placed on the straight line between their heights (relief.js liftOf: the
// camera and the name over a head follow that line, smoothly). The hop is one arc over that line, from the middle
// of a tile to the middle of the next, as a thrown thing goes: high enough to clear the edge it goes over. Its
// shadow stays on the ground under it (the ground it leaves, until it is over the edge), it holds the pose it took
// off in (no walking on air), and there is dust where it leaves the ground and where it lands.
// It is quick: a hop takes the time of a step (walk.js: your screen doesn't slow down for it). Seen frame by frame,
// what looked wrong before was the hang: a step and a half long, the body near the top of its arc for most of it.

const JUMP = {over: 2, off: 1};      // art px the arc clears the edge by: going up, coming down

// -> null on the level, or {body, ground: art px over the straight line (its feet, its shadow)}
function jumpOf(p) {
  const ax = Math.floor(p.x), ay = Math.floor(p.y), bx = Math.ceil(p.x), by = Math.ceil(p.y);
  if (ax === bx && ay === by) return null;
  const la = standAt(ax, ay), lb = standAt(bx, by);
  if (la === lb) return null;
  const f = ax === bx ? p.y - ay : p.x - ax, d = (lb - la) * RELIEF_STEP;        // how far across; px from the first to the second
  const up = (ax === bx ? p.ty - p.y || p.fy : p.tx - p.x || p.fx) >= 0 === d > 0;   // going to the higher one?
  return {body: (Math.abs(d) / 2 + (up ? JUMP.over : JUMP.off)) * 4 * f * (1 - f), ground: (f < .5 ? 0 : d) - d * f};
}

// Called as a body is drawn: dust as it leaves the ground, dust and a sound as it lands. -> its hop, or null
function jumping(p) {
  const j = jumpOf(p), tx = Math.round(p.x), ty = Math.round(p.y);
  if (j && p.jfrom === undefined) { p.jfrom = standAt(tx, ty); burst(p.x, p.y + .35 - UP, "dust", 3, {up: .8, spread: 1.6, g: 3, life: .3}); }
  if (!j && p.jfrom !== undefined) {
    const down = standAt(tx, ty) < p.jfrom;
    smoke(p.x, p.y + .35 - UP, down ? 4 : 3, down ? .4 : .3); sfx(down ? "thud" : "step", tx, ty);
    p.jfrom = p.jpose = undefined;
  }
  return j;
}
// Its shadow, on the ground under it (x, y: where the body is drawn standing; z: the zoom)
function jumpShadow(j, x, y, S, z, wide = 5) {
  ctx.fillStyle = "rgba(40,30,50,.2)";
  ctx.beginPath(); ctx.ellipse(x + S / 2, y - Math.round(j.ground * z) + S - 2 * z, Math.max(wide * .6, wide - (j.body - j.ground) / 6) * z, 2 * z, 0, 0, 7); ctx.fill();
}
