"""Under the land or behind it, in the HD look (hd_level.js `over`, `sunk`, `under`, `steep`; vox_style.js; vox_style_glsl.js;
vox_style_land.js; hd.js). ONE question, "how much land is over the eye's line to these feet", answers all of it:
on a small hill, or behind it, no x-ray window opens (the hill's top was opened onto the meadow behind it: "the hill fell
apart under me"); behind land (a hill, a wall you built) your body is hidden where the land is in front and shows through
it one px in two (it was drawn whole over the wall: "I stand on it"); in a pit seen from the side the floor shows through
a veil of the meadow in front of it (it lay on the meadow, "a drawer pulled out"); the eye tilts by one rule (no tile of
the floor you stand on shows from the side); a tunnel is not opened from afar nor from the hill over it; a fire under the
land does not light the meadow; who stands on the meadow over your room has its ground under them."""

from test_e2e_hd_land import AT_
from test_e2e_hd_sun import hd

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
    assert behind["n"] == 0 and behind["a"] == 0 and behind["pitch"] < 36.1, behind
    assert .05 < behind["seen"] < .6, behind                               # hidden where the hill is in front, one px in two of you through it (it was 1: all of you, over a hill opened like a box)
    front = go(g, x + 4, y + 5)
    assert front["n"] == 0 and front["seen"] > .9, front
    tidy(g, x, y)


def test_behind_a_wall_you_built_your_body_is_behind_it_not_on_it(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.give(dirt=4)
    for z in (1, 2):
        r = g.js("(a) => rpc('act', a)", {"tool": "place", "args": {"x": x, "y": y - 1, "item": "dirt", "z": z}})
        assert r.get("ok"), r
    g.settle(f"topAt({x}, {y - 1}) === 2")
    whole = go(g, x, y)
    assert whole["seen"] > .9 and whole["n"] == 0, whole                   # in front of it: all of you
    s = go(g, x, y - 2)                                                    # behind it
    assert s["n"] == 0 and s["pitch"] < 36.1 and .3 < s["seen"] < .9, s    # your head over the wall whole, the rest through it (it was 1: the whole cat, feet on the wall's top)
    lv = go(g, x, y - 1, 2)                                                # ON it
    assert lv["seen"] > .9 and lv["n"] == 0, lv
    tidy(g, x, y)


def test_in_a_pit_seen_from_the_side_the_floor_shows_through_a_veil_of_the_meadow(browser, server):
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in (-1, 0, 1) for i in (3, 4, 5)], col=[-4])     # a pit 3 x 3, four deep
    g.rest()
    s = go(g, x + 4, y + 1, -4, "HdLook.win.a === 1 && !HdLook.busy")       # its south row: behind the pit's south wall
    g.js("(() => { WayShow.paint = () => {}; return 1; })()"); g.frames(3)  # (the way out's marks run over these px)
    assert s["pitch"] < 36.1 and s["n"] >= 3 and s["seen"] > .9, s        # the side view (its north row shows from the side), the window on it, you whole
    P = {"west": [x + 3.5, y + 1.5, -4], "east": [x + 5.5, y + 1.5, -4], "mine": [x + 4.2, y + 1.85, -4]}     # the floor beside you, each side; a corner of your own tile
    read = lambda: {k: g.js(AT_, v) for k, v in P.items()}
    on = read()
    g.js("(() => { HdLook.veil = 0; return 1; })()"); g.frames(3)
    off = read()
    g.js("(() => { HdLook.veil = 1; return 1; })()"); g.frames(3)
    tint = lambda k: (on[k][1] - on[k][0]) - (off[k][1] - off[k][0])
    assert not any(green(c) for c in list(on.values()) + list(off.values())), (on, off)      # the floor's own px, with the veil too (the first veil was a dark checker: one px in two was grass)
    assert max(tint("west"), tint("east")) >= 6, (on, off)                 # a little of the meadow's green over the floor: seen through the ground (one side may be your way: clear)
    assert all(sum(on[k]) >= sum(off[k]) - 12 for k in on), (on, off)      # and never darker for it
    assert on["mine"] == off["mine"], (on, off)                            # your own tile: clear
    grass = lambda c: c[1] >= c[0] and c[1] > c[2] + 40
    south = [g.js(AT_, [x + dx + .5, y + 4.5, 0]) for dx in (1, 7)]
    assert all(grass(c) for c in south), south                             # the meadow south of it: whole
    tidy(g, x, y)


def test_the_eye_tilts_by_one_rule(browser, server):
    """No tile of the floor you stand on shows from the side (two levels of land or more over the eye's line to each):
    from above; back when one shows again (under one level). The table: [where, its level, from above?], in the order walked."""
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
             ("stair 1 wide", (x + 1, y - 5, -1), False), ("stair 1 wide", (x + 2, y - 5, -2), False), ("stair 1 wide", (x + 3, y - 5, -3), True), ("stair 1 wide", (x + 6, y - 5, -6), True),
             ("stair 1 wide, back up", (x + 2, y - 5, -2), True), ("stair 1 wide, back up", (x + 1, y - 5, -1), False),      # (its hysteresis is the land's: out a step higher than in)
             ("stair 3 wide", (x + 3, y + 3, -3), False), ("stair 3 wide", (x + 5, y + 3, -5), False), ("stair 3 wide, its floor", (x + 8, y + 3, -6), True),
             ("meadow", (x, y, 0), False), ("pit 3 x 3, 4 deep", (x - 5, y, -4), False), ("pit, its south row", (x - 5, y + 1, -4), False),
             ("meadow", (x, y, 0), False), ("shaft 6 deep", (x - 5, y - 6, -6), True),
             ("meadow", (x, y, 0), False), ("room 14 deep", (x - 7, y + 8, -14), True),
             ("meadow", (x, y, 0), False), ("cave, a tile in", (x - 8, y - 4, 0), False), ("cave, three tiles in", (x - 8, y - 6, 0), False), ("cave, its end", (x - 8, y - 9, 0), True)]
    got = []
    for name, (tx, ty, tz), steep in table:
        s = go(g, tx, ty, tz)
        got.append((name, tz, round(s["pitch"]), round(g.js("HdLevel.shows"), 1)))
    want = [(name, at[2], 68 if steep else 36) for name, at, steep in table]
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


def test_a_fire_under_the_land_does_not_light_the_meadow_and_who_stands_over_your_room_has_the_ground_under_them(browser, server):
    g = hd(browser, server)
    g.js("setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    x, y = g.pos()
    cid = g.spawn("chicken", 1, 2, still=4000)                             # (on the meadow, before the room is under it; it stays)
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
    # somebody on the meadow over the room
    g.hour(.3, still=True)
    key = f"chicken{cid}"
    g.wait(f"ents.has('{key}') && HdLook.bodies().some((b) => b[0] === 'chicken')", timeout=8000)
    g.rest()
    b = g.js(f"(() => {{ const q = ents.get('{key}'); return [Math.round(q.x), Math.round(q.y), q.e.z, q.x, q.y]; }})()")
    assert b[:3] == [x + 1, y + 2, 0], (b, g.js("HdLook.bodies()"))        # where it was put, on the meadow: over the room's south rows, where the land's top is inside the window on the screen
    pair = [g.js(AT_, [b[0] + .5 + o / 16, b[1] + .9, 0]) for o in (-7, -5)]     # its tile's south-west corner: not its body
    grass = lambda c: c[1] >= c[0] and c[1] > c[2] + 40                    # (a meadow's px: its green, and its pale tufts: (210, 225, 119) was "not green", once in eight runs)
    assert sum(grass(c) for c in pair) == 1, (pair, b, g.js("[HdLook.bodies(), HdLook.win.a, HdLook.win.n]"))     # the grass under its feet: one px in two of it stays (it hung in the room's picture, nothing under it)
    assert not grass(g.js(AT_, [x - 1.5, y + 2.5, 0])) and not grass(g.js(AT_, [x - 1.5 + 2 / 16, y + 2.5, 0]))    # a tile of the roof nobody stands on: lifted
    tidy(g, x, y)
