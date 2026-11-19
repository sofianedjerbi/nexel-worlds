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
    game.stamp(-8, -6, ["~" * 5] * 4); game.stamp(2, -6, [")" * 5] * 4)          # a pond one level deep at its banks; a piece of the deep
    x, y = game.pos(); game.wait(READY, 20000); game.sleep(600)
    # a pond's tile by its west bank with nothing floating on it: its own bed shows in its south half (a bed one deep is drawn a level down the picture)
    row = next(j for j in range(1, 4) if game.js(f"hash({x - 8}, {y - 6 + j}, 41) >= .09"))
    tx, ty = x - 8, y - 6 + row
    assert game.js(f"WaterBed.depth({tx}, {ty})") == 1 and game.js(f"topAt({tx}, {ty})") == 0      # (the bed is for the eye: the tile is at its level, as ever)
    got = game.js(MOST, [tx + .3, ty + .6, tx + .8, ty + .95])
    sand, tint, a = (236, 220, 174), (136, 224, 214), .26                        # water.js: the sand a level down, the tint over it and how much of it
    want = [s * (1 - a) + t * a for s, t in zip(sand, tint)]
    assert all(abs(g - w) <= 4 for g, w in zip(got, want)), (got, want)
    deep = game.js(MOST, [x + 4, y - 4.5, x + 5, y - 3.5])
    assert all(abs(g - w) <= 3 for g, w in zip(deep, (72, 115, 150))), deep      # the deep: water.js's own deep colour, all of it
    game.js("(() => { setOpt('clearwater', false); return 1; })()"); game.wait(READY, 20000); game.sleep(600)
    assert game.js(MOST, [tx + .3, ty + .6, tx + .8, ty + .95]) != got           # (off: another picture there)
    game.js(RESET)


def test_off_the_water_is_one_painted_face_and_on_again_off_again_it_is_the_same_picture(game):
    plain(game)
    game.stamp(-8, -6, ["~" * 6] * 4); game.stamp(-2, -6, ["..."] * 2, levels=["333"] * 2); game.wait(READY, 20000)
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
    game.stamp(-9, -7, ["~" * 14] * 6); game.stamp(-9, -1, ["....~~~~......"]); game.wait(READY, 20000)
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
    game.rpc("dev_teleport", x=x, y=y - 1, z=0); game.wait(f"myAt && myAt.y === {y - 1}", 8000); game.wait(READY, 20000); game.sleep(800)
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
    tint = {1: (136, 224, 214), 2: (78, 188, 208)}[game.js(f"WaterBed.depth({x}, {y - 1})")]      # (water.js: the tint of water one and two levels deep)
    far = lambda c: sum(abs(a - b) for a, b in zip(c, tint))
    assert far(on["drawn"]) < far(on["sheet"]) - 30, on                          # ...tinted: nearer the water's colour than the sheet's own px are
    assert game.js(seen, False)["n"] == 0                                        # off: not at all (the body dimly seen, as it was)
    game.js(RESET)
