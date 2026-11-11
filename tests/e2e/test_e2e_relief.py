"""Regressions for higher ground drawn higher (relief.js), the world-to-screen lift, smooth fly-ins, no frame waiting
on drawing new ground, cave entrances, and the underground view staying cheap."""

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


def test_a_hole_shows_the_tunnels_leaving_it(game):
    """Surface holes show where the floor below goes on under the ground: shade toward that side."""
    x, y = game.pos()
    L = 1000000
    game.clear_area(4)
    game.rpc("dev_stamp", x=x + 2 + L, y=y - 2, rows=["R", "R", "R"])    # below first: the tunnel going east...
    game.rpc("dev_stamp", x=x + 2 + L, y=y, rows=["-"])
    game.rpc("dev_stamp", x=x + 3 + L, y=y, rows=["---"])
    game.stamp(2, 0, ["O"])                                            # ...then the hole over its west end
    game.sleep(1500)
    dark = game.js(f"""(() => {{ const b = blocks.get(bkey(Math.floor({x + 2} / B), Math.floor({y} / B))), lx = ({x + 2} - b.bx * B) * 16, ly = ({y} - b.by * B) * 16;
      const d = b.ctx.getImageData(lx + 13, ly + 8, 3, 1).data; return (d[0] + d[1] + d[2]) / 3; }})()""")
    assert dark < 140                                           # the east edge of the hole is in shade


def test_underground_draws_without_canvas_filters(game):
    """The level above was faded with a canvas filter: 5x slower. No filter in the frame."""
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.press("x", 2600)
    assert game.server()["depth"] == 1
    game.sleep(500)
    assert game.js("ctx.filter") in ("none", "")
