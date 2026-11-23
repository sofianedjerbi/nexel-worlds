"""Build mode, placing: one rule with digging (build.js `open`). A block to place is a whole box when something holds it
(the ground, a block, or a block planned under or beside it) and dotted when nothing does yet; dotted, nothing is said
and Space does nothing (it said in red "Nothing holds it"). By mouse, the block goes on the face pointed at: on a
block's west side, west of it (Minecraft's way), its ghost with its side showing; walls are pointed at as the boxes
they are (the ray went through them to the ground behind).
(The tests that Space says nothing put the welcome away first: it shows 3.2 s of the page's time after waking, and on
the tests' fast clock a quick set-up was still in it: "nothing said" read the welcome, one run in a few.)"""

import pytest

from test_e2e_hd_sun import hd

pytestmark = pytest.mark.e2e

# the cursor's place box as drawn the next frames: [x, y, z, far, whole line, dots]
PLACE = """async () => { const raf = () => new Promise((r) => requestAnimationFrame(r)); Target.drew = []; for (let i = 0; i < 60 && !Target.drew.length; i++) await raf(); await raf();
  const d = Target.drew.find((c) => c.key === "use"); return d ? [d.x, d.y, d.z, d.far, d.line > 0, d.dots > 0] : null; }"""
# the pointer moved to the place of the land (x, y, z) on the screen, again till the view (half way to the cursor) is still; -> the cursor
POINT = """async ([x, y, z]) => { const raf = () => new Promise((r) => requestAnimationFrame(r));
  for (let n = 0; n < 40; n++) { const p = HdLook.screenOf(x, y, z); cv.dispatchEvent(new MouseEvent('mousemove', {clientX: p[0], clientY: p[1], bubbles: true})); await raf(); await raf();
    const q = HdLook.screenOf(x, y, z); if (Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]) < .5) break; }
  Target.drew = []; for (let i = 0; i < 60 && !Target.drew.length; i++) await raf(); await raf();
  const a = Build.S.at; return {x: a.x, y: a.y, side: a.side || null, hint: Build.hint(a), drew: Target.drew.map((c) => [c.x, c.y, c.z, c.kind, c.line > 0, !!c.far]), ghost: BuildGhost.drew}; }"""


def test_a_block_nothing_holds_is_dotted_and_silent_and_whole_once_a_block_is_planned_under_it(game):
    game.clear_area(8)
    x, y = game.pos()
    game.give(dirt=6)
    game.hold_item("dirt")
    game.face(1, 0)
    game.press("z")
    game.wait("Build.on", 3000)
    game.js("(() => { Build.S.working = true; return 1; })()")           # (the work held: only plans)
    assert game.js(PLACE) == [x + 1, y, 1, False, True, False]          # on the ground: whole
    game.press("e", 100)                                                 # a level up, in the air: nothing beside it
    h = game.js("Build.hint(Build.S.at)")
    assert h["far"] is True and h["text"] == "" and h["z"] == 2, h
    assert game.js(PLACE) == [x + 1, y, 2, True, False, True]           # dotted
    assert not [r for r in game.js("Build.rows()") if r[0] == "Space"] and "Nothing holds" not in game.actions()
    assert game.js("BuildGhost.drew.z") is None                          # no ghost in it: its dotted box alone
    game.js("$('toast').style.display = 'none'")                        # (the welcome is up 3.2 s of the page's time from waking: a quick set-up read it)
    game.press(" ", 120)
    assert game.js("Build.S.plans.size") == 0 and game.toast() == ""    # Space on it: nothing
    game.press("q", 100)
    game.press(" ", 120)                                                 # a block planned on the ground...
    assert game.js("Build.S.plans.size") == 1
    game.press("e", 100)
    assert game.js(PLACE) == [x + 1, y, 2, False, True, False]          # ...holds the one over it: whole
    game.press(" ", 120)
    assert game.js("[...Build.S.plans.values()].map((j) => j.z).sort()") == [1, 2]
    assert not game.errors


def test_stairs_with_nothing_higher_beside_them_are_dotted_and_silent(game):
    game.clear_area(8)
    x, y = game.pos()
    game.give(stairs=4)
    game.hold_item("stairs")
    game.face(1, 0)
    game.press("z")
    game.wait("Build.on", 3000)
    h = game.js("Build.hint(Build.S.at)")
    assert h["far"] is True and h["text"] == "", h
    d = game.js(PLACE)
    assert d == [x + 1, y, 1, True, False, True], (d, h)                 # the cell its first step would fill: dotted
    game.js("$('toast').style.display = 'none'")                        # (the welcome, still up: as above)
    game.press(" ", 120)
    assert game.js("Build.S.plans.size") == 0 and game.toast() == ""
    assert not game.errors


def test_pointing_at_a_block_s_west_side_places_west_of_it_and_its_ghost_shows_its_side(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    g.stamp(3, 0, ["."], levels=["1"])                                   # a block of earth, three east of you
    g.give(dirt=4)
    g.hold_item("dirt")
    g.press("z")
    g.wait("Build.on", 3000)
    r = g.js(POINT, [x + 3.03, y + .5, .5])                              # its west side, the one turned to you
    assert [r["x"], r["y"], r["side"]] == [x + 3, y, "W"], r
    assert r["hint"]["ok"] and r["hint"]["at"] == {"x": x + 2, "y": y} and r["hint"]["z"] == 1, r["hint"]
    assert [x + 2, y, 1, "place", True, False] in r["drew"], r["drew"]     # the box west of it, whole
    assert [r["ghost"]["x"], r["ghost"]["z"]] == [x + 2, 1], r["ghost"]
    r = g.js(POINT, [x + 3.5, y + .5, 1])                                # its top: on top of it, as ever
    assert r["side"] == "T" and r["hint"].get("at") is None and r["hint"]["z"] == 2, r
    r = g.js(POINT, [x + 3.03, y + .5, .5])
    g.js("(() => { const p = HdLook.screenOf(%s, %s, .5); for (const t of ['mousedown', 'mouseup']) cv.dispatchEvent(new MouseEvent(t, {clientX: p[0], clientY: p[1], button: 0, bubbles: true})); return 1; })()" % (x + 3.03, y + .5))
    g.wait(f"topAt({x + 2}, {y}) === 1 && !Build.S.plans.size && !myAction", 20000)
    assert g.js(f"topAt({x + 3}, {y})") == 1 and not g.errors


def test_the_pointer_on_a_wall_s_top_is_on_the_wall_and_its_box_is_drawn(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    g.stamp(-1, -3, ["WWW"])                                             # a wall, three north of you
    g.rest()
    g.press("z")
    g.wait("Build.on", 3000)
    r = g.js(POINT, [x + .5, y - 3 + .3, 1])                             # on the wall's top, near its back (the ray went on to the ground behind it)
    assert [r["x"], r["y"]] == [x, y - 3], r
    assert [x, y - 3, 1, "break", True, False] in r["drew"], r["drew"]
    assert "Nothing holds" not in g.actions() and not g.errors
