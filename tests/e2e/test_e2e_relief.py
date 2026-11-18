"""Regressions for higher ground drawn higher (relief.js), the world-to-screen lift, smooth fly-ins, no frame waiting
on drawing new ground, caves (a roof like a house's) and pits."""

import json


def terrace(game, h=3, dy=-4, rows=3):
    game.stamp(-2, dy, ["....."] * rows, levels=[str(h) * 5] * rows)


# a block's raised ground alone (what is shown, b.relief.flat, has its ground under it: relief.js)
RAISED = "((b) => { const it = reliefSteps({x: b.bx * B, y: b.by * B, w: B, h: B, solid: b.solid}, b.px); let r; do r = it.next(); while (!r.done); return r.value.flat; })"

def test_every_layer_is_the_same_step_up(game):
    """Level 1 is raised too: +1 always looks like +1 (it used to be drawn flat, so two +1s looked like a +2)."""
    x, y = game.pos()
    game.stamp(-2, -4, ["....."] * 3, levels=["11111", "22222", "33333"])
    z = game.js("zoom")
    lifts = [game.js(f"liftAt({x}, {y + dy})") for dy in (-2, -3, -4)]
    assert lifts == [24 * z, 16 * z, 8 * z] and game.js(f"liftAt({x}, {y})") == 0


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
    for f in ("drawBody", "drawNameplate", "drawLoot"):            # the things in the world go through it (a body: through bodyY, which is sy and where a body stands in its tile)
        src = game.js(f"{f}.toString()")
        assert "bodyY(p, sy)" in src or "sy(l.y, l.x)" in src
    assert "liftOf(p)" in game.js("bodyY.toString()")              # (a body: lifted with the ground it stands on, which over a room is a floor: floors.js)


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
      buildRelief(b); const c = {RAISED}(b); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      for (let i = 0; i < d.length; i += 4) if (d[i + 3] && d[i] === 80 && d[i + 1] === 64 && d[i + 2] === 134) return true;
      return false; }})()""")
    assert found is False


def test_sides_show_a_ledge_per_layer(game):
    """A +3 one tile wide shows earth ledges on both sides, a layer each (the side of a +3 looked like a +1)."""
    game.stamp(-3, -6, [".......", "......."] * 2, levels=["0001000", "0001000", "0003000", "0003000"])
    game.sleep(800)
    x, y = game.pos()
    width = lambda yy: game.js(f"""(() => {{ const b = blocks.get(bkey(Math.floor({x} / B), Math.floor({yy} / B))); buildRelief(b);
      const c = {RAISED}(b), lx = ({x} - b.bx * B) * 16, ly = ({yy} - b.by * B) * 16 + 8 + b.relief.up - shOf(1);   // (level 1's row in the block's raised picture)
      const d = c.getContext('2d').getImageData(lx - 12, ly, 40, 1).data; let n = 0;
      for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; }})()""")
    high, low = width(y - 3), width(y - 5)
    assert high - low >= 2 * 2 * 3 - 2, (high, low, game.js('dirtyTiles.length'))   # a +3 strip: two ledges of 3 px each side more than a +1


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
      const it = blockRelief(b); while (true) { const t0 = performance.now(), r = it.next(); worst = Math.max(worst, performance.now() - t0); if (r.done) break; } }
      return worst; })()""")
    assert t < 12, t                                            # a step is small: it fits the frame's budget


def test_a_cave_is_its_mountain_from_outside_and_seen_through_it_inside(game):
    """A cave is drawn as the mountain over it, like a house's roof: what's in it is not seen. Walk in and you are
    seen through the mountain, as anywhere you are hidden (xray.js): you, the cave, what is in it; the mountain stays
    round it, and no shade goes over the world."""
    game.clear_area(6)
    x, y = game.pos()
    game.stamp(-3, -6, [".......", "......."] * 3, levels=["4441444", "4441444", "4441444", "4441444", "4441444", "4441444"],
               roofs=["0003000"] * 5 + ["0000000"])           # a tunnel running north into the hill, its mouth at the south
    game.stamp(-3, 0, ["......."], levels=["1111111"])
    game.spawn("chicken", 0, -5, still=1)
    game.sleep(1200)
    assert game.js(f"levelAt({x}, {y - 3})") == 4 and game.js(f"hiddenAt({x}, {y - 3})")     # outside: its roof
    game.js("""window.seen = []; (function f() { const p = ents.get('agent' + myId);
      window.seen.push([liftOf(p), unseen(p)]); requestAnimationFrame(f); })()""")
    game.hold(["w"], 900)                                    # in through the mouth
    game.wait("xray.a > .95", 8000)
    assert game.server()["in_cave"] and game.js(f"seenUnder({x}, {y - 3})") == 1
    # ...and all the way in you stayed on the ground, in sight (never drawn climbing its roof, or under it)
    assert game.js("Math.max(...window.seen.map((s) => s[0])) - Math.min(...window.seen.map((s) => s[0]))") < .5 and not game.js("window.seen.some((s) => s[1])")
    assert game.js(f"standAt({x}, {y - 3})") == 1 and game.js(f"standAt({x - 1}, {y - 3})") == 4   # shown through the hill
    assert game.js(f"!hiddenAt({x}, {y - 5})")
    assert game.js("ctx.filter") in ("none", "") and not game.js("typeof drawCave !== 'undefined'")
    game.hold(["s"], 900)                                    # and out: its roof is back
    game.sleep(500)
    assert game.js("Math.max(...window.seen.map((s) => s[0])) - Math.min(...window.seen.map((s) => s[0]))") < .5 and not game.js("window.seen.some((s) => s[1])")
    assert game.js("xray.a < .01") and game.js(f"[standAt({x}, {y - 3}), hiddenAt({x}, {y - 3})]") == [4, True]


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


def test_walking_off_a_cliff_you_fall_and_a_long_fall_hurts(game):
    """Off an edge you come down on the ground below, on screen as on the server; 6 layers cost a heart and a half."""
    game.clear_area(6)
    x, y = game.pos()
    game.stamp(-2, -6, ["....."] * 3, levels=["66666"] * 3)
    game.rpc("dev_teleport", x=x, y=y - 4)                   # up on it (dev_teleport: on top)
    game.sleep(900)
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
    game.stamp(-2, -3, ["....."] * 3, levels=["33333"] * 3)  # a hill 3 high, its south face in front of you
    game.sleep(600)
    game.face(0, -1)
    assert "Dig into the hill" in game.actions()
    game.press(" ", 1500)
    assert game.js(f"surfacesAt({x}, {y - 1})") == [0, 3] and game.js(f"shownVoids({x}, {y - 1}, 0, 1)") == [[1, 1]]
    game.js("selectItem(null)")
    game.hold(["w"], 300)
    game.sleep(600)
    s = game.server()
    assert s["in_cave"] and s["z"] == 0 and (s["x"], s["y"]) == (x, y - 1) and game.js(f"seenUnder({x}, {y - 1})") == 0


def test_a_frame_paints_the_screen_a_few_times_over_not_ten(game):
    """What a weak GPU pays for is paint. Over water every layer of it (bottom, wobble, two nets of light, tint, two
    of waves) was painted at the screen's size, and the old water under every block besides: ten screens of paint a
    frame. The water is put together small and blown up once (water.js); a block's raised ground and its caves are
    painted only where they have something."""
    game.clear_area(10)
    game.stamp(-16, -10, ["~" * 33] * 21)
    game.sleep(1500)
    screens = game.js("""(() => { const scr = cv.width * cv.height; let px = 0;
      const area = (x, y, w, h) => { const m = ctx.getTransform(), x0 = m.a * x + m.e, y0 = m.d * y + m.f, x1 = m.a * (x + w) + m.e, y1 = m.d * (y + h) + m.f;
        return Math.max(0, Math.min(Math.max(x0, x1), cv.width) - Math.max(Math.min(x0, x1), 0)) * Math.max(0, Math.min(Math.max(y0, y1), cv.height) - Math.max(Math.min(y0, y1), 0)); };
      const d = ctx.drawImage, raf = window.requestAnimationFrame;
      ctx.drawImage = function (img, ...a) { const k = a.length >= 8 ? 4 : 0; px += area(a[k], a[k + 1], a.length >= 4 ? a[k + 2] : img.width, a.length >= 4 ? a[k + 3] : img.height); return d.call(ctx, img, ...a); };
      ctx.fillRect = function (x, y, w, h) { px += area(x, y, w, h); return CanvasRenderingContext2D.prototype.fillRect.call(ctx, x, y, w, h); };
      window.requestAnimationFrame = () => 0;
      try { frame(performance.now()); } finally { window.requestAnimationFrame = raf; ctx.drawImage = d; delete ctx.fillRect; }
      return px / scr; })()""")
    assert 1.5 < screens < 4.5, screens                      # (it was 9.8 over the sea)
    assert not game.errors


def test_ground_redrawn_while_a_block_is_first_built_builds_it_again(game):
    """A block's raised ground is built in steps over a few frames. Its ground redrawn meanwhile (the block beside
    it arriving changes its edge) was only noted for a block that had been built before: on a first build the note
    was dropped, and the block kept land worked out without its neighbour (a column of flat ground along that edge)."""
    game.clear_area(8)
    game.stamp(2, -3, ["....."] * 5, levels=["33333"] * 5)
    game.sleep(900)
    x, y = game.pos()
    game.js(f"""(() => {{ const t = tileIdx({x + 7}, {y - 1}), b = t[0];
      b.relief = null; b.reliefGen = blockRelief(b); b.reliefGen.next();      // as if just arrived: its first build under way
      b.lv[t[1]] = String.fromCharCode(SEA + 3); drawTile({x + 7}, {y - 1});   // ...and its land turns out higher here
      window.__b = b; return 1; }})()""")
    game.sleep(900)
    sig = "(() => { const c = __b.relief.flat; return c ? Array.from(c.getContext('2d').getImageData(0, 0, c.width, c.height).data).reduce((h, v) => (h * 31 + v) | 0, 7) : 0; })()"
    shown = game.js(sig)
    game.js("(() => { buildRelief(__b); return 1; })()")
    assert shown == game.js(sig) and shown != 0


def test_told_it_missed_events_the_page_asks_for_its_land_again(game):
    """(The server says `resync` to a page whose queue overflowed: a flood of tile changes.)"""
    game.clear_area(6)
    x, y = game.pos()
    game.js(f"(() => {{ const t = tileIdx({x + 2}, {y}); t[0].comb[t[1]] = 'T'; return 1; }})()")     # as if we'd missed a change
    assert game.tile(2, 0) == "T"
    game.js("""(() => { spec.onmessage({data: '{"type":"resync"}'}); return 1; })()""")
    game.sleep(1200)
    assert game.tile(2, 0) != "T"


def test_a_sprite_behind_a_ledge_is_cut_along_the_ledges_own_edge(game):
    """Behind higher ground you are cut at its top edge. That edge is set in a little from the tile's side and rounded
    at a corner: cut straight across the tile (a px under its top), you were gone where the corner lets the ground
    behind it show."""
    game.clear_area(8)
    lv = ["1110000", "1110000", "1110000", "1111000", "1111100", "1111110", "1111111"]   # a ledge west and south of you, its edge in steps
    game.stamp(-3, -2, ["." * 7] * 7, levels=lv)
    game.sleep(1000)
    r = game.js("""(() => { const p = ents.get('agent' + myId), S = TS(), [ox, oy] = screenOrigin(S);
      const sx = (x) => ox + x * S, sy = (y, x) => oy + y * S - (x === undefined ? 0 : liftOf({x, y})), strips = [];
      ctx.rect = function (x, y, w, h) { strips.push([x, y + h]); return CanvasRenderingContext2D.prototype.rect.call(ctx, x, y, w, h); };
      const cut = clipBehind(p, sx, sy, S); if (cut) ctx.restore(); delete ctx.rect;
      const x0 = sx(Math.round(p.x)), foot = sy(Math.round(p.y) + 1);      // your tile's column; the line between you and the tile in front
      return {cut, edge: strips.filter((q) => q[0] > x0 - .01 && q[0] < x0 + S - .01 && q[1] < 5000).map((q) => Math.round((q[1] - foot) / zoom))}; })()""")
    assert r["cut"] and r["edge"]
    assert max(r["edge"]) > -5 and len(set(r["edge"])) > 2, r   # (art px over that line: the ledge is 8 high, and was cut at -7 all the way across; its edge rounds off at the corner)
    assert not game.errors
