"""Falling from a height in Chrome (js/jump.js): you come down by your own weight, with the wind, and land in dust."""


def test_a_fall_takes_the_time_of_a_fall_and_lands_in_dust(game):
    """Eight layers down: about a third of a second in the air, faster and faster, the camera with you, the wind
    rising; where you land, dust, and what it cost you shown there (a flash, the number, the ground shaking). It
    was a hop: one arc in the time of a step, and nothing to say it had hurt."""
    game.clear_area(10)
    game.stamp(-1, -1, ["..."] * 3, levels=["888"] * 3)       # a tower eight layers high under you
    game.sleep(700)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    x, y = game.pos()
    game.js("""(() => { window.__f = []; const o = fallOf;
      fallOf = (p, now) => { const r = o(p, now); if (p === ents.get('agent' + myId)) __f.push([now, r ? (r.air ? 1 : 0) : -1, r ? r.body + liftOf(p) / zoom : 0, parts.length, wind ? 1 : 0, cam.y]); return r; }; return 1; })()""")
    game.hold(["d"], 450)
    game.sleep(250)
    assert game.js("fallQuake !== null") and game.js("flashes.has('agent' + myId)")            # it hurt: the ground shakes, you flash
    assert any(f["text"] == "-2.5" for f in game.js("floats"))                                  # (8 layers: 5 over what is safe, half a heart each)
    game.sleep(700)
    rec = game.js("__f")
    air = [r for r in rec if r[1] == 1]
    assert 280 < air[-1][0] - air[0][0] < 440, air[-1][0] - air[0][0]                            # 0.36 s by the fall's own time, not a step's 0.2
    heights = [r[2] for r in air]
    drops = [a - b for a, b in zip(heights, heights[1:])]
    assert heights[0] > 60 and all(d > 0 for d in drops) and drops[-1] > 2.5 * drops[1]          # from 64 px up, faster and faster
    assert max(r[4] for r in air) == 1 and game.js("wind") is None                               # the wind while you fall, gone once you are down
    before, after = max(r[3] for r in rec if r[0] < air[0][0]), max(r[3] for r in rec if r[0] > air[-1][0])
    assert after >= before + 12, (before, after)                                                 # dust where you land
    k = len(air) // 2                                                                            # the camera is on you as you fall
    assert abs(air[k + 1][5] - (y - heights[k] / 16)) < .02                                      # (each frame's is read at the start of the next)
    assert game.js("fallQuake") is None and game.server()["hp"] < 16
    assert game.pos() == (game.server()["x"], game.server()["y"]) and not game.errors


def test_a_drop_of_two_layers_is_still_a_hop_and_three_a_short_fall(game):
    game.clear_area(10)
    game.stamp(-1, -1, ["..."] * 3, levels=["222"] * 3)
    game.sleep(600)
    x, y = game.pos()
    step = lambda f: game.js(f"(() => {{ const p = {{x: {x + 1} + {f}, y: {y}, tx: {x + 2}, ty: {y}, fx: 1, fy: 0}}; return [fallOf(p, 1000) !== null, jumpOf(p) !== null]; }})()")
    assert step(.6) == [False, True]                           # two layers: the hop's arc
    game.stamp(-1, -1, ["..."] * 3, levels=["333"] * 3)
    game.sleep(600)
    assert step(.3) == [True, True] and step(.6)[0]            # three: a fall (it walks to the edge, then drops)
    assert game.server()["hp"] == 20


def test_dust_shows_on_level_ground_and_not_behind_a_ledge(game):
    """Dust, sparks and splashes behind higher ground aren't drawn. On the level nothing is behind anything: the check
    compared 0 with less than 0 there, and every puff that wasn't on the top line of its tile went unseen."""
    game.clear_area(8)
    x, y = game.pos()
    assert game.js(f"[behindHill({x} + .5, {y} + .85), behindHill({x} + .5, {y} + .2)]") == [False, False]
    game.stamp(-1, 1, ["..."], levels=["111"])                 # a ledge a layer high in front of you: its top covers the lower half of your tile
    game.sleep(500)
    assert game.js(f"[behindHill({x} + .5, {y} + .85), behindHill({x} + .5, {y} + .2)]") == [True, False]
    game.stamp(-1, 1, ["..."], levels=["000"])
    game.sleep(400)
    n = game.js("(() => { parts.length = 0; return 1; })()")
    shown = game.js(f"""(() => {{ burst({x}, {y} + .35, 'dust', 8, {{g: 0, life: 3}}); let n = 0; const f = ctx.fillRect;
      ctx.fillRect = function (...a) {{ if (ctx.fillStyle === PCOL.dust[0] || ctx.fillStyle === PCOL.dust[1]) n++; return f.apply(ctx, a); }};
      return new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {{ ctx.fillRect = f; ok(n); }}))); }})()""")
    assert shown >= 8, shown                                   # the dust is painted
