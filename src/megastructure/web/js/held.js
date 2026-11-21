// What a player holds is in their paw: the bar's selected slot (yours: `selected`; the others': the server's `held`, sent
// by `hold` when your selection changes). A block as a tiny cube (cube_icons.js), anything else its icon made 8 px
// (characters.js biteIcon: crisp, whole px). Drawn at the paw of the facing the body has, in front of it, behind it when
// they face away. Not while a tool swings (the sheet's swing draws the tool), they eat (the food is at the mouth), sleep,
// climb rungs or sail.
const Held = (() => {
  const arts = new Map();
  function art(name) {
    if (!name) return null;
    if (!arts.has(name)) { let c = null; try { c = CubeIcon.is(name) ? CubeIcon.canvas(name, N) : biteIcon(name, 0); } catch (e) { c = null; } if (c) arts.set(name, c); return c; }
    return arts.get(name);
  }
  // the 8 x 8 picture's top left in the 48 x 48 cell, per DIR_ROW (down, up, right, left): the right paw, low at the side
  const AT = [[14, 22], [28, 21], [26, 22], [16, 22]], N = 7;
  const at = (p) => AT[DIR_ROW(p)];
  function draw(c, p, cellX, cellY, z) { const [ax, ay] = at(p); ctx.drawImage(c, cellX + ax * z, cellY + ay * z, c.width * z, c.height * z); }
  let sent;
  // yours, to the server when it changes (and again whenever the server has another: a new connection)
  function sync(s) { const want = selected || null; if (s && (s.held || null) !== want && sent !== want + "@" + (s.held || "")) { sent = want + "@" + (s.held || ""); rpc("hold", {item: want}); } }
  return {art, draw, at, sync};
})();
