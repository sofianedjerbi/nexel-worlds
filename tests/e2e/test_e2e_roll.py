"""The roll's land is whole px of its paint, and a long way at once never shows a blank frame (web/js/vox_curve.js,
curve.js, render.js): the reviewer's "things 6-9 tiles north are squashed into the horizon band" and "one blank
frame after a teleport"."""
from test_e2e_curve import curved

# ---- whole px of the paint in the roll ("things 6-9 tiles north are squashed into the horizon band... its pixel art
# squeezed to non-whole pixels"): a tile's row is a whole number of art px tall, and each of them is one whole row
# of the tile's own 16 (vox_curve.js: rows), the ones its height says: the same whatever the frame.

# the rows of paint of tiles (x, y - k), k < n, as they are on the screen: for each, how tall it is drawn (art px),
# and each art px row of it: its 16 px across (read at a px's middle), and is every px of the screen in them one colour
ROWS = """([x, y, n]) => { const S = TS(), z = zoom, [ox, oy] = screenOrigin(S), sy = Curve.sy(oy, S), out = [];
  const g = ctx.getImageData(0, 0, cv.width, cv.height), at = (px, py) => { const i = (Math.floor(py * DPR) * cv.width + Math.floor(px * DPR)) * 4; return (g.data[i] << 16) | (g.data[i + 1] << 8) | g.data[i + 2]; };
  for (let k = 0; k < n; k++) { const top = sy.row(y - k, 0), foot = sy.row(y - k + 1, 0), h = (foot - top) / z, rows = [];
    if (top < Curve.line + z || sy.far(y - k) || VoxCurve.past(Curve.c, oy + (y - k) * S, 0) > 0 || foot > H) { out.push(null); continue; }      // (not on the screen, or not all of it before the horizon)
    for (let i = 0; i < Math.round(h); i++) { const r = []; let whole = true;
      for (let a = 0; a < 16; a++) { const px = ox + x * S + a * z, py = top + i * z, c = at(px + .5, py + .5); if (at(px + z - .5, py + z - .5) !== c || at(px + .5, py + z - .5) !== c || at(px + z - .5, py + .5) !== c) whole = false; r.push(c); }
      rows.push([r.join(), whole]); }
    out.push({h, rows}); }
  return out; }"""
SAME = """([x, y, n, flat]) => { const got = (%s)([x, y, n]), bad = []; let seen = 0, least = 16;
  got.forEach((t, k) => { if (!t || !flat[k]) return; seen++; least = Math.min(least, t.h);
    if (t.h !== Math.round(t.h) || t.h < 1 || t.h > 16) { bad.push([k, 'tall', t.h]); return; }
    t.rows.forEach((r, i) => { if (!r[1]) bad.push([k, i, 'not whole']); else if (r[0] !== flat[k].rows[VoxCurve.rows(i, t.h, 16)][0]) bad.push([k, i, 'another row']); }); });
  return {bad, seen, least}; }""" % ROWS


def flat_rows(game, x, y, n):
    """The 16 rows of paint of each of the n tiles north of (x, y), read off the flat picture from five tiles north (those that are on the screen there)."""
    game.js("(() => { Curve.force = 'off'; setOpt('shader', 'off'); return 1; })()")
    game.rpc("dev_teleport", x=x - 2, y=y - 5, z=99)
    game.wait(f"myPos().y === {y - 5} && !Curve.on && !arrivingNow && dirtyTiles.length === 0 && Math.abs(cam.y - myPos().y) < .01")
    game.sleep(400)
    flat = game.js(ROWS, [x, y, n])
    assert sum(1 for t in flat if t) >= 10 and all(t["h"] == 16 and all(r[1] for r in t["rows"]) for t in flat if t), "the flat picture is whole px"
    game.rpc("dev_teleport", x=x - 2, y=y, z=99)
    game.wait(f"myPos().y === {y}")
    return flat


def test_in_the_roll_a_tiles_row_is_a_whole_number_of_px_of_its_paint_and_each_is_one_of_its_sixteen_rows(game):
    """A meadow, Far: every tile of a column from you to the horizon is drawn a whole number of art px tall (16 down
    to 4: the floor), every px of the screen in an art px of it is one colour, and its i-th art px is the row of its
    own paint that vox_curve.js picks for that height (read off the flat picture): rows are left out, none is
    blended, none is shown twice."""
    game.clear_area(14)
    x, y = game.pos()
    flat = flat_rows(game, x + 2, y, 11)
    curved(game, "far")
    game.wait("Math.abs(cam.y - myPos().y) < .01 && !arrivingNow && dirtyTiles.length === 0")
    game.sleep(400)
    got = game.js(SAME, [x + 2, y, 11, flat])
    assert got["bad"] == [] and got["seen"] >= 6 and 3 <= got["least"] <= 8, got


def test_walking_north_twelve_frames_the_rows_shown_are_the_ones_each_tiles_height_says(game):
    """No shimmer: while you walk north, in each of twelve consecutive frames every tile of the column is whole px
    of its own paint, the rows its height picks: a row of paint is left out or comes back only when the tile's
    height changes by a px, never from one frame to the next at the same height."""
    game.clear_area(14)
    x, y = game.pos()
    flat = flat_rows(game, x + 2, y, 11)
    curved(game, "far")
    game.sleep(400)
    game.page.keyboard.down("w")
    game.sleep(250)
    got = game.js("""([x, y, n, flat]) => new Promise((ok) => { const out = [], of = window.frame, same = %s;
      window.frame = (now) => { of(now); const r = same([x, y, n, flat]); out.push([r.bad.slice(0, 4), r.seen, r.least, Math.round(cam.y * 100) / 100]); if (out.length >= 12) { window.frame = of; ok(out); } }; })""" % SAME, [x + 2, y, 11, flat])
    game.page.keyboard.up("w")
    assert all(f[0] == [] and f[1] >= 6 for f in got), got
    assert len({f[3] for f in got}) >= 6, got                    # (you did walk: the camera was somewhere else in most frames)


def test_after_a_teleport_the_screen_keeps_its_picture_until_the_land_there_has_come(game):
    """ "One blank frame after a teleport": sixty tiles at once, the land there not known yet: no frame of sky over
    bare ground colour, no dark one. Frame by frame: while the land where you are has not come, the picture is the
    one the screen had; never one colour over nine tenths of it."""
    game.clear_area(10)
    x, y = game.pos()
    curved(game, "far")
    game.js("""([x, y]) => { window.__tp = new Promise((ok) => { const out = [], of = window.frame; let first = null;
      const small = () => { const s = document.createElement('canvas'); s.width = 64; s.height = 36; const g = s.getContext('2d', {willReadFrequently: true}); g.imageSmoothingEnabled = false; g.drawImage(cv, 0, 0, 64, 36); return g.getImageData(0, 0, 64, 36).data; };
      window.frame = (now) => { of(now); const d = small(), m = new Map(); let top = 0, same = !!first;
        for (let i = 0; i < d.length; i += 4) { const k = d[i] << 16 | d[i + 1] << 8 | d[i + 2], v = (m.get(k) || 0) + 1; m.set(k, v); if (v > top) top = v; if (first && (first[i] !== d[i] || first[i + 1] !== d[i + 1] || first[i + 2] !== d[i + 2])) same = false; }
        if (Math.abs(cam.x - x) < 1) first = d;                       // (the picture the screen had, until you are gone)
        const b = blocks.get(bkey(Math.floor(cam.x / B), Math.floor(cam.y / B)));
        out.push([top / 2304, same, !!(b && Voxels.made(b)) && !arrivingNow, Math.round(cam.x)]);
        if (out.length >= 600 || (cam.x < x - 50 && out.filter((f) => f[3] < x - 50 && f[2]).length >= 5)) { window.frame = of; ok(out); } }; }); return 1; }""", [x, y])      # (until five frames of the land there)
    game.rpc("dev_teleport", x=x - 60, y=y, z=99)
    got = [f for f in game.js("window.__tp") if f[3] < x - 50]       # the frames from the teleport on
    assert all(share <= .9 for share, _, _, _ in got), got
    assert all(same or there or share < .7 for share, same, there, _ in got), got      # the land not there: the picture the screen had (or, after a long wait on a busy machine, the sky and the part of the land that has come)
    assert any(cx < x - 50 and there and not same for _, same, there, cx in got), got      # ...and then the land there
