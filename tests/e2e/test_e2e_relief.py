"""Regressions for higher ground drawn higher (relief.js), the world-to-screen lift, smooth fly-ins, no frame waiting
on drawing new ground, caves (a roof like a house's) and pits."""

import json


def terrace(game, h=3, dy=-4, rows=3):
    game.stamp(-2, dy, ["....."] * rows, levels=[str(h) * 5] * rows)


def test_every_layer_is_the_same_step_up(game):
    """Level 1 is raised too: +1 always looks like +1 (it used to be drawn flat, so two +1s looked like a +2)."""
    x, y = game.pos()
    game.stamp(-2, -4, ["....."] * 3, levels=["11111", "22222", "33333"])
    z = game.js("zoom")
    lifts = [game.js(f"liftAt({x}, {y + dy})") for dy in (-2, -3, -4)]
    assert lifts == [18 * z, 12 * z, 6 * z] and game.js(f"liftAt({x}, {y})") == 0


def test_the_camera_centres_on_you_as_drawn(game):
    """Up on a terrace you're drawn higher: the camera follows that, not your raw tile (you were off-centre)."""
    terrace(game, h=3, dy=-1, rows=3)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")
    game.sleep(1200)
    d = game.js("(() => { const p = ents.get('agent' + myId); return [cam.y, p.y - liftOf(p) / TS(), liftOf(p)]; })()")
    assert d[2] > 0 and abs(d[0] - d[1]) < 1e-6


def test_world_to_screen_is_lifted_in_one_place(game):
    """sy(y, x) lifts by the ground there: what stands, drops, dies or is picked up on high ground is drawn there."""
    terrace(game)
    x, y = game.pos()
    r = game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S);
      const sy = (yy, xx) => oy + yy * S - (xx === undefined ? 0 : liftOf({{x: xx, y: yy}}));
      return [sy({y - 3}), sy({y - 3}, {x}), liftAt({x}, {y - 3})]; }})()""")
    assert abs((r[0] - r[1]) - r[2]) < 1e-6 and r[2] > 0
    for f in ("drawEntity", "drawNameplate", "drawLoot"):          # the things in the world go through it
        assert "sy(p.y, p.x)" in game.js(f"{f}.toString()") or "sy(l.y, l.x)" in game.js(f"{f}.toString()")


def test_picked_up_items_fly_smoothly_on_high_ground(game):
    """An item flying to you eases its height (no steps at tile borders), and lands where you're drawn."""
    terrace(game, h=3, dy=-6, rows=6)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 2}}})")
    game.sleep(1200)
    x, y = game.pos()
    ys = game.js(f"""(() => {{
      magnetItems({{x: {x + 2}, y: {y + 3}, items: {{wood: 1}}, name: me}});
      const out = [], d0 = ctx.drawImage; let got = null;
      ctx.drawImage = function (img, ...r) {{ if (r.length === 8) got = r[5]; else if (r.length === 4) got = r[1]; return d0.call(this, img, ...r); }};
      const sx = (v) => v * TS(), sy = (v, w) => v * TS() - (w === undefined ? 0 : liftOf({{x: w, y: v}}));
      for (let i = 0; i < 40; i++) {{ const list = []; drawOrbs(sx, sy, TS(), 1 / 120, list); list.forEach((o) => {{ got = null; o.fx(); if (got !== null) out.push(got); }}); }}
      ctx.drawImage = d0; return out; }})()""")
    steps = [abs(b - a) for a, b in zip(ys, ys[1:])]
    assert len(ys) > 10 and max(steps) < game.js("TS()") * .35, steps


def test_walls_have_no_dark_line_at_their_foot(game):
    """The ink line under high walls looked like a black underline: gone."""
    terrace(game)
    game.sleep(800)
    x, y = game.pos()
    found = game.js(f"""(() => {{ const b = blocks.get(bkey(Math.floor({x} / B), Math.floor({y - 2} / B)));
      buildRelief(b); const c = b.relief.layers[3]; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      for (let i = 0; i < d.length; i += 4) if (d[i + 3] && d[i] === 80 && d[i + 1] === 64 && d[i + 2] === 134) return true;
      return false; }})()""")
    assert found is False


def test_sides_show_a_ledge_per_layer(game):
    """A +3 one tile wide shows earth ledges on both sides, a layer each (the side of a +3 looked like a +1)."""
    game.stamp(-3, -6, [".......", "......."] * 2, levels=["0001000", "0001000", "0003000", "0003000"])
    game.sleep(800)
    x, y = game.pos()
    width = lambda yy: game.js(f"""(() => {{ const b = blocks.get(bkey(Math.floor({x} / B), Math.floor({yy} / B))); buildRelief(b);
      const c = b.relief.layers[1], lx = ({x} - b.bx * B) * 16, ly = ({yy} - b.by * B) * 16 + 8;
      const d = c.getContext('2d').getImageData(lx - 12, ly, 40, 1).data; let n = 0;
      for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; }})()""")
    assert width(y - 3) - width(y - 5) >= 2 * 2 * 3 - 2        # a +3 strip: two ledges of 3 px each side more than a +1


def test_running_into_new_ground_never_stalls_a_frame(game):
    """Raised ground and new blocks are drawn in steps within a budget: no frame waits on a whole block (sprinting
    froze the game for 70-130 ms)."""
    x, y = game.pos()
    ms = game.js(f"""new Promise((res) => {{
      for (const b of blocks.values()) b.reliefDirty = true;
      rpc('dev_teleport', {{x: -10, y: 190}});
      const f = []; (function step(t) {{ f.push(t); if (f.length < 150) requestAnimationFrame(step); else res(f); }})(performance.now()); }})""")
    gaps = sorted(b - a for a, b in zip(ms, ms[1:]))
    assert gaps[-1] < 60, gaps[-5:]
    t = game.js("""(() => { let worst = 0; for (const b of blocks.values()) { if (!b.canvas) continue;
      const it = reliefSteps(b); while (true) { const t0 = performance.now(), r = it.next(); worst = Math.max(worst, performance.now() - t0); if (r.done) break; } }
      return worst; })()""")
    assert t < 12, t                                            # a step is small: it fits the frame's budget


def test_a_cave_is_its_mountain_from_outside_and_a_hole_in_it_inside(game):
    """A cave is drawn as the mountain over it, like a house's roof: what's in it is not seen. Walk in and its roof is
    off at once (no fade, no shade over the world): the cave is a hole in the mountain, the mountain stays round it."""
    game.clear_area(6)
    x, y = game.pos()
    game.stamp(-3, -6, [".......", "......."] * 3, levels=["4441444", "4441444", "4441444", "4441444", "4441444", "4441444"],
               roofs=["0003000"] * 5 + ["0000000"])           # a tunnel running north into the hill, its mouth at the south
    game.stamp(-3, 0, ["......."], levels=["1111111"])
    game.spawn("chicken", 0, -5, still=1)
    game.sleep(1200)
    assert game.js(f"levelAt({x}, {y - 3})") == 4 and game.js(f"hiddenAt({x}, {y - 3})")     # outside: its roof
    game.hold(["w"], 900)                                    # in through the mouth
    game.sleep(500)
    assert game.server()["in_cave"] and game.js("caveOpen")
    assert game.js(f"levelAt({x}, {y - 3})") == 1 and game.js(f"levelAt({x - 1}, {y - 3})") == 4   # a hole in the hill
    assert game.js(f"!hiddenAt({x}, {y - 5})")
    assert game.js("ctx.filter") in ("none", "") and not game.js("typeof drawCave !== 'undefined'")
    game.hold(["s"], 900)                                    # and out: its roof is back
    game.sleep(500)
    assert not game.js("caveOpen") and game.js(f"levelAt({x}, {y - 3})") == 4


def test_a_pit_below_sea_level_is_drawn_like_any_hole(game):
    """Digging down at sea level: a pit, drawn lower like any lower ground, the ground round it as it was."""
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.clear_area(3)
    x, y = game.pos()
    game.face(1, 0)
    game.press("x", 2600)                                    # X: down a layer where you stand
    assert game.js(f"floorAt({x}, {y})") == -1 and game.js(f"liftAt({x}, {y})") < 0
    game.act("dig_down", **{"with": "pickaxe"})             # (X now faces the pit's side: it would cut into that)
    game.sleep(2200)
    assert game.js(f"floorAt({x}, {y})") == -2
    game.js("selectItem(null)")
    game.hold(["d"], 200)                                    # two layers up: a wall
    game.sleep(600)
    assert game.server()["x"] == x
