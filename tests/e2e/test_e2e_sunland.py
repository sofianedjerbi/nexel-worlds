"""The sun on the land as blocks (vox_light.js, sun.js), with a shader on: the land throws its shadow on the land,
away from the sun; the shadow of what stands falls on the land it is thrown on and never on a wall; what stands in
the land's shadow is in it; the land north of water is seen in it. With no shader the land is as it is painted."""

# the mean light of a part of the world's flat ground [x0, y0, x1, y1] (tiles) on the game's own canvas, read in the frame it was drawn in
LIT = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
  const S = TS(), [ox, oy] = screenOrigin(S), a = Math.round((ox + x0 * S) * DPR), b = Math.round((oy + y0 * S) * DPR);
  const d = cv.getContext("2d").getImageData(a, b, Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)).data;
  let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] + d[i + 1] + d[i + 2];
  ok(sum / d.length * 4 / 3); })))"""
PX = LIT.replace("let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] + d[i + 1] + d[i + 2];\n  ok(sum / d.length * 4 / 3);", "ok(Array.from(d));")
RESET = "for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()"


def look(game, name, wait=800):
    game.js(f"setOpt('clouds', 0); setOpt('shader', '{name}')")      # (no clouds unless a test is about them: they drift over the land's own picture)
    game.sleep(wait)


def test_a_cliff_throws_its_shadow_on_the_ground_away_from_the_sun(game):
    game.js("setOpt('depth', false)")                         # (the land as it is painted, to tell a shader's sun from: the land's depth, on by default, has its own tests)
    game.flat()                                                  # (it measures parts of the picture north of you by the flat picture's px, and two frames px for px: the curved world's sky moves)
    game.clear_area(8)
    game.stamp(-1, -3, ["..", ".."], levels=["33", "33"])      # a block of land three high, north of you
    x, y = game.pos()
    west, east = [x - 2.8, y - 2.9, x - 1.3, y - 2.1], [x + 1.3, y - 2.9, x + 2.8, y - 2.1]      # the ground beside it
    game.rpc("dev_time", phase=.06)                             # morning: the sun in the east
    game.sleep(1200)
    plain = [game.js(LIT, r) for r in (west, east)]
    look(game, "natural")
    on = [game.js(LIT, r) for r in (west, east)]
    assert on[0] < plain[0] - 8 and abs(on[1] - plain[1]) < 1.5, (plain, on)      # in shadow west of it, in the sun east of it
    game.js("setOpt('landshade', false)"); game.sleep(600)   # the settings' Land shadows, off: none
    assert abs(game.js(LIT, west) - plain[0]) < 1.5
    game.js("setOpt('landshade', true)")
    look(game, "off", 300)
    game.rpc("dev_time", phase=.7)                              # evening: the other side
    game.sleep(1200)
    plain = [game.js(LIT, r) for r in (west, east)]
    look(game, "natural")
    on = [game.js(LIT, r) for r in (west, east)]
    assert on[1] < plain[1] - 8 and abs(on[0] - plain[0]) < 1.5, (plain, on)
    game.js(RESET)


def test_the_shadow_of_what_stands_is_not_on_a_wall_and_what_stands_in_shadow_is_in_it(game):
    game.js("setOpt('depth', false)")                         # (the land as it is painted, to tell a shader's sun from: the land's depth, on by default, has its own tests)
    game.clear_area(8)
    x, y = game.pos()
    tx, ty = x + 3, y - 2
    game.stamp(3, -2, ["T"])                                     # a tree; south-west of it a wall two high: its front is
    game.stamp(1, -1, [".."], levels=["22"])                     # where the tree's shadow would lie, laid flat on the picture
    game.stamp(-5, -2, ["T"])                                    # and a tree on open ground
    game.stamp(-8, 3, ["l"], levels=["1"])                       # (and south of it, on another level, a thing that throws no shadow: the others keep theirs)
    front = [tx - 1.9, ty + 1.2, tx - .1, ty + 1.75]             # (not its last px: the ground shows at a front's foot, and takes the shadow)
    open_ = [tx - 8 - 2, ty + .6, tx - 8, ty + 1.7]
    game.rpc("dev_time", phase=.06)
    game.sleep(1200)
    plain = [game.js(LIT, r) for r in (front, open_)]
    look(game, "natural")
    on = [game.js(LIT, r) for r in (front, open_)]
    assert on[1] < plain[1] - 3, (plain, on)                    # the tree on open ground: its shadow on the ground west of it
    assert abs(on[0] - plain[0]) < 1.5, (plain, on)             # the wall's front: no shadow on it
    # a tree in the shadow of a cliff is as dark as the ground it stands on: lit, it was a bright thing in the shade
    game.stamp(-2, 2, [".."] * 4, levels=["44"] * 4); game.stamp(-3, 4, ["T"])
    tree = [x - 2.85, y + 3.3, x - 2.15, y + 4.2]                # (its crown: nothing of the ground in it)
    game.js("setOpt('landshade', false)"); game.sleep(700)
    lit = game.js(LIT, tree)
    game.js("setOpt('landshade', true)")
    for _ in range(12):                                         # (the cliff's faces are made a little a frame: read till it is there)
        game.sleep(300)
        dark = game.js(LIT, tree)
        if dark < lit - 8:
            break
    assert dark < lit - 8, (lit, dark)
    game.js(RESET)


def test_with_no_shader_and_with_no_sun_asked_for_the_land_is_as_it_is_painted(game):
    game.js("setOpt('depth', false)")                         # (the land as it is painted, to tell a shader's sun from: the land's depth, on by default, has its own tests)
    game.flat()                                                  # (it measures parts of the picture north of you by the flat picture's px, and two frames px for px: the curved world's sky moves)
    game.clear_area(8)
    game.stamp(-4, -4, ["...", "..."], levels=["231", "220"])  # land with fronts, banks and feet, and no one on it
    x, y = game.pos()
    part = [x - 5, y - 5.5, x - .5, y - 1.5]
    game.js("setOpt('shimmer', false)")
    game.rpc("dev_time", phase=.3)                              # (plain day: the hour lays no colour of its own over the picture)
    game.sleep(1200)
    off = game.js(PX, part)
    assert off == game.js(PX, part)                              # (it is still: two frames are the same)
    game.js("setOpt('clouds', 0); setOpt('shader', 'natural'); setOpt('shaderk', 0)"); game.sleep(700)
    assert game.js(PX, part) == off                              # strength 0: nothing of the sun
    game.js("setOpt('shaderk', 100); setOpt('shadows', 0); setOpt('reflect', 0)"); game.sleep(700)
    assert game.js(PX, part) == off                              # no shadows asked for: every px as it was
    game.js("setOpt('shadows', 100)"); game.sleep(700)
    assert game.js(PX, part) != off                              # ...and with them, it is not
    game.js(RESET)


def test_the_land_north_of_water_is_seen_in_it(game):
    game.flat()                                                  # (it measures parts of the picture north of you by the flat picture's px, and two frames px for px: the curved world's sky moves)
    game.clear_area(8)
    game.stamp(-4, -5, ["........", "~~~~~~~~", "~~~~~~~~", "~~~~~~~~"], levels=["33333333"] + ["0" * 8] * 3)      # a cliff, a pond at its foot
    x, y = game.pos()
    near, far = [x - 3, y - 3.95, x + 3, y - 3.1], [x - 3, y - 2.4, x + 3, y - 2.1]      # the water at the cliff's foot; further out than the cliff is high
    game.js("setOpt('shimmer', false); setOpt('shadows', 0)")
    game.rpc("dev_time", phase=.3)
    look(game, "natural", 1200)
    seen = [game.js(LIT, r) for r in (near, far)]
    game.js("setOpt('reflect', 0)"); game.sleep(700)
    bare = [game.js(LIT, r) for r in (near, far)]
    assert abs(seen[0] - bare[0]) > 1 and abs(seen[1] - bare[1]) < .5, (seen, bare)      # (water seen through, waterbed.js: near you the mirror is faint, the bed is what shows)
    game.js(RESET)


def test_the_sun_on_the_land_costs_little_of_a_frame(game):
    game.clear_area(8)
    game.stamp(-6, -5, ["......", "......", "~~~~~~"], levels=["332211", "332211", "000000"]); game.stamp(2, -3, ["T.T", "...", "T.T"])
    game.rpc("dev_time", phase=.08)
    look(game, "natural", 1000)
    ms = game.js("new Promise((ok) => { const out = [], of = window.frame; window.frame = (now) => { const a = performance.now(); of(now); out.push(performance.now() - a); if (out.length >= 90) { window.frame = of; ok(out); } }; })")
    ms.sort()
    assert ms[len(ms) // 2] < 7 and ms[int(len(ms) * .95)] < 14, ms[-5:]
    game.js(RESET)


# ---- the curved world (curve.js): the shadows are laid on the flat picture and bent with the land ----
# the mean light of a part of the SCREEN [x0, y0, x1, y1] (px) on the game's own canvas
BOX = LIT.replace("const S = TS(), [ox, oy] = screenOrigin(S), a = Math.round((ox + x0 * S) * DPR), b = Math.round((oy + y0 * S) * DPR);", "const a = Math.round(x0 * DPR), b = Math.round(y0 * DPR);") \
    .replace("Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)", "Math.max(1, Math.round((x1 - x0) * DPR)), Math.max(1, Math.round((y1 - y0) * DPR))")
BOXPX = BOX.replace("let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] + d[i + 1] + d[i + 2];\n  ok(sum / d.length * 4 / 3);", "ok(Array.from(d));")


def tile_box(game, x, y, top=.1, foot=.9):
    """Where the curve draws the ground of tile (x, y): the part of it between two shares of its height."""
    from test_e2e_curve import PROJ
    cx, _, t, f = game.js(PROJ, [x, y])
    half = game.js("TS()") * .4
    return [cx - half, t + (f - t) * top, cx + half, t + (f - t) * foot]


def far(game):
    from test_e2e_curve import curved
    curved(game, "far")


def test_in_the_bend_a_cliff_shadows_the_ground_where_the_curve_draws_it(game):
    game.js("setOpt('depth', false)")                         # (the land as it is painted, to tell a shader's sun from: the land's depth, on by default, has its own tests)
    game.clear_area(10)
    game.stamp(-1, -7, ["..", "..", ".."], levels=["33", "33", "33"])      # a block of land three high, in the bent part of the screen
    x, y = game.pos()
    far(game)
    assert game.js("([y]) => { const S = TS(), [, oy] = screenOrigin(S); return Curve.y(oy + y * S, 0) > oy + y * S + 4; }", [y - 5])      # (that row is bent: drawn lower than flat)
    west, east = tile_box(game, x - 2, y - 5), tile_box(game, x + 1, y - 5)
    game.rpc("dev_time", phase=.06)                             # morning: its shadow lies west of it
    game.sleep(1200)
    plain = [game.js(BOX, r) for r in (west, east)]
    look(game, "natural")
    on = [game.js(BOX, r) for r in (west, east)]
    assert on[0] < plain[0] - 8 and abs(on[1] - plain[1]) < 1.5, (plain, on)
    look(game, "off", 300)
    game.rpc("dev_time", phase=.7)                              # evening: east of it
    game.sleep(1200)
    plain = [game.js(BOX, r) for r in (west, east)]
    look(game, "natural")
    on = [game.js(BOX, r) for r in (west, east)]
    assert on[1] < plain[1] - 8 and abs(on[0] - plain[0]) < 1.5, (plain, on)
    game.js(RESET)


def test_in_the_bend_a_trees_shadow_lies_at_its_foot(game):
    game.js("setOpt('depth', false)")                         # (the land as it is painted, to tell a shader's sun from: the land's depth, on by default, has its own tests)
    game.clear_area(10)
    game.stamp(3, -5, ["T"])
    x, y = game.pos()
    far(game)
    game.rpc("dev_time", phase=.06)
    game.sleep(1200)
    foot, north = tile_box(game, x + 2, y - 5, .7, 1.7), tile_box(game, x + 5, y - 5)       # west of its foot (its shadow goes on south a little: more of a row, now that a row there is a third taller; the shadow lies on whole px of the paint); and east of it, the sun's side
    plain = [game.js(BOX, r) for r in (foot, north)]
    look(game, "natural")
    on = [game.js(BOX, r) for r in (foot, north)]
    assert on[0] < plain[0] - 3 and abs(on[1] - plain[1]) < 1.5, (plain, on)
    game.js(RESET)


def test_in_the_bend_with_no_sun_asked_for_the_land_is_as_it_is_drawn(game):
    game.js("setOpt('depth', false)")                         # (the land as it is painted, to tell a shader's sun from: the land's depth, on by default, has its own tests)
    game.clear_area(10)
    game.stamp(-4, -7, ["...", "..."], levels=["231", "220"])
    x, y = game.pos()
    far(game)
    game.js("setOpt('shimmer', false)")
    game.rpc("dev_time", phase=.3)
    game.sleep(1200)
    a, b = tile_box(game, x - 5, y - 5, 0, 0), tile_box(game, x, y - 3, 1, 1)
    part = [a[0], a[1], b[2], b[3]]                               # the land from the block's foot to near you: bent, no sky in it (its far side is past the horizon, where a row's place comes down again: the box began under the block's shadow)
    off = game.js(BOXPX, part)
    assert off == game.js(BOXPX, part)
    game.js("setOpt('clouds', 0); setOpt('shader', 'natural'); setOpt('shaderk', 0)"); game.sleep(700)
    assert game.js(BOXPX, part) == off
    game.js("setOpt('shaderk', 100); setOpt('shadows', 0); setOpt('reflect', 0)"); game.sleep(700)
    assert game.js(BOXPX, part) == off
    game.js("setOpt('shadows', 100)"); game.sleep(700)
    assert game.js(BOXPX, part) != off
    game.js(RESET)


# ---- one frame drawn twice: with the game as it is, and with a setting changed (a fire flickers, a cloud drifts, a
# body sways: two frames a moment apart differ by as much as a faint shadow does; the same frame drawn twice does not) ----
# -> for each part [x0, y0, x1, y1] (tiles of flat ground): [its mean light as it is, with the setting changed, as it is again]
TWICE = """([boxes, name, value]) => new Promise((ok) => requestAnimationFrame((T) => {
  const raf = window.requestAnimationFrame, was = opt(name), out = boxes.map(() => []); window.requestAnimationFrame = () => 0;
  const S = TS(), [ox, oy] = screenOrigin(S);
  const lit = () => boxes.forEach(([x0, y0, x1, y1], n) => { const d = ctx.getImageData(Math.round((ox + x0 * S) * DPR), Math.round((oy + y0 * S) * DPR), Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)).data;
    let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] + d[i + 1] + d[i + 2]; out[n].push(sum / d.length * 4 / 3); });
  try { frame(T); lit(); setOpt(name, value); frame(T); lit(); setOpt(name, was); frame(T); lit(); } finally { setOpt(name, was); window.requestAnimationFrame = raf; raf(frame); }
  ok(out); }))"""


def twice(game, boxes, name, value):
    out = game.js(TWICE, [boxes, name, value])
    assert all(abs(a - c) < 1e-9 for a, _, c in out), out          # (the same frame drawn again is the same picture)
    return [(a, b) for a, b, _ in out]


def test_what_is_built_in_a_cliffs_shadow_is_dark_on_the_shaded_side_only(game):
    """A house half in a cliff's shadow was dark a piece at a time (a tile of wall all dark, the next all lit). Each
    px across it is in the shadow as high as the shadow stands there: by the cliff all of the wall, further on its
    foot only, past the shadow's end none of it."""
    game.clear_area(10)
    game.stamp(-5, 2, ["WWWWWW"])                               # a wall east-west, south of you (where the picture is flat)
    game.stamp(1, 0, ["..", "..", "..", ".."], levels=["44"] * 4)      # a cliff at its east end
    x, y = game.pos()
    game.rpc("dev_time", phase=.08)                             # morning: the cliff's shadow lies west, along the wall
    look(game, "natural", 1000)
    front = lambda tx, a, b: [tx + a, y + 2 + .1, tx + b, y + 2 + .7]
    near, mid, far_ = twice(game, [front(x, .1, .9), front(x - 1, .1, .9), front(x - 4, .1, .9)], "shadows", 0)
    assert near[0] < near[1] - 8, near                          # by the cliff: dark
    assert abs(far_[0] - far_[1]) < .01, far_                   # past the shadow's end: as it is painted
    # the tile the shadow's line crosses: its east half darker than its west half, by the shadow alone
    for tx in (x - 1, x - 2):
        west, east = twice(game, [front(tx, .05, .45), front(tx, .55, .95)], "shadows", 0)
        assert west[1] - west[0] <= east[1] - east[0] + .01, (tx, west, east)      # never darker further from the cliff
    game.js(RESET)


def test_a_fires_shadow_lies_away_from_the_fire_on_the_level_of_what_throws_it(game):
    game.clear_area(8)
    game.stamp(-6, -1, ["........", "........", "........"], levels=["00111000", "00111000", "00111000"])      # a low terrace,
    game.stamp(-3, 0, ["T"], levels=["1"]); game.stamp(0, 1, ["^"])                                                  # a tree on it, a fire east of it (south of you)
    x, y = game.pos()
    tx, ty = x - 3, y
    game.js("setOpt('shimmer', false); setOpt('corners', 0)")
    game.rpc("dev_time", phase=.87)
    look(game, "natural", 1500)
    up = game.js("RELIEF_STEP / P")                              # (the terrace is drawn that much of a tile up)
    west, east, low = twice(game, [[tx - 1, ty + .3 - up, tx + .1, ty + 1.2 - up], [tx + .9, ty + .3 - up, tx + 1.9, ty + 1.2 - up], [tx - 3, ty + .2, tx - 1.3, ty + 1.3]], "shadows", 0)
    assert west[0] < west[1] - .3, west                         # west of the tree, away from the fire: its shadow
    assert abs(east[0] - east[1]) < .01, east                   # between it and the fire: none
    assert abs(low[0] - low[1]) < .01, low                      # and it does not go on over the lower ground past the terrace's edge
    game.js(RESET)


def test_a_clouds_shadow_lies_on_the_land_and_what_stands_and_not_under_a_roof(game):
    """The clouds' shadows are the land's own (vox_light.js) and what stands is as dark as its ground (sunland.js);
    under a roof there is none."""
    game.rpc("dev_time", phase=.3)
    look(game, "natural", 800)
    game.js("setOpt('clouds', 100); setOpt('shadows', 0); setOpt('shimmer', false)"); game.sleep(500)
    # where a cloud's shadow is deep now, near you (the field drifts a tile in five seconds)
    spot = game.js("""() => { const c = Sun.given().cloud, p = myPos(); let best = null;
      for (let dy = -14; dy <= 14; dy++) for (let dx = -14; dx <= 14; dx++) { const k = Math.min(...[0, 1, 2, 3].map((i) => VoxLight.cloud({k: c.k, drift: [c.drift[0] - i * .11, c.drift[1] + i * .04]}, p.x + dx, p.y + dy, P)));
        if (!best || k > best[2]) best = [p.x + dx, p.y + dy, k]; }
      return best; }""")
    assert spot[2] > .3, spot                                    # (dark there now and for the next thirty seconds)
    cx, cy = spot[0], spot[1]
    game.rpc("dev_teleport", x=cx, y=cy + 2, z=0); game.wait(f"myAt && myAt.x === {cx} && myAt.y === {cy + 2}", 8000)
    game.clear_area(6)
    game.stamp(0, -2, ["T"])                                    # a tree at the spot
    game.wait("dirtyTiles.length === 0", 20000); game.sleep(600)
    ground, tree = twice(game, [[cx - 2, cy + .2, cx - 1, cy + 1], [cx + .2, cy - .6, cx + .8, cy + .2]], "clouds", 0)
    assert ground[0] < ground[1] - 4, ground                     # the land is darker under the cloud
    assert tree[0] < tree[1] - .5, tree                           # and so is the tree that stands there
    game.stamp(-3, -4, ["." * 7] * 5, levels=["4" * 7] * 5)     # a hill over the spot, a cave in it, its mouth south
    game.stamp(-2, -3, ["." * 5] * 3, levels=["0" * 5] * 3, roofs=["4" * 5] * 3, heads=["2" * 5] * 3)
    game.stamp(0, -1, ["."], levels=["0"], roofs=["4"], heads=["2"])
    game.rpc("dev_teleport", x=cx, y=cy, z=0); game.wait(f"myAt && myAt.x === {cx} && myAt.y === {cy}", 8000)
    game.wait("dirtyTiles.length === 0", 20000); game.wait("coveredAt(myAt.x, myAt.y, myAt.z)"); game.sleep(900)
    inside, = twice(game, [[cx - 6, cy - 5, cx + 6, cy + 4]], "clouds", 0)
    assert abs(inside[0] - inside[1]) < 1e-9, inside             # under the roof: no cloud's shadow on anything
    game.js(RESET)
