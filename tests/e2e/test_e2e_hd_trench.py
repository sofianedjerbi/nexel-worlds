"""A stair and a passage one tile wide in the HD look, and what stands in the x-ray window (vox_style_glsl.js,
vox_style_land.js, vox_style.js, hd.js, hd_ease.js): a dug stair's treads are warm steps under the open sky as under the
land (they were grey squares: the sun's shade on bare earth), lighter at the top than at the bottom; over a passage one
tile wide the section is thin and the floor is a good part of the hole; what stands in a deep room is as dim as its
floor, you are not; the plants over your room go and come over a few frames, not in one; a paint that is not there is
never drawn as earth brown, and no px is drawn from one on ten walks down the stair and back; on grey stone the hole has
a darker lip."""

import pytest
from test_e2e_hd_stair import MOST, deep_room, spot, stair
from test_e2e_hd_sun import hd
from test_e2e_hd_window import PX, inside, room

# the mean colour of a tile's top as the screen has it (the px inside its four corners' box, two px in): [r, g, b]
TILE = """([x, y, z]) => { const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + a, y + b, z)), k = devicePixelRatio;
  const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 2 * zoom, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 2 * zoom, y0 = Math.ceil(c[0][1] * k) + 2 * zoom, y1 = Math.floor(c[2][1] * k) - 2 * zoom;
  const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data, s = [0, 0, 0]; for (let i = 0; i < d.length; i += 4) for (let j = 0; j < 3; j++) s[j] += d[i + j]; return s.map((v) => Math.round(v / (d.length / 4))); }"""
# the brightest px of what stands on a tile (a box a tile wide, a tile high, over its floor's middle): r + g + b
BRIGHT = """([x, y, z]) => { const a = HdLook.screenOf(x + .5, y + .6, z), k = devicePixelRatio, w = 14 * zoom * k, d = HdLook.read(Math.round(a[0] * k - w / 2), Math.round(a[1] * k - w), w, w).data; let m = 0;
  for (let i = 0; i < d.length; i += 4) m = Math.max(m, d[i] + d[i + 1] + d[i + 2]); return m; }"""
lum = lambda c: c[0] + c[1] + c[2]
warm = lambda c: c[0] > c[1] > c[2] and c[0] - c[2] > 35


def calm(g):
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer"):
        g.js(f"setOpt('{o}', 0)")


def at(g, x, y, z, n=1):
    g.rpc("dev_teleport", x=x, y=y, z=z)
    g.arrive()
    g.wait(f"HdLook.win.a === 1 && HdLook.win.n >= {n} && !HdLook.busy && HdLook.cam.pitch > 67.9 && HdLook.level[1] === {z}", timeout=8000)
    g.js("(() => { WayShow.paint = () => {}; return 1; })()")
    g.rest()


def test_a_stair_s_treads_are_warm_steps_lighter_at_the_top_and_the_floor_is_a_good_part_of_the_hole(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = stair(g)
    at(g, x + 5, y, -5)
    g.js("(() => { HdLook.veil = 0; return 1; })()"); g.frames(3)               # (the treads' own light: the veil of the meadow south of them lays a little of its green over the open ones: test_e2e_hd_behind.py)
    treads = {i: g.js(TILE, [x + i, y, -i]) for i in (2, 3, 4, 7, 8)}          # 2 to 4 under the open sky, 7 and 8 under the land
    assert all(warm(c) for c in treads.values()), treads                         # steps you can walk: warm earth, the open ones too (they were (106, 90, 85): grey)
    assert lum(treads[2]) > lum(treads[3]) > lum(treads[4]) and lum(treads[2]) > lum(treads[4]) * 1.1 and lum(treads[7]) > lum(treads[8]), treads    # the top ones lighter: down is read
    assert g.js("HdLook.raw()") == 0
    # the passage at its foot, one tile wide, 14 deep, a roof three over its floor: the section over its north wall is the ground's true height in strata, the floor wider than its own wall
    at(g, x + 17, y, -14)
    top = g.js(f"HdLook.screenOf({x + 17.5}, {y}, -11)")
    col = g.js("([px, py]) => { const k = devicePixelRatio, o = []; for (let j = 1; j < 40; j++) o.push([...HdLook.read(Math.round(px * k), Math.round((py - j * zoom) * k), 1, 1).data.slice(0, 3)]); return o; }", top)
    sect = next((i for i, c in enumerate(col) if c[1] > c[0] + 8), len(col))    # rows of earth over the wall's top, up to the meadow's green
    a, b, w = (g.js(f"HdLook.screenOf({x + 17.5}, {y + dy}, {z})")[1] / g.js("zoom") for dy, z in ((0, -14), (1, -14), (0, -11)))
    floor, wall = b - a, a - w
    assert sect >= 24, (sect, col)                                               # (the ground over the passage's ceiling, 11 levels, at its true height from this eye, in strata: test_e2e_hd_stair.py. It was capped at half the floor: a passage 14 down read 2 down)
    assert sum(col[1]) < sum(col[sect - 4]) * .7, col                            # darker down: one deep wall, not a slab of one tone lying over the floor
    assert floor / (floor + wall) >= .5, (floor, wall, sect)
    assert warm(g.js(TILE, [x + 16, y, -14])) and g.js("HdLook.catSeen()") > .8


def test_what_stands_in_a_deep_room_is_as_dim_as_its_floor_and_you_are_not(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.stamp(-9, -9, ["." * 34] * 19)
    g.rest()
    g.give(chest=2)
    seen = {}
    for depth, dx in ((4, 0), (14, 12)):
        deep_room(g, x + dx, y, depth)
        tx, ty = x + dx - 2, y - 2                                               # a chest in the room's far corner, on its north wall (the same picture in both rooms: a mushroom's is one of several)
        g.js("(a) => rpc('act', a)", {"tool": "place", "args": {"x": tx, "y": ty, "item": "chest", "z": -depth}})
        g.wait(f"isObject(combAt({tx}, {ty})) && !myAction", timeout=8000)
        g.rest()
        seen[depth] = (g.js(BRIGHT, [tx, ty, -depth]), lum(spot(g, x + dx - 2.5, y + 1.5, -depth)), g.js("HdLook.catSeen()"))
    (m4, f4, me4), (m14, f14, me14) = seen[4], seen[14]
    assert f14 < f4 * .9, seen                                                   # (the deep room's far floor is dimmer: test_e2e_hd_stair.py)
    assert m14 < m4 * .9 and m14 > m4 * .6, seen                                 # and so is the chest on it (it glowed: the day's colours on a dim floor); still read
    assert me4 > .8 and me14 > .8, seen                                          # your own body: its own colours in both


@pytest.mark.realtime
def test_the_plants_over_your_room_go_and_come_over_a_few_frames(browser, server):
    g = hd(browser, server)
    x, y = room(g, flowers=True)
    inside(g, x, y)
    over = [[x - 1, y - 1], [x - 2, y], [x + 2, y], [x + 1, y + 1]]             # (hd_window's flowers: on the meadow, level 4, over the room)
    mine = lambda l: [s for s in l if s[:2] in over]
    assert not mine(g.js("HdLook.stands()"))                                     # the window is on them: not drawn
    rec = """(() => { window.__f = []; window.__on = true; const f = () => { __f.push(HdLook.fades().map((v) => v[2])); if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
    for shut, there in ((True, 4), (False, 0)):
        g.js(rec)
        g.js(f"HdLook.nowin = {'true' if shut else 'false'}")
        g.wait(f"HdLook.win.a === {0 if shut else 1}", timeout=4000)
        g.sleep(500)
        fr = g.js("(() => { __on = false; return __f; })()")
        part = [min(f) for f in fr if f]                                         # the frames in which some of them are drawn in part: how much
        assert len(part) >= 3 and all(0 < v < 1 for v in part), (shut, part)     # over a few frames (120 ms), never in one
        assert part == sorted(part, reverse=not shut), (shut, part)              # coming: more each frame; going: less
        assert not fr[-1] and len(mine(g.js("HdLook.stands()"))) == there, (shut, fr[-3:], g.js("HdLook.stands()"))
    assert not g.errors


def test_no_px_is_drawn_from_a_paint_that_is_not_there_on_ten_walks_down_the_stair_and_back(browser, server):
    g = hd(browser, server)
    g.rpc("dev_time", phase=.3)
    x, y = stair(g)
    g.js("""(() => { window.__raw = 0; window.__n = 0; window.__on = true; const f = () => { __raw = Math.max(__raw, HdLook.raw()); __n++; if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()""")
    for _ in range(10):
        for key, done in (("ArrowRight", f"myPos().x >= {x + 18}"), ("ArrowLeft", f"myPos().x <= {x}")):
            g.page.keyboard.down(key)
            g.wait(done, timeout=20000)
            g.page.keyboard.up(key)
    n, raw = g.js("(() => { __on = false; return [__n, __raw]; })()")
    assert n > 300 and raw == 0, (n, raw)                                        # every frame read: no px of the land from an empty paint
    # and were the shown land's paints lost (they cannot be now: a full sheet no longer wipes them): the counter sees it, and the land is its mean colour, not one earth brown
    g.rest()
    spot = [x - 4.5, y + 2.5, 0]
    grass = g.js(PX, spot)
    g.js("HdLook.blank()")
    g.frames(3)
    lost = g.js(PX, spot)
    assert g.js("HdLook.raw()") > 1000, g.js("HdLook.raw()")
    assert grass[1] > grass[0] and not (lost[0] > lost[1] + 12), (grass, lost)   # (it was (107, 82, 64) whatever the land)
    assert not g.errors


def test_on_grey_stone_the_hole_has_a_darker_lip_and_on_a_meadow_a_light_one(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.stamp(-9, -9, ["." * 34] * 19)
    g.rest()
    g.rpc("dev_col", tiles=[[x + 12 + i, y + j] for j in range(-5, 6) for i in range(-5, 6)], col=[6])     # a block of stone, level 6
    out = {}
    for name, cx, lv in (("meadow", x, 0), ("stone", x + 12, 6)):
        g.rpc("dev_col", tiles=[[cx + i, y + j] for j in (-1, 0) for i in (-1, 0, 1)], col=[lv - 5, lv - 2, lv])
        at(g, cx, y, lv - 5, 6)
        scan = [g.js(PX, [cx + 1.5, y + 1 + i * .02, lv]) for i in range(60)]     # south of the room: from the hole's edge out onto the ground
        k = next(i for i, c in enumerate(scan) if not warm(c))                   # (before it: the room's floor, seen in the hole)
        # (the ground beyond the lip and far from it: the colour most px of a piece of it have, a tile wide. One px, and
        # the middle one of a row of eleven, were a mark of the stone's own picture, 447 for 495, wherever you woke with one under it: one run in six)
        out[name] = (scan[k], g.js(MOST, [cx + 1, y + 2.15, cx + 2, y + 2.45, lv]), g.js(MOST, [cx + 1, y + 3.2, cx + 2, y + 3.8, lv]))
    lip, far, ground = out["stone"]
    assert max(ground) - min(ground) < 30, out                                   # (grey)
    assert lum(lip) < lum(ground) * .8 and lum(far) > lum(ground) * .93, out     # stone: its own px a good step darker along the hole's near edge, then the stone as it is
    lip, far, ground = out["meadow"]
    assert lum(lip) > lum(ground) + 12 and lum(far) < lum(ground) + 12, out      # a meadow: the lit lip, as it was
