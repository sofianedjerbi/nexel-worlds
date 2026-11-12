"""The x-ray circle in Chrome (js/xray.js): behind a wall or a mountain, the ground it hides shows through it round you,
and nothing else changes."""

def test_behind_a_mountain_you_are_seen_through_it(game):
    """Behind a wall or a mountain you were cut at its edge: gone. A circle round you is seen through it (xray.js),
    fading toward its edge: you show, on the ground you stand on; out from behind it, the circle goes."""
    game.clear_area(10)
    game.stamp(-5, 1, ["." * 11] * 4, levels=["66666666666"] * 4)   # a wall 6 layers high, right in front (south) of you
    game.sleep(900)
    look = """(() => { const k = DPR, w = Math.round(48 * k), d = ctx.getImageData(Math.round(W / 2 * k) - w / 2, Math.round(H / 2 * k) - w / 2, w, w).data;
      return Array.from(d); })()"""
    assert game.js("xray.a") > .95
    seen = game.js(look)
    game.js("(() => { XRAY.from = 1e9; XRAY.full = 2e9; return 1; })()")          # without it: the wall, and nothing of you
    game.sleep(700)
    assert game.js("xray.a") == 0
    hidden = game.js(look)
    assert sum(1 for a, b in zip(seen[::4], hidden[::4]) if abs(a - b) > 24) > len(seen) / 4 * .3
    game.js("(() => { XRAY.from = .7; XRAY.full = .8; return 1; })()")
    game.hold(["w"], 900)                                              # out from behind it
    game.sleep(600)
    assert game.js("xray.a") == 0
    assert not game.errors


def test_the_circle_shows_only_the_hidden_ground(game):
    """The circle is the ground that rock hides (your height, a step up, or lower), and nothing else: rock that hides
    none stays as it is drawn. (It had painted the rock too: first the walls beside you with a tall face down to the
    cut, walls that are not there; then all of it as a brown footprint, wherever the circle reached.)"""
    game.clear_area(10)
    game.stamp(-4, -3, ["." * 9] * 7, levels=["666606666"] * 4 + ["666666666"] * 3)   # a nook, open to the north: walls west, east and south
    game.sleep(1200)
    x, y = game.pos()
    look = lambda dx, dy: game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S), out = [];
      for (let k = 3; k <= 12; k++) out.push(...ctx.getImageData(Math.round((ox + ({x + dx} + .5) * S) * DPR), Math.round((oy + ({y + dy}) * S + k * zoom) * DPR), 1, 1).data.slice(0, 3));
      return out; }})()""")
    assert game.js("xray.a") > .95
    rock, ground = look(-1, 0), look(0, -2)                   # where the wall beside you stands; the channel behind you
    game.js("(() => { XRAY.from = 9; XRAY.full = 10; return 1; })()")
    game.sleep(700)
    assert game.js("xray.a") == 0
    assert rock == look(-1, 0)                                # rock: the same, circle or not
    assert ground != look(0, -2)                              # hidden ground: the circle showed it
    assert not game.errors


def test_the_circle_never_touches_ground_that_already_shows(game):
    """Behind a wall three layers high: its top covers you and half of the row behind you. The circle shows what it
    covers; a pixel further back, where the ground shows anyway, is the same with the circle or without (it was cut
    out in whole tile columns with a margin: seams and dark lines in open ground and open water)."""
    game.clear_area(10)
    game.stamp(-3, 1, ["." * 7] * 2, levels=["3333333"] * 2)
    game.sleep(1200)
    x, y = game.pos()
    look = lambda dx, dy, rows: game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S), out = [];
      for (const k of {rows}) for (const i of [3, 8, 13]) out.push(...ctx.getImageData(Math.round((ox + {x + dx} * S + i * zoom) * DPR), Math.round((oy + {y + dy} * S + k * zoom) * DPR), 1, 1).data.slice(0, 3));
      return out; }})()""")
    assert game.js("xray.a") > .95
    shows, covered = look(1, -1, [1, 3, 5]), look(1, 0, [4, 8, 12])      # beside you: behind the wall's top edge, and under it
    game.js("(() => { XRAY.from = 9; XRAY.full = 10; return 1; })()")
    game.sleep(700)
    assert game.js("xray.a") == 0
    assert shows == look(1, -1, [1, 3, 5])
    assert covered != look(1, 0, [4, 8, 12])
    assert not game.errors
