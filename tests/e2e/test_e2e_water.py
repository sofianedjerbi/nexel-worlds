"""Clear water (the settings' Picture page, on by default; waterbed.js, vox_water.js): the water is seen through to a
bed drawn as blocks, tinted by its depth; deep water is not seen through; off, it is the one painted face it was;
a bed is made again when the land near it changes; a swimmer's body under the face is tinted."""
import random

READY = "(() => { const [vx, vy, vw, vh] = viewRect(2); for (let y = vy; y <= vy + vh; y += 8) for (let x = vx; x <= vx + vw; x += 8) { const b = blockOf(x, y); if (b && b.px && !Voxels.made(b)) return false; } return dirtyTiles.length === 0; })()"
# the land's own picture (the engine's canvas), one frame at a fixed time: a hash of it; and how many px differ from the last one taken (again: the land made from nothing first)
GRAB = """async (again) => {
  const settle = () => new Promise((ok) => { const step = () => ((%s) ? requestAnimationFrame(() => requestAnimationFrame(ok)) : requestAnimationFrame(step)); requestAnimationFrame(step); });
  if (again) { Voxels.engine.forget(() => false); await new Promise((ok) => requestAnimationFrame(ok)); }
  await settle(); await settle();
  let got = null; const f0 = Voxels.frame; Voxels.frame = (...a) => { got = a; f0(...a); };
  await new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(ok))); Voxels.frame = f0;
  got[4] = 123.456; got[6] = null; f0(...got);
  const gl = VoxGL.gl, w = gl.drawingBufferWidth, h = gl.drawingBufferHeight, px = new Uint8Array(w * h * 4); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
  const was = window.__px; window.__px = px; let n = 0, hash = 0; for (let i = 0; i < px.length; i += 4) { hash = (Math.imul(hash, 31) + px[i] * 65536 + px[i + 1] * 256 + px[i + 2]) | 0; if (was && (px[i] !== was[i] || px[i + 1] !== was[i + 1] || px[i + 2] !== was[i + 2])) n++; }
  return {hash, differ: was ? n : -1, faces: Voxels.engine.faces};
}""" % READY
# the colour that most px of a part of the picture have: [x0, y0, x1, y1] in tiles
MOST = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
  const S = TS(), [ox, oy] = screenOrigin(S), d = ctx.getImageData(Math.round((ox + x0 * S) * DPR), Math.round((oy + y0 * S) * DPR), Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)).data, n = new Map();
  for (let i = 0; i < d.length; i += 4) { const k = d[i] + ',' + d[i + 1] + ',' + d[i + 2]; n.set(k, (n.get(k) || 0) + 1); }
  ok([...n].sort((a, b) => b[1] - a[1])[0][0].split(',').map(Number)); })))"""
RESET = "(() => { setOpt('clearwater', true); setOpt('shimmer', true); setOpt('depth', true); return 1; })()"


def plain(game):
    """The flat picture, no waves and no light on it, no sun: a px is its paint and the water's tint, nothing else."""
    game.flat(); game.clear_area(10); game.rpc("dev_time", phase=.3)
    game.js("(() => { setOpt('shimmer', false); setOpt('depth', false); setOpt('clearwater', true); return 1; })()")


def test_shallow_water_shows_its_bed_tinted_and_deep_water_is_not_seen_through(game):
    plain(game)
    game.stamp(-8, -6, ["~" * 5] * 4); game.stamp(1, -9, [")" * 9] * 9)         # a pond one level deep at its banks; a piece of the deep (wide: the dark is four tiles from a bank or more, waterbed.js)
    x, y = game.pos(); game.wait(READY, 20000); game.rest()
    # a pond's tile by its west bank with nothing floating on it: its own bed shows in its south half (a bed one deep is drawn a level down the picture)
    row = next(j for j in range(1, 4) if game.js(f"hash({x - 8}, {y - 6 + j}, 41) >= .09"))
    tx, ty = x - 8, y - 6 + row
    assert game.js(f"WaterBed.depth({tx}, {ty})") == 1 and game.js(f"topAt({tx}, {ty})") == 0      # (the bed is for the eye: the tile is at its level, as ever)
    got = game.js(MOST, [tx + .3, ty + .6, tx + .8, ty + .95])
    sand, tint, a = (236, 220, 174), (104, 204, 208), .52                        # water.js: the sand a level down; waterbed.js: the tint over it and how much of it
    want = [s * (1 - a) + t * a for s, t in zip(sand, tint)]
    assert all(abs(g - w) <= 4 for g, w in zip(got, want)), (got, want)
    assert game.js(f"[WaterBed.depth({x + 5}, {y - 4}), WaterBed.depth({x + 2}, {y - 4}), WaterBed.depth({x + 1}, {y - 4})]") == [4, 2, 2]      # its middle; nearer its bank one basin, to the bank (its kind is deeper than a rim)
    deep = game.js(MOST, [x + 5, y - 4.8, x + 6, y - 4.1])
    assert all(abs(g - w) <= 3 for g, w in zip(deep, (72, 115, 150))), deep      # the deep: water.js's own deep colour, all of it
    game.js("(() => { setOpt('clearwater', false); return 1; })()"); game.wait(READY, 20000); game.rest()
    assert game.js(MOST, [tx + .3, ty + .6, tx + .8, ty + .95]) != got           # (off: another picture there)
    game.js(RESET)


def test_off_the_water_is_one_painted_face_and_on_again_off_again_it_is_the_same_picture(game):
    plain(game)
    game.stamp(-8, -6, ["~" * 6] * 4); game.stamp(-2, -6, ["..."] * 2, levels=["333"] * 2); game.wait(READY, 20000); game.rest()
    x, y = game.pos()
    game.js("(() => { setOpt('clearwater', false); window.__px = null; return 1; })()"); off = game.js(GRAB, False)
    assert game.js(f"Voxels.engine.faces") == off["faces"] and not game.js(f"WaterBed.on")
    game.js("(() => { setOpt('clearwater', true); return 1; })()"); on = game.js(GRAB, False)
    assert on["differ"] > 2000 and on["faces"] > off["faces"], (on, off)         # on: the beds are there (more faces), the picture another
    game.js("(() => { setOpt('clearwater', false); return 1; })()"); again = game.js(GRAB, False)
    assert again["hash"] == off["hash"] and again["faces"] == off["faces"], (again, off)      # off again: to the px what it was, nothing of the beds left
    game.js(RESET)


def test_a_bed_is_made_again_when_the_land_near_it_changes(game):
    plain(game)
    game.stamp(-9, -7, ["~" * 14] * 6); game.stamp(-9, -1, ["....~~~~......"]); game.wait(READY, 20000); game.rest()
    rnd = random.Random(7); game.js("(() => { window.__px = null; return 1; })()")
    for i in range(10):                                                          # a bank dug, earth put in the water, a hole flooded: where the dice say
        kind, dx, dy = rnd.choice(["dig", "fill", "flood"]), rnd.randint(-10, 5), rnd.randint(-8, 0)
        game.stamp(dx, dy, ["~" if kind == "flood" else "."], levels=[] if kind == "fill" else ["a"])
        game.js(GRAB, False); n = game.js(GRAB, True)["differ"]                  # the picture as it is; then the same world made from nothing
        assert n == 0, (i, kind, dx, dy, n)
    game.js(RESET)


def test_a_swimmers_body_under_the_water_is_tinted(game):
    game.flat(); game.clear_area(10); game.rpc("dev_time", phase=.3)
    game.stamp(-3, -3, ["~" * 7] * 5); x, y = game.pos()
    game.rpc("dev_teleport", x=x, y=y - 1, z=0); game.wait(f"myAt && myAt.y === {y - 1}", 8000); game.wait(READY, 20000); game.rest()
    assert game.js("swimsAt(ents.get('agent' + myId), ents.get('agent' + myId).e)")
    # a few frames with the setting on or off: how often the water's own hand drew the body under the face, and the mean
    # colour [r, g, b] of what it drew (its px that are not empty) beside that of the same px of the person's sheet
    seen = """async (on) => { setOpt('clearwater', on); await new Promise((ok) => setTimeout(ok, 900)); const u0 = WaterBed.under, out = {n: 0, drawn: null, sheet: null};
      const mean = (c) => { const d = c.getContext('2d', {willReadFrequently: true}).getImageData(0, 0, 48, 12).data, s = [0, 0, 0]; let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 200) { n++; for (let j = 0; j < 3; j++) s[j] += d[i + j]; } return s.map((v) => v / Math.max(1, n)); };
      WaterBed.under = (sheet, a, b, w, h, ...rest) => { out.n++; const di = ctx.drawImage;
        ctx.drawImage = function (src, ...r) { if (src instanceof HTMLCanvasElement && src.width === 48) out.drawn = mean(src); return di.call(this, src, ...r); };
        try { u0(sheet, a, b, w, h, ...rest); } finally { ctx.drawImage = di; }
        const c = document.createElement('canvas'); c.width = 48; c.height = 12; c.getContext('2d').drawImage(sheet, a, b, w, h, 0, 0, w, h); out.sheet = mean(c); };
      await new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(ok)))); WaterBed.under = u0; return out; }"""
    on = game.js(seen, True)
    assert on["n"] >= 2 and on["drawn"] and on["sheet"], on                      # on: the body under the face is drawn by the water's own hand
    tint = {1: (104, 204, 208), 2: (70, 174, 204)}[game.js(f"WaterBed.depth({x}, {y - 1})")]      # (waterbed.js: the tint of water one and two levels deep)
    far = lambda c: sum(abs(a - b) for a, b in zip(c, tint))
    assert far(on["drawn"]) < far(on["sheet"]) - 30, on                          # ...tinted: nearer the water's colour than the sheet's own px are
    assert game.js(seen, False)["n"] == 0                                        # off: not at all (the body dimly seen, as it was)
    game.js(RESET)


def test_water_one_level_deep_is_clearly_bluer_than_dry_ground_at_noon_and_at_low_sun(game):
    """A pond one level deep is water at every hour: never a pit of pale sand ("cream water reads as sand")."""
    game.flat(); game.clear_area(10); game.js(RESET); game.js("(() => { setOpt('shimmer', false); setOpt('shader', 'off'); return 1; })()")
    game.stamp(-8, -6, ["~" * 4] * 2); game.stamp(-3, -6, ["," * 3] * 3)         # a pond (all of it by its banks: one deep), bare earth beside it
    x, y = game.pos(); game.wait(READY, 20000); game.rest()
    assert game.js(f"WaterBed.depth({x - 7}, {y - 5})") == 1
    for phase in (.375, .65):
        game.hour(phase)
        w, d = game.js(MOST, [x - 7.5, y - 5, x - 5.5, y - 4.15]), game.js(MOST, [x - 2.5, y - 5.5, x - .5, y - 4.5])
        assert (w[2] - w[0]) - (d[2] - d[0]) >= 50 and w[2] >= w[0] - 5 and w[1] > w[0] + 15, (phase, w, d)      # blue over red: far more than the earth's; and no cream
    game.rpc("dev_time", phase=.3); game.js(RESET)


def test_a_bed_step_under_water_is_one_colour_no_checker(game):
    """The front of a step of the bed, seen through the water: a band of one colour, its first row a touch darker (a shelf's line, not a box's edge). No dither."""
    plain(game)
    game.stamp(-9, -7, ["~" * 6] * 6); x, y = game.pos(); game.wait(READY, 20000); game.rest()
    tx, ty = x - 7, y - 6                                                         # two deep (no land beside it), the tile north of it one deep: the step's front is rows 8 to 15 of its face
    assert game.js(f"[WaterBed.depth({tx}, {ty}), WaterBed.depth({tx}, {ty - 1})]") == [2, 1]
    grab = """([tx, ty, r0, n]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
      const S = TS(), [ox, oy] = screenOrigin(S), k = S / 16, out = [];
      for (let j = 0; j < n; j++) { const row = []; for (let i = 0; i < 16; i++) { const d = ctx.getImageData(Math.round((ox + tx * S + (i + .5) * k) * DPR), Math.round((oy + ty * S + (r0 + j + .5) * k) * DPR), 1, 1).data; row.push(d[0] + ',' + d[1] + ',' + d[2]); } out.push(row); }
      ok(out); })))"""
    for col in (tx, tx + 1, tx + 2):
        rows = game.js(grab, [col, ty, 8, 8])
        assert all(len(set(r)) == 1 for r in rows), rows                          # every row of the front: one colour from side to side
        v = [sum(map(int, r[0].split(","))) for r in rows]                        # (a row may differ from the next by a unit: the water is less seen through the further north it is)
        assert max(v[1:]) - min(v[1:]) <= 3 and 4 <= v[1] - v[0] <= 30, rows      # seven rows of one colour under one a little darker
    game.js(RESET)


BRIGHT = """async ([b64, x0, y0, x1, y1]) => { const im = await createImageBitmap(await (await fetch('data:image/png;base64,' + b64)).blob()), c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
  const g = c.getContext('2d'); g.drawImage(im, 0, 0); const S = TS(), [ox, oy] = screenOrigin(S), k = im.width / innerWidth, X = Math.round((ox + x0 * S) * k), Y = Math.round((oy + y0 * S) * k), w = Math.round((x1 - x0) * S * k), h = Math.round((y1 - y0) * S * k);
  const d = g.getImageData(X, Y, w, h).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.min(d[i], d[i + 1], d[i + 2]) > 228) n++; return n / (w * h); }"""


def test_the_shaders_glitter_is_a_few_dashes_not_snow_on_the_water(game):
    """Natural: the sun's glitter on water is rare dashes in the band under the sun; it was white specks all over, like snow."""
    import base64
    game.flat(); game.clear_area(12); game.js(RESET); game.rpc("dev_time", phase=.375)
    game.stamp(-10, -8, ["~" * 21] * 6); x, y = game.pos(); game.wait(READY, 20000); game.rest()
    game.js("(() => { setOpt('shader', 'natural'); return 1; })()"); game.rest()
    worst = 0
    for _ in range(4):
        shot = base64.b64encode(game.page.screenshot()).decode()
        worst = max(worst, game.js(BRIGHT, [shot, x - 9.5, y - 7.5, x + 10.5, y - 2.5])); game.sleep(350)
    game.js("(() => { setOpt('shader', 'off'); return 1; })()")
    assert worst < .005, worst                                                   # white px on the water (the surface's own glints with them): under 0.5 % (it is 0.3; it was 0.8 to 1)


def test_water_up_on_a_plateau_has_a_bank_and_water_beside_a_dug_bank_has_a_side(game):
    """A pond flush with a plateau's top ("a hard rectangle pasted on grass, no shore"): the land round it has its rim
    along the water, as along any drop (voxpaint.js shape), the water going on under it. And a pond whose south bank
    was dug away: the water has a side over the pit, its own colour (it ended in a straight edge over its bed's sand)."""
    game.flat()
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(2, -3, ["." * 5] * 4, levels=["2" * 5] * 4); game.stamp(3, -2, ["~~~"] * 2, levels=["222"] * 2)
    game.stamp(-6, -3, ["~~~", "~~~"]); game.stamp(-6, -1, ["..."], levels=["b" * 3])
    game.rest()
    assert game.js(f"[VoxPaint.shape({x} + 2, {y} - 2, 2), VoxPaint.shape({x} + 4, {y} - 3, 2), VoxPaint.shape({x} + 4, {y}, 2)].every((s) => s > 0)")
    assert game.js(f"topAt({x} + 3, {y} - 2)") == 2
    # the water's side: under the pond's south edge, over the pit: blue-green, not sand
    from test_e2e_digging import LAND
    r, g, b = game.js(LAND, [[x - 5, y - 1, 0, 8, 3]])[0]
    assert b > r + 20 and g > r + 20, (r, g, b)


def test_a_pillar_and_an_islet_standing_in_a_pond_do_not_change_the_bed_round_them(game):
    """The bed is deeper by the distance to the water's banks, not to what stands in it: a step down round every pillar
    and islet, each with its lip and its shadow, was a quilt of squares. A tile beside the pillar is as deep, and the
    same colour, as one three tiles from it at the same distance from the bank."""
    plain(game)
    game.stamp(-10, -9, ["~" * 12] * 8); x, y = game.pos(); game.wait(READY, 20000); game.rest()
    X, Y = x - 10, y - 9                                                          # the pond's corner
    before = game.js("([X, Y]) => { const o = []; for (let j = 0; j < 8; j++) for (let i = 0; i < 12; i++) o.push(WaterBed.depth(X + i, Y + j)); return o; }", [X, Y])
    assert before == [1 if i in (0, 11) or j in (0, 7) else 2 for j in range(8) for i in range(12)]      # a rim one deep, then one basin
    game.stamp(-6, -6, ["-"], levels=["3"]); game.stamp(-2, -6, ["..", ".."])      # a stone pillar, an islet of four tiles
    game.wait(READY, 20000); game.rest()
    after = game.js("([X, Y]) => { const o = []; for (let j = 0; j < 8; j++) for (let i = 0; i < 12; i++) o.push(WaterBed.depth(X + i, Y + j)); return o; }", [X, Y])
    land = {(4, 3), (8, 3), (9, 3), (8, 4), (9, 4)}
    assert all(a == (0 if (i % 12, i // 12) in land else b) for i, (a, b) in enumerate(zip(after, before))), after
    row = Y + 5                                                                   # a row of the basin south of them: its tiles show their own bed in their south half
    cols = [c for c in range(X + 2, X + 10) if game.js(f"hash({c}, {row}, 41) >= .09")]      # (nothing floating on them)
    seen = {c: tuple(game.js(MOST, [c + .2, row + .55, c + .8, row + .95])) for c in cols}
    assert len(cols) >= 4 and len(set(seen.values())) == 1, seen                  # under the pillar's column and three tiles from it: one colour
    game.stamp(-10, -9, ["." * 12] * 8, levels=["0" * 12] * 8); game.js(RESET)


def test_under_a_shader_the_sky_in_the_water_ends_at_an_islets_own_edge(game):
    """Natural: the sky's tint lies on the px where the water's face is seen and on no other. It was laid through a
    picture of the water a rectangle a tile: a square of water with no sky in it round each islet. Along the four
    lines through an islet's middle: the last px of water before its edge has the tint, the first px of the islet has none,
    and its edge is inside its tile's square."""
    game.flat(); game.clear_area(10); game.js(RESET); game.rpc("dev_time", phase=.375)
    x, y = game.pos()
    # (the islet: where no leaf floats on the four tiles of water beside it. One floats on a water tile in eleven, by the
    # tile's own place (water.js: hash 41), and the islet was always five tiles north-west of wherever you woke: with a
    # leaf on a line read, "the first px that is not water" was the leaf, not the islet: one run in three, on any machine)
    ix, iy = next(((i, j) for j in (-5, -4, -6) for i in (-5, -4, -6, -3, -7) if game.js(f"[[1, 0], [-1, 0], [0, 1], [0, -1]].every(([a, b]) => hash({x + i} + a, {y + j} + b, 41) >= .09)")), (-5, -5))
    game.stamp(-9, -8, ["~" * 9] * 7); game.stamp(ix, iy, ["."]); game.wait(READY, 20000); game.rest()
    game.js("(() => { setOpt('shimmer', false); setOpt('clouds', 0); setOpt('glow', 0); setOpt('reflect', 0); setOpt('shader', 'natural'); return 1; })()"); game.wait("!!Sun.water", 8000); game.sleep(1500)
    scan = """([tx, ty, dx, dy]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
      const S = TS(), [ox, oy] = screenOrigin(S), k = S / 16, c = document.createElement('canvas'); c.width = cv.width; c.height = cv.height; const g = c.getContext('2d', {willReadFrequently: true}); g.drawImage(Shader.el, 0, 0);
      const out = [];
      for (let n = -12; n < 9; n++) {                                           // art px along the line, from 12 px outside the tile to its middle
        const i = dx > 0 ? n : dx < 0 ? 15 - n : 8, j = dy > 0 ? n : dy < 0 ? 15 - n : 8, X = Math.round((ox + tx * S + (i + .5) * k) * DPR), Y = Math.round((oy + ty * S + (j + .5) * k) * DPR);
        const a = ctx.getImageData(X, Y, 1, 1).data, b = g.getImageData(X, Y, 1, 1).data;
        out.push([n, a[0], a[1], a[2], Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2])]);
      }
      ok(out); })))"""
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        line = game.js(scan, [x + ix, y + iy, dx, dy])
        wet = lambda p: p[3] > p[1] + 12 and p[2] > p[1]                          # (the land's own picture there: water is blue over red; the islet's foam, earth and grass are not)
        edge = next(i for i, p in enumerate(line) if not wet(p))
        assert edge >= 2 and line[edge][0] >= 1, (dx, dy, line)                   # the islet's edge: inside its tile's square, water before it
        assert line[edge - 1][4] >= 8 and line[edge - 2][4] >= 8, (dx, dy, line)  # the water up to it: the sky in it
        assert all(p[4] <= 3 for p in line[edge:edge + 3]), (dx, dy, line)        # the islet from its first px: none
    game.js("(() => { setOpt('shader', 'off'); setOpt('clouds', 100); setOpt('glow', 100); setOpt('reflect', 100); return 1; })()"); game.js(RESET)
    game.stamp(-9, -8, ["." * 9] * 7)
