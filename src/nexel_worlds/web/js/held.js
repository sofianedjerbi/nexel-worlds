// What a player holds is in their paw: the bar's selected slot (yours: `selected`; the others': the server's `held`, sent
// by `hold` when your selection changes). A block as a tiny cube (cube_icons.js), a tool gripped (hold_art.js), anything else its icon made 8 px
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
  const AT = [[14, 22], [26, 21], [26, 22], [16, 22]], N = 7;
  const at = (p) => AT[DIR_ROW(p)];
  // The body's own bob in a frame of the sheet (sx, sy: its 48 x 48 cell): how many art px its top is lower than in the
  // row's first frame. The paw goes with it (the item stood still while the body walked up and down under it)
  const tops = new WeakMap();
  function top(sheet, sx, sy) {
    let m = tops.get(sheet); if (!m) tops.set(sheet, m = new Map()); const k = sx + "," + sy; if (m.has(k)) return m.get(k);
    let t = 0; try { const g = document.createElement("canvas").getContext("2d", {willReadFrequently: true}); g.canvas.width = g.canvas.height = 48; g.drawImage(sheet, sx, sy, 48, 48, 0, 0, 48, 48);
      const d = g.getImageData(0, 0, 48, 48).data; t = 48; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) { t = Math.floor(i / 4 / 48); break; } } catch (e) { t = 0; }
    m.set(k, t); return t;
  }
  const lift = (sheet, sx, sy) => (sheet ? top(sheet, sx, sy) - top(sheet, 0, sy) : 0);
  // (an aim's pose, aim_art.js: in the paw where the pose holds it, its middle there; a jump's: the paw's own row moved, jump_art.js.)
  // A tool (hold_art.js) is held by its grip, the hand over it: `name` is what `c` is the picture of
  function draw(c, p, cellX, cellY, z, sheet, sx, sy, name) { const aim = sy >= ANIM.aim * 48 && sy < (ANIM.aim + 4) * 48 && Object.keys(AimArt.COL)[sx / 48], A = aim && AimArt.PAW[aim], t = A && A[DIR_ROW(p)];
    const [ax, ay] = t ? [t[0] - 3, t[1] - 3] : at(p), J = sy >= ANIM.jump * 48 && sy < (ANIM.jump + 4) * 48, dy = t ? 0 : J ? JumpArt.shift(DIR_ROW(p), sx / 48, ay + 3) : lift(sheet, sx, sy);
    // (a sword, a spear: one pose, at the hip; it sways with the walk's (the run's) frame: hold_art.js LOW)
    const step = sy >= ANIM.walk * 48 && sy < (ANIM.run + 4) * 48 ? sx / 48 : -1;
    const tool = name && sheet && HoldArt.art(name, DIR_ROW(p), t ? aim : "rest", sheet, t, step);
    if (tool) return ctx.drawImage(tool, cellX, cellY + dy * z, 48 * z, 48 * z);
    ctx.drawImage(c, cellX + ax * z, cellY + (ay + dy) * z, c.width * z, c.height * z); }
  let sent;
  // yours, to the server when it changes (and again whenever the server has another: a new connection)
  function sync(s) { const want = selected || null; if (s && (s.held || null) !== want && sent !== want + "@" + (s.held || "")) { sent = want + "@" + (s.held || ""); rpc("hold", {item: want}); } }
  return {art, draw, at, lift, sync};
})();
