"""Regressions for higher ground drawn higher (relief.js), the world-to-screen lift, smooth fly-ins, no frame waiting
on drawing new ground, caves (a roof like a house's) and pits."""

from test_e2e_digging import LAND, earth


def terrace(game, h=3, dy=-4, rows=3):
    game.stamp(-2, dy, ["....."] * rows, levels=[str(h) * 5] * rows)


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
    """The ink line under high walls looked like a black underline: gone. On the screen a terrace's front, from its
    top edge to a little under its foot, has earth and none of the pack's ink."""
    terrace(game)
    game.sleep(800)
    x, y = game.pos()
    ink, front = game.js(f"""(() => {{ const keep = {{}}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) {{ keep[f] = window[f]; window[f] = () => null; }}
      frame(performance.now()); Object.assign(window, keep); const S = TS(), [ox, oy] = screenOrigin(S);
      const d = ctx.getImageData(Math.round((ox + ({x} - 2) * S) * DPR), Math.round((oy + ({y} - 1 - 26 / 16) * S) * DPR), Math.round(5 * S * DPR), Math.round(28 / 16 * S * DPR)).data; let ink = 0, front = 0;
      for (let i = 0; i < d.length; i += 4) {{ if (d[i] === 80 && d[i + 1] === 64 && d[i + 2] === 134) ink++; if (d[i] > d[i + 1] + 8) front++; }}
      return [ink, front / (d.length / 4)]; }})()""")
    assert ink == 0 and front > .7, (ink, front)


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
    assert game.js(f"surfacesAt({x}, {y - 1})") == [0, 3]
    game.wait("dirtyTiles.length === 0", 8000); game.sleep(400)
    hole, beside = game.js(LAND, [[x, y - 1, 0, 8, 12], [x + 1, y - 1, 0, 8, 12]])
    assert earth(beside) and not earth(hole), (hole, beside)  # the face is open there: the tunnel's floor in it, the hill's front beside it
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


def test_ground_redrawn_while_a_block_is_first_made_is_made_again(game):
    """A block of land is made in steps over a few frames (vox_engine.js work). Its ground redrawn meanwhile (the
    block beside it arriving changes its edge) was only noted for a block that had been built before: on a first
    build the note was dropped, and the block kept land worked out without its neighbour. A tile that changes while
    its block is first being made is made again: what is shown is what is made from nothing afterwards."""
    game.clear_area(8)
    game.stamp(2, -3, ["....."] * 5, levels=["33333"] * 5)
    game.sleep(900)
    x, y = game.pos()
    ty = y - 1 if (y - 1) % 32 else y                        # (a tile that is not in its block's first row: painted before the block is whole)
    made = "Voxels.made(__b) && dirtyTiles.length === 0"
    part = game.js(f"""(() => {{ const t = tileIdx({x + 7}, {ty}), b = t[0], E = Voxels.engine;
      E.forget(() => false);                                   // as if just arrived: nothing of it made
      for (let n = Math.ceil((B * B - t[1]) / 24); n > 0; n--) E.work([{{cx: b.bx, cy: b.by}}], 0);      // its first build under way, that tile painted
      const part = !E.made(b.bx, b.by);
      b.lv[t[1]] = String.fromCharCode(SEA + 3); drawTile({x + 7}, {ty});   // ...and its land turns out higher here
      window.__b = b; return part; }})()""")
    assert part
    game.wait(made, 20000); game.sleep(400)
    tile = f"""(() => {{ const keep = {{}}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) {{ keep[f] = window[f]; window[f] = () => null; }}
      frame(performance.now()); Object.assign(window, keep); const S = TS(), [ox, oy] = screenOrigin(S);
      return [Voxels.engine.faces, Array.from(ctx.getImageData(Math.round((ox + {x + 7} * S) * DPR), Math.round((oy + {ty} * S - shOf(3) * zoom) * DPR), Math.round(S * DPR), Math.round(2.5 * S * DPR)).data).join()]; }})()"""
    shown = game.js(tile)
    game.js("(() => { Voxels.engine.forget(() => false); return 1; })()")
    game.sleep(100); game.wait(made, 20000); game.sleep(400)
    again = game.js(tile)
    assert shown[0] == again[0] and shown[1] == again[1], (shown[0], again[0])
    top = game.js(LAND, [[x + 7, ty, 3, 8, 8], [x + 7, ty, 3, 8, 20]])
    assert not earth(top[0]) and earth(top[1]), top          # (its top, three layers up; its front under it)


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
