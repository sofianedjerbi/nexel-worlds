"""A stair and a passage one tile wide in the HD look, and what stands in the x-ray window (vox_style_glsl.js,
vox_style_land.js, vox_style.js, hd.js, hd_ease.js): a dug stair's treads under the land are warm steps, lighter at the top than at
the bottom (its open ones are ground under the sky, lit as any is: test_e2e_hd_cut.py); over a passage one
tile wide the section is the ground's height and the floor a whole tile of the hole; what stands in a deep room is as dim as its
floor, you are not; the plants over your room go and come over a few frames, not in one; a paint that is not there is
never drawn as earth brown, and no px is drawn from one on ten walks down the stair and back; on grey stone the hole has
a darker lip."""

from test_e2e_hd_stair import deep_room, spot, stair
from test_e2e_hd_sun import hd
from test_e2e_hd_window import PX

# the mean colour of a tile's top as the screen has it (the px inside its four corners' box, two px in): [r, g, b]
TILE = """([x, y, z]) => { const c = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => HdLook.screenOf(x + a, y + b, z)), k = devicePixelRatio;
  const x0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 2 * zoom, x1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 2 * zoom, y0 = Math.ceil(c[0][1] * k) + 2 * zoom, y1 = Math.floor(c[2][1] * k) - 2 * zoom;
  const d = HdLook.read(x0, y0, x1 - x0, y1 - y0).data, s = [0, 0, 0]; for (let i = 0; i < d.length; i += 4) for (let j = 0; j < 3; j++) s[j] += d[i + j]; return s.map((v) => Math.round(v / (d.length / 4))); }"""
# the brightest px of what stands on a tile (a box a tile wide, a tile high, over its floor's middle): r + g + b
BRIGHT = """([x, y, z]) => { const a = HdLook.screenOf(x + .5, y + .6, z), k = devicePixelRatio, w = 14 * zoom * k, d = HdLook.read(Math.round(a[0] * k - w / 2), Math.round(a[1] * k - w), w, w).data; let m = 0;
  for (let i = 0; i < d.length; i += 4) m = Math.max(m, d[i] + d[i + 1] + d[i + 2]); return m; }"""
lum = lambda c: c[0] + c[1] + c[2]
warm = lambda c: c[2] <= c[0] + 3 and .3 * c[0] + .59 * c[1] + .11 * c[2] > 110      # (your light: the floor's own colours, bright, never the cold grey-blue of a floor out of your way. It was the lantern's warm light, red 25 over blue: grey stone went olive, "keep the colors the same")


def calm(g):
    g.hour(.3, still=True)
    for o in ("clouds", "rays", "shimmer"):
        g.js(f"setOpt('{o}', 0)")


def at(g, x, y, z, n=1):
    g.rpc("dev_teleport", x=x, y=y, z=z)
    g.arrive()
    g.wait(f"HdLook.win.a === 1 && HdLook.win.n >= {n} && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1 && HdLook.level[1] === {z}", timeout=8000)
    g.js("(() => { WayShow.paint = () => {}; return 1; })()")
    g.rest()


def test_a_stair_s_covered_treads_are_warm_steps_lighter_at_the_top_and_the_floor_is_a_good_part_of_the_hole(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = stair(g)
    at(g, x + 9, y, -9)
    treads = {i: spot(g, x + i + .5, y + .5, -i) for i in (7, 8)}            # under the land, from in there. (The open ones, 2 to 4, are the ground under the sky: lit as any ground is, test_e2e_hd_cut.py)
    assert all(warm(c) for c in treads.values()), treads                         # steps you can walk: warm earth
    # the top one lighter: down is read. (7 and 8 are read from two treads down, not standing on 7: your own
    # sprite and shadow on its tile made it (149, 135, 115), not warm, one run in two.)
    assert lum(treads[7]) > lum(treads[8]), treads
    assert g.js("HdLook.raw()") == 0
    # the passage at its foot, one tile wide, 14 deep, a roof three over its floor: the land over it is not drawn (hd_cutaway.js), its floor a good part of the hole
    at(g, x + 17, y, -14)
    a, b, w = (g.js(f"HdLook.screenOf({x + 17.5}, {y + dy}, {z})")[1] / g.js("zoom") for dy, z in ((0, -14), (1, -14), (0, -11)))
    floor, wall = b - a, a - w
    assert g.js(f"HdLook.cut({x + 17}, {y})") == -12
    assert floor / (floor + wall) >= .3, (floor, wall)                    # (from 58 degrees a tile's floor is 13.6 px, a level of wall 8.5: the floor a whole tile, a third of the hole; from 78.6 it was .6)
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


# the HD look's picture on the screen, the look live (HdView.read reads none of it while hidden: [0, 0, 0]. Not `drew`: a still
# screen is not drawn again, and its picture stays)
SHOWN = "HdLook.live && !!HdView.el && HdView.el.style.display === 'block'"
# what a px read was taken from: the screen point, the canvases, the look's state
WHERE = """([x, y, z]) => { const a = HdLook.screenOf(x, y, z), el = HdView.el, cv = document.getElementById('c');
  const p = myPos(), m = p && HdLook.screenOf(p.x + .5, p.y + .5, myZ(p.x, p.y));
  return {at: a && a.map((v) => Math.round(v * devicePixelRatio)), me: p && [p.x, p.y], meAt: m && m.map((v) => Math.round(v * devicePixelRatio)), el: el && [el.width, el.height, el.style.display], cv: cv && [cv.width, cv.height], live: HdLook.live, lost: HdLook.lost, drew: HdLook.drew}; }"""
# until `expr` holds on the page, `n` frames at the most -> the frames it took, -1 if it never did (counted in frames: the same at any frame length)
UNTIL = """([expr, n]) => new Promise((ok) => { const f = new Function("return (" + expr + ")"); let k = 0; const g = () => { if (f()) ok(k); else if (++k > n) ok(-1); else requestAnimationFrame(g); }; g(); })"""
# you as the page has you: your tile, where you are drawn, the walk, what you are doing
STATE = "(() => { const p = ents.get('agent' + myId); return {pos: myPos(), at: p && [p.x, p.y, p.tx, p.ty], e: p && p.e && [p.e.x, p.e.y], walking: walking && walking.dir, pwalk: p && !!p.walking, act: myAction && myAction.tool, pred: !!pred, leap: Leap.on(), glide: Leap.gliding()}; })()"
# the eye on you: your screen point across the middle of the screen (CSS px)
ON_YOU = "(() => { const p = myPos(), m = p && HdLook.screenOf(p.x + .5, p.y + .5, myZ(p.x, p.y)); return !!m && Math.abs(m[0] - innerWidth / 2) < innerWidth * .15; })()"

def test_no_px_is_drawn_from_a_paint_that_is_not_there_on_ten_walks_down_the_stair_and_back(browser, server):
    g = hd(browser, server)
    g.rpc("dev_time", phase=.3)
    x, y = stair(g)
    g.js("""(() => { window.__raw = 0; window.__n = 0; window.__on = true; const f = () => { __raw = Math.max(__raw, HdLook.raw()); __n++; if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()""")
    for _ in range(10):
        for key, done in (("ArrowRight", f"myPos().x >= {x + 18}"), ("ArrowLeft", f"myPos().x <= {x}")):
            g.page.keyboard.down(key)
            if key == "ArrowLeft":                                               # up the steps: Space at each (walking into one stops you)
                for _ in range(200):
                    if g.js(done):
                        break
                    g.page.keyboard.press("Space")
                    g.frames(1)                                                  # (a press a frame drawn, not one every 100 ms of the machine's: #47)
            g.wait(done, timeout=20000)
            g.page.keyboard.up(key)
    n, raw = g.js("(() => { __on = false; return [__n, __raw]; })()")
    # every frame read: no face of the land from an empty paint. (A lost paint marks a whole face, about 200 px of the land's
    # canvas, art px; HdLook.blank below reads over 1000. raw counts any px of alpha 236 to 254, and one frame in 1013 of a
    # runner's had 1: a blended edge of what is drawn over the land, not a face)
    assert n > 300 and raw < 16, (n, raw, g.js("HdLook.work"))
    # and were the shown land's paints lost (they cannot be now: a full sheet no longer wipes them): the counter sees it, and the land is its mean colour, not one earth brown
    # (back at the stair's top where the walk began, the walk ended: one read on main was 10 tiles off the screen's left
    # edge, [-211, 192] of 960 px: run 45895689042. And the eye on you there, else the view is not where you are: a bug of its own)
    k = g.js(UNTIL, [f"myPos().x <= {x} && !walking && !myAction", 600])   # (frames, not ms: at 200 ms frames the walk's end takes longer than at 16)
    assert k >= 0, f"the walk back did not end at the stair's top (x <= {x}): {g.js(STATE)}"
    g.rest()
    spot = [x - 4.5, y + 2.5, 0]
    assert g.js(ON_YOU), ("the view is not on you", g.js(WHERE, spot))
    # (each px read off a frame the look drew and shows: one read on main gave [0, 0, 0] twice, no picture at all, the land
    # shown and drawn in the screenshot: run 45870743293. What the screen was then is said if it happens again)
    g.wait(SHOWN, timeout=8000)
    grass = g.js(PX, spot)
    g.js("HdLook.blank()")
    g.wait("HdLook.raw() > 1000", timeout=8000)                                  # (the lost paints drawn: what the counter sees, not three frames)
    g.wait(SHOWN, timeout=8000)
    lost = g.js(PX, spot)
    assert g.js("HdLook.raw()") > 1000, g.js("HdLook.raw()")
    assert grass[1] > grass[0] and not (lost[0] > lost[1] + 12), (grass, lost, g.js(WHERE, spot))   # (it was (107, 82, 64) whatever the land)
    assert not g.errors
