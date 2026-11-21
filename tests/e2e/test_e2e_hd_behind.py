"""Under the land or behind it, in the HD look (hd_level.js `over`, `sunk`, `under`, `steep`; vox_style.js; vox_style_glsl.js;
vox_style_land.js; hd.js). ONE question, "how much land is over the eye's line to these feet", answers all of it:
on a small hill, or behind it, no x-ray window opens (the hill's top was opened onto the meadow behind it: "the hill fell
apart under me"); behind land (a hill, a wall you built) your body is hidden where the land is in front and shows through
it one px in two (it was drawn whole over the wall: "I stand on it"); in a pit seen from the side the floor shows through
no window under the open sky: from above its own south wall hides what is behind it, its floor lies inside its rim (it lay on
the meadow, "a drawer pulled out"); the eye tilts by one rule (your feet two levels under the land round you); a tunnel is not opened from afar nor from the hill over it; a fire under the
land does not light the meadow; under a roof who stands on the land over you is not seen (no mob through the ceiling), who is in your room is."""

from test_e2e_hd_land import AT_
from test_e2e_hd_sun import hd

STEEP = 78.6        # the eye's pitch from above (hd.js api.steep: 68 when a level was 8 px; tan 78.6 = 2 tan 68)

green = lambda c: c[1] > c[0] + 15 and c[1] > c[2] + 40
STATE = "(() => ({n: HdLook.win.n, a: HdLook.win.a, pitch: HdLook.cam.pitch, seen: HdLook.catSeen()}))()"


def calm(g):
    g.hour(.3, still=True)
    g.js("setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")


def go(g, x, y, z=None, wait="!HdLook.busy"):
    g.rpc("dev_teleport", **({"x": x, "y": y} if z is None else {"x": x, "y": y, "z": z}))
    g.arrive()
    g.wait(wait, timeout=8000)
    g.sleep(700)                                                           # (the window's hold and the eye's tilt: 300 + 400 ms of the game's time, whichever way they go)
    g.rest()
    return g.js(STATE)


def tidy(g, x, y):
    """The meadow as it was round (x, y), nobody on it: the world is the next test's too (a hill left standing laid its shadow on another test's stone)."""
    g.rpc("dev_teleport", x=x, y=y, z=0)
    g.arrive()
    g.rpc("dev_creatures", clear=40)
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-14, 15) for i in range(-14, 15)], col=[0])     # (whole land: a stamp lays a meadow over a room, it does not fill it)
    g.stamp(-14, -14, ["." * 29] * 29)
    g.rest()


def test_on_a_small_hill_and_behind_it_no_window_opens_and_behind_it_you_show_through(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.stamp(3, 1, ["...."] * 3, levels=["4444"] * 3)                       # a hill four high, 4 x 3 (the sixth audit's)
    g.rest()
    on = go(g, x + 4, y + 1, 4)                                            # on its top, its north row
    assert on["n"] == 0 and on["a"] == 0 and on["pitch"] < 36.1 and on["seen"] > .9, on
    assert green(g.js(AT_, [x + 5.5, y + 2.5, 4])), "the hill's top is its own grass"
    behind = go(g, x + 4, y)                                               # one tile north of it: behind it, not under it
    assert behind["n"] == 0 and behind["a"] == 0 and behind["pitch"] > 36.1, behind     # (land over your head south of you: the eye looks down over it, hd_level.js clear)
    assert behind["seen"] > .9, behind                                     # whole (it was one px in two of you in the disc's own px: a checker cat, audit A8 B5)
    front = go(g, x + 4, y + 5)
    assert front["n"] == 0 and front["seen"] > .9, front
    tidy(g, x, y)


def test_behind_a_wall_you_built_your_body_is_behind_it_not_on_it(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.give(dirt=4)
    for z in (1,):                                                         # (a block: as tall as you, 16 px: it was two 8 px levels)
        r = g.js("(a) => rpc('act', a)", {"tool": "place", "args": {"x": x, "y": y - 1, "item": "dirt", "z": z}})
        assert r.get("ok"), r
    g.settle(f"topAt({x}, {y - 1}) === 1")
    whole = go(g, x, y)
    assert whole["seen"] > .9 and whole["n"] == 0, whole                   # in front of it: all of you
    s = go(g, x, y - 2)                                                    # behind it
    assert s["n"] == 0 and s["pitch"] < 36.1 and .3 < s["seen"] < .9, s    # your head over the wall whole, the rest through it (it was 1: the whole cat, feet on the wall's top)
    lv = go(g, x, y - 1, 1)                                                # ON it
    assert lv["seen"] > .9 and lv["n"] == 0, lv
    tidy(g, x, y)


def test_in_a_hole_the_eye_looks_from_above_and_its_floor_lies_inside_its_rim(browser, server):
    """(The fourth audit's "a drawer pulled out onto the grass": the x-ray window cut the hole's south wall away and its floor was
    drawn where it projects, south of the rim, on the meadow; a veil of the meadow over it did not help.) In any hole two deep
    or more the eye looks from above (STEEP) and no window opens under the open sky: the hole's own south wall hides what is behind
    it, so every px of the floor that shows lies inside the rim, and the meadow just south of the rim is grass."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in (-1, 0, 1) for i in (3, 4, 5)], col=[-4])     # a pit 3 x 3, four deep
    g.rest()
    for at in ((x + 4, y), (x + 4, y + 1)):                                # its middle; its south row, behind its south wall
        s = go(g, *at, -4, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep")
        g.js("(() => { WayShow.paint = () => {}; return 1; })()"); g.frames(3)
        assert s["pitch"] == STEEP and s["n"] == 0, s
        assert s["seen"] > .1, s                                           # you: whole, or one px in two where the south wall is in front
        south = [g.js(AT_, [x + i + .5, y + 2.35, 0]) for i in (3, 4, 5)]  # the meadow a third of a tile south of the rim: no floor hangs there
        assert all(c[1] >= c[0] for c in south), (at, south)               # (grass, a flower's px too: never the floor's brown)
        inside = [g.js(AT_, [x + i + .5, y - .5, -4]) for i in (3, 4, 5)]  # the floor's north row: drawn, inside the rim
        rim = [g.js("([x, y, z]) => HdLook.screenOf(x, y, z)[1]", [x + 4.5, v, 0]) for v in (y - 1, y + 2)]
        fl = g.js("([x, y, z]) => HdLook.screenOf(x, y, z)[1]", [x + 4.5, y - .5, -4])
        assert rim[0] < fl < rim[1] and not any(green(c) for c in inside), (rim, fl, inside)
    tidy(g, x, y)


def test_a_deep_shaft_is_darker_than_a_shallow_one(browser, server):
    """Shaft 3 and shaft 6 were the same picture (a cat in a brown box). From above, the wall strata of the north wall fill
    more of the opening the deeper it is (3 px a level), and the walls of a hole are darker the deeper the hole is (vox_style_glsl.js:
    2 deep light brown, 6 near black, 12 black): the opening of shaft 6 is much darker than shaft 3's, shaft 12's darker still.
    (You stand in the openings, drawn at the rim's line: your own px, cream and purple, are not counted.)"""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + 3, y]], col=[-3])
    g.rpc("dev_col", tiles=[[x + 7, y]], col=[-6])
    g.rpc("dev_col", tiles=[[x + 11, y]], col=[-12])
    g.rest()
    LUM = """([x, y]) => { const a = HdLook.screenOf(x + .5, y, 0), b = HdLook.screenOf(x + .5, y + 1, 0), k = cv.width / innerWidth; let s = 0, n = 0;
      for (let v = Math.ceil(a[1] * k) + 2; v < Math.floor(b[1] * k) - 2; v++) for (let dx = -16; dx <= 16; dx += 2) { const d = HdLook.read(Math.round(a[0] * k + dx), v, 1, 1).data; if (d[0] > 185 || d[2] > d[1] + 8) continue; s += .3 * d[0] + .59 * d[1] + .11 * d[2]; n++; } return [s / n, n]; }"""
    out = {}
    for d, tx in ((3, x + 3), (6, x + 7), (12, x + 11)):
        s = go(g, tx, y, -d, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep")
        assert s["pitch"] == STEEP, s
        out[d] = g.js(LUM, [tx, y])
    assert out[6][1] >= 6 and out[6][0] < out[3][0] - 25 and out[12][0] < out[6][0], out     # (it was 68 against 85: one picture)
    tidy(g, x, y)


def test_in_a_shaft_six_deep_no_px_of_your_body_lies_outside_the_hole_s_opening(browser, server):
    """(After the eye came to look from above: "a ghost on the grass".) No pitch below 90 puts a deep 1x1 floor inside its
    rim: your body, behind the south rim, was drawn one px in two on the meadow just south of the hole. In a hole seen from
    above you are drawn no deeper than the eye sees past the rim south of you (hd_level.js `lift`): your feet on that rim's
    line, whole, every px of you that shows inside the hole's opening on the screen. The floor is not moved (no drawer)."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + 3, y]], col=[-6])
    g.rest()
    s = go(g, x + 3, y, -6, "!HdLook.busy && HdLook.cam.pitch === HdLook.steep")
    assert s["pitch"] == STEEP and s["n"] == 0, s
    nw, se = g.js(f"HdLook.screenOf({x + 3}, {y}, 0)"), g.js(f"HdLook.screenOf({x + 4}, {y + 1}, 0)")
    u = g.js("zoom")
    seen, out = g.js("(b) => HdLook.catSeen(b)", [nw[0] - u, nw[1] - u, se[0] + u, se[1] + u])
    assert seen > .6 and out == 0, (seen, out, nw, se)                     # (it was .44 seen, a checker of you under the rim)
    south = [g.js(AT_, [x + 3 + i, y + 1.35, 0]) for i in (.3, .5, .7)]
    assert all(green(c) for c in south), south                             # the meadow south of the rim: grass, nothing of you
    floor = g.js(f"HdLook.screenOf({x + 3.5}, {y + .5}, -6)")
    assert floor[1] > se[1], (floor, se)                                   # the floor itself is where it is: past the rim (hidden), not drawn inside it
    tidy(g, x, y)


def test_the_eye_tilts_by_one_rule(browser, server):
    """Your feet a level (your height, a cube) or more under the land round you (ten of sixteen straight ways out, 6 tiles long, run into
    land a level over your feet: a wall or two beside you is not "round you"): from above; level with it: the surface's pitch. Every hole alike. The table: [where, its level, from above?], in the order walked."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    col = lambda tiles, c: g.rpc("dev_col", tiles=[list(t) for t in tiles], col=c)
    for i in range(1, 7):
        col([(x + i, y - 5)], [-i])                                        # a stair one tile wide, six down
        col([(x + i, y + j) for j in (2, 3, 4)], [-i])                     # a stair three wide, six down ...
    col([(x + i, y + j) for j in (2, 3, 4) for i in (7, 8, 9)], [-6])      # ... to a floor 3 x 3
    col([(x - 6 + i, y + j) for j in (-1, 0, 1) for i in (0, 1, 2)], [-4])  # a pit 3 x 3, four deep
    col([(x - 5, y - 6)], [-6])                                            # a shaft six deep
    col([(x - 9 + i, y + 6 + j) for j in range(5) for i in range(5)], [-14, -11, 0])      # a room 14 deep
    col([(x - 9 + i, y - 9 + j) for j in range(6) for i in range(3)], [0, 2, 5])            # a cave in a block of land five high, its mouth to the south ...
    col([(x - 9 + i, y - 9 + j) for j in range(6) for i in (-1, 3)] + [(x - 9 + i, y - 10) for i in range(-1, 4)], [5])
    g.rest()
    table = [("meadow", (x, y, 0), False),
             ("stair 1 wide", (x + 1, y - 5, -1), True), ("stair 1 wide", (x + 2, y - 5, -2), True), ("stair 1 wide", (x + 3, y - 5, -3), True), ("stair 1 wide", (x + 6, y - 5, -6), True),
             ("stair 1 wide, back up", (x + 2, y - 5, -2), True), ("stair 1 wide, back up", (x + 1, y - 5, -1), True),      # (its hysteresis is the land's: out a step higher than in)
             ("stair 3 wide", (x + 3, y + 3, -3), True), ("stair 3 wide", (x + 5, y + 3, -5), True), ("stair 3 wide, its floor", (x + 8, y + 3, -6), True),
             ("meadow", (x, y, 0), False), ("pit 3 x 3, 4 deep", (x - 5, y, -4), True), ("pit, its south row", (x - 5, y + 1, -4), True),
             ("meadow", (x, y, 0), False), ("shaft 6 deep", (x - 5, y - 6, -6), True),
             ("meadow", (x, y, 0), False), ("room 14 deep", (x - 7, y + 8, -14), True),
             ("meadow", (x, y, 0), False), ("cave, a tile in", (x - 8, y - 4, 0), True), ("cave, three tiles in", (x - 8, y - 6, 0), True), ("cave, its end", (x - 8, y - 9, 0), True)]
    got = []
    for name, (tx, ty, tz), steep in table:
        s = go(g, tx, ty, tz)
        got.append((name, tz, round(s["pitch"]), round(g.js("HdLevel.shows"), 1)))
    want = [(name, at[2], round(STEEP) if steep else 36) for name, at, steep in table]
    assert [v[:3] for v in got] == want, got
    tidy(g, x, y)


def test_a_tunnel_is_not_opened_from_afar_nor_from_the_hill_over_it(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-3, 4) for i in range(4, 13)], col=[6])     # a hill of stone six high, 9 x 7 ...
    g.rpc("dev_col", tiles=[[x + i, y] for i in range(4, 13)], col=[0, 2, 6])                          # ... a tunnel through it, east to west
    g.rest()
    far = go(g, x, y)                                                      # four tiles west of its mouth
    assert far["n"] == 0 and far["a"] == 0 and far["pitch"] < 36.1, far    # (it was 9 boxes: the tunnel cut open through the hill's south front)
    top = go(g, x + 8, y, 6)                                               # on the hill, over the tunnel
    assert top["n"] == 0 and top["seen"] > .9, top
    inside = go(g, x + 8, y, 0, "HdLook.win.a === 1 && !HdLook.busy")
    assert inside["n"] >= 9 and inside["seen"] > .9, inside
    tidy(g, x, y)


def test_a_fire_under_the_land_does_not_light_the_meadow(browser, server):
    g = hd(browser, server)
    g.js("setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[-14, -11, 0])
    g.give(campfire=1)
    g.rest()
    west = lambda: go(g, x - 3, y, -14, "HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > 67.9")     # the room's west end: your own lantern does not reach its east end
    g.hour(.9, still=True)
    west()
    lum = lambda c: c[0] + c[1] + c[2]
    P = {"meadow": [x + 4.5, y + 3.5, 0], "floor": [x + 3.5, y + 1.5, -14]}   # the meadow two tiles from where the fire will be, as the screen has them; the room's floor beside it
    read = lambda: {k: lum(g.js(AT_, v)) for k, v in P.items()}
    dark = read()                                                          # the SAME px before the fire and with it (two px of a meadow differ by its tufts, and the fire flickers: it was one px against another, with a margin)
    go(g, x, y, -14)
    r = g.js("(a) => rpc('act', a)", {"tool": "place", "args": {"x": x + 2, "y": y, "item": "campfire", "z": -14}})
    assert r.get("ok"), r
    west()
    lit = dark
    for _ in range(60):                                                    # until its light is in the picture (the server's tick, the tile on the page, the light's picture made again)
        g.frames(3)
        lit = read()
        if lit["floor"] > dark["floor"] + 15:
            break
    state = g.js(f"[clock.phase, HdLook.win.a, HdLook.cam.pitch, combAt({x + 2}, {y}), HdLook.stands()]")
    assert lit["floor"] > dark["floor"] + 15, (dark, lit, state)           # the room's floor by the fire: lit
    assert abs(lit["meadow"] - dark["meadow"]) <= 6, (dark, lit, state)    # the meadow over it: as it was (it had a warm ring, 14 levels over the fire)
    tidy(g, x, y)


def test_under_a_roof_a_hen_on_the_land_over_you_is_not_drawn_a_hen_in_your_room_is(browser, server):
    """A room 4 deep under a roof two thick; a hen on the meadow right over your head and one in the room with you. The one up
    there was drawn in full colour over the window, the ground under its feet kept one px in two: "underground still shows mobs above me"."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    up = g.spawn("chicken", 0, -1, still=60000)                            # on the meadow (level 0), before the room is dug under it
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-2, 3) for i in range(-3, 4)], col=[-4, -2, 0])
    g.rest()
    go(g, x, y, -4, "HdLook.win.a === 1 && !HdLook.busy && HdLook.cam.pitch > 67.9")
    down = g.spawn("chicken", 2, 0, still=60000)                           # at your level: in the room
    g.wait(f"ents.has('chicken{up}') && HdLook.bodies().some((b) => b[0] === 'chicken' && b[1] === -4)", timeout=8000)
    g.rest()
    where = g.js(f"[['chicken{up}', 'chicken{down}'].map((k) => {{ const q = ents.get(k); return q && [Math.round(q.x), Math.round(q.y), q.e.z]; }}), HdLook.winAt({x}, {y - 1})]")
    assert where[0] == [[x, y - 1, 0], [x + 2, y, -4]] and where[1], where       # one on the roof over the window's tile north of you, one on your floor
    assert g.js("HdLook.bodies()") == [["chicken", -4]], where            # only the one in your room is drawn (and so no name, no mark for the one up there)
    tidy(g, x, y)


def test_the_ground_before_a_tunnel_s_mouth_has_no_shade_of_the_hole(browser, server):
    """Standing in a tunnel through a hill, a tile from its mouth: the tile before the mouth is under the open sky
    and no box of the window (it was its first box). The meadow seen through it is plain ground, not a floor in a hole: it took the hole's inner
    shade, counted from the hill's top: a dark line on the grass beside the hill, at the ceiling's height."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    hill = [[x + i, y + j] for j in range(-3, 4) for i in range(4, 13)]
    g.rpc("dev_col", tiles=hill, col=[6])
    g.rpc("dev_col", tiles=[[x + i, y] for i in range(4, 13)], col=[0, 2, 6])
    g.rest()
    try:
        s = go(g, x + 5, y, 0, "HdLook.win.a === 1 && !HdLook.busy")
        g.js("(() => { WayShow.paint = () => {}; return 1; })()"); g.frames(3)
        assert not g.js(f"!!HdLook.winAt({x + 3}, {y})"), s                  # the tile before the mouth is under the open sky: not of the window (audit A8: the window on the open shaft you stepped out of drew its floor south of its rim)
        P = [[x + 3 + i / 4, y - 1 + j / 8, 0] for i in (1, 2) for j in range(-3, 8)]     # the meadow north of it, beside the hill
        on = [g.js(AT_, p) for p in P]
        g.js("HdLook.nowin = true"); g.wait("HdLook.win.a === 0", timeout=4000); g.frames(2)
        off = [g.js(AT_, p) for p in P]
        g.js("HdLook.nowin = false")
        bad = [(p, c, d) for p, c, d in zip(P, on, off) if any(abs(a - b) > 8 for a, b in zip(c, d))]
        assert not bad, bad
    finally:
        g.rpc("dev_col", tiles=hill, col=[0])


def test_behind_a_cliff_the_eye_looks_down_over_it_and_you_are_whole(browser, server):
    """Behind land taller than you (a cliff's back), on the surface: the eye looks down as steeply as it must to see you
    and the ground at your feet over it (hd_level.js clear). (You were a faint checker on the cliff's face, a sixth of
    you; then a disc of one px in two in it: with cubes, a plateau over half the screen.) In front of it: as ever."""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    hill = [[x + i, y + j] for j in range(-1, 4) for i in range(3, 10)]
    g.rpc("dev_col", tiles=hill, col=[5])                                 # (stone, from level 5: its grey top is not read as the meadow; 80 px high)
    g.rest()
    GROUND = """([cx, cy]) => { let n = 0, gr = 0; const k = devicePixelRatio; for (let j = -14; j <= 0; j++) for (let i = -6; i <= 6; i++) { const a = HdLook.screenOf(cx + .5 + i / 8, cy + .5 + j / 8, 0), c = HdLook.read(Math.round(a[0] * k), Math.round(a[1] * k), 1, 1).data; n++; if (c[1] > c[0] + 15 && c[1] > c[2] + 40) gr++; } return gr / n; }"""
    try:
        s = go(g, x + 6, y - 2)
        g.wait("HdLook.catSeen() > .9", timeout=4000)                      # (the disc opens over 120 ms)
        s = g.js(STATE)
        assert s["n"] == 0 and s["pitch"] > 60 and s["seen"] > .9, s        # no window; all of you, from above
        assert g.js(GROUND, [x + 6, y - 2]) > .5                           # the meadow at your feet, seen as it is (through the disc it was a checker: .15)
        s = go(g, x + 6, y + 5)
        assert s["seen"] > .95 and s["pitch"] < 36.1, s                    # in front of it: whole, the surface's pitch
    finally:
        g.rpc("dev_col", tiles=hill, col=[0])

