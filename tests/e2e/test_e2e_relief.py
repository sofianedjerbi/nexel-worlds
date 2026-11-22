"""Regressions for higher ground lifted higher (relief.js: the camera on you as drawn), no frame waiting on new
ground, pits, falls, a tunnel dug into a hill, and the land asked for again."""

import pytest


def terrace(game, h=3, dy=-4, rows=3):
    game.stamp(-2, dy, ["....."] * rows, levels=[str(h) * 5] * rows)


def test_every_layer_is_the_same_step_up(game):
    """Level 1 is raised too: +1 always looks like +1 (it used to be drawn flat, so two +1s looked like a +2)."""
    x, y = game.pos()
    game.stamp(-2, -4, ["....."] * 3, levels=["11111", "22222", "33333"])
    z = game.js("zoom")
    lifts = [game.js(f"liftAt({x}, {y + dy})") for dy in (-2, -3, -4)]
    assert lifts == [48 * z, 32 * z, 16 * z] and game.js(f"liftAt({x}, {y})") == 0      # (a level is a cube: 16 art px)


def test_the_camera_centres_on_you_as_drawn(game):
    """Up on a terrace you're drawn higher: the camera follows that, not your raw tile (you were off-centre)."""
    terrace(game, h=3, dy=-1, rows=3)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")
    game.sleep(1200)
    d = game.js("(() => { const p = ents.get('agent' + myId); return [cam.y, p.y - liftOf(p) / TS(), liftOf(p)]; })()")
    assert d[2] > 0 and abs(d[0] - d[1]) < 1e-6


@pytest.mark.realtime
def test_running_into_new_ground_never_stalls_a_frame(game):
    """New land is made in steps within a budget (voxels.js work): no frame waits on a whole block (sprinting froze the
    game for 70-130 ms). (How long a step is: test_e2e_land.py.)"""
    x, y = game.pos()
    ms = game.js(f"""new Promise((res) => {{
      Voxels.engine.forget(() => false);                       // (the land round you to be made again too, as blocks)
      rpc('dev_teleport', {{x: -10, y: 190}});
      const f = []; (function step(t) {{ f.push(t); if (f.length < 150) requestAnimationFrame(step); else res(f); }})(performance.now()); }})""")
    gaps = sorted(b - a for a, b in zip(ms, ms[1:]))
    assert gaps[-1] < 60, gaps[-5:]


def test_a_pit_below_sea_level_is_drawn_like_any_hole(game):
    """Digging down at sea level: a pit, drawn lower like any lower ground, the ground round it as it was."""
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.clear_area(3)
    x, y = game.pos()
    game.face(1, 0)
    game.act("dig_down", **{"with": "pickaxe"})              # down a layer where you stand
    game.sleep(2200)
    assert game.js(f"floorAt({x}, {y})") == -1 and game.js(f"liftAt({x}, {y})") < 0
    game.act("dig_down", **{"with": "pickaxe"})             # (X now faces the pit's side: it would cut into that)
    game.sleep(2200)
    assert game.js(f"floorAt({x}, {y})") == -2
    game.js("selectItem(null)")
    game.hold(["d"], 200)                                    # two layers up: a wall
    game.sleep(600)
    assert game.server()["x"] == x


def test_walking_off_a_cliff_you_fall_and_a_long_fall_hurts(game):
    """Off an edge you come down on the ground below, on screen as on the server; 6 layers cost a heart and a half."""
    game.clear_area(6)
    x, y = game.pos()
    game.stamp(-2, -6, ["....."] * 3, levels=["66666"] * 3)
    game.rpc("dev_teleport", x=x, y=y - 4); game.arrive()                   # up on it (dev_teleport: on top)
    assert game.server()["z"] == 6 and game.js("myAt.z") == 6
    game.rpc("dev_needs", hp=20, hunger=17)                    # (not healing by itself)
    hp = game.server()["hp"]
    game.hold(["s"], 420)                                    # off its south edge
    game.sleep(900)
    s = game.server()
    assert s["z"] == 0 and s["hp"] == hp - 3 and (s["x"], s["y"]) == game.pos() and s["y"] >= y - 3
    assert game.js("myAt.z") == 0 and game.js("liftOf(ents.get('agent' + myId))") == 0


def test_a_pickaxe_cuts_a_tunnel_into_a_wall(game):
    """Digging toward a wall takes out the block in front of you: under a hill two layers high or more, a tunnel
    you walk into, which opens at once and shows on the hill's face from outside."""
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.clear_area(4)
    x, y = game.pos()
    game.stamp(-2, -3, ["....."] * 3, levels=["33333"] * 3); game.rest()  # a hill 3 high, its south face in front of you
    game.face(0, -1)
    assert "Dig into the hill" in game.actions()
    game.press("x", 1500)
    assert game.js(f"surfacesAt({x}, {y - 1})") == [0, 3]
    game.rest()
    game.js("selectItem(null)")
    game.hold(["w"], 300)
    game.sleep(600)
    s = game.server()
    assert s["in_cave"] and s["z"] == 0 and (s["x"], s["y"]) == (x, y - 1)


def test_told_it_missed_events_the_page_asks_for_its_land_again(game):
    """(The server says `resync` to a page whose queue overflowed: a flood of tile changes.)"""
    game.clear_area(6)
    x, y = game.pos()
    game.js(f"(() => {{ const t = tileIdx({x + 2}, {y}); t[0].comb[t[1]] = 'T'; return 1; }})()")     # as if we'd missed a change
    assert game.tile(2, 0) == "T"
    game.js("""(() => { spec.onmessage({data: '{"type":"resync"}'}); return 1; })()""")
    game.sleep(1200)
    assert game.tile(2, 0) != "T"
