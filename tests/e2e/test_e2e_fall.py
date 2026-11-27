"""Falling from a height in Chrome (js/jump.js): you come down by your own weight, with the wind, and land in dust."""

import pytest
from clock import FRAME_MS


@pytest.mark.realtime
def test_a_fall_takes_the_time_of_a_fall_and_lands_in_dust(game):
    """Eight layers down: about half a second in the air, faster and faster, the camera with you, the wind
    rising; where you land, dust, and what it cost you shown there (a flash, the number, the ground shaking). It
    was a hop: one arc in the time of a step, and nothing to say it had hurt. Walking off it is the jump's own fall
    now (leap.js dropDue: "weird issues when jumping from high heights": the fall's own eye was put on the ground
    under the edge at once, the body 55 px up the screen in a frame): at the walk's speed, off the edge, by the
    jump's weight (JUMP.g)."""
    game.clear_area(10)
    game.stamp(-1, -1, ["..."] * 3, levels=["888"] * 3); game.rest()       # a tower eight layers high under you
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.js("""(() => { window.__f = []; const o = Leap.frame;
      Leap.frame = (p, dt, now) => { o(p, dt, now); const L = Leap.state; __f.push([now, L ? 1 : 0, L ? L.z : null, parts.length, wind ? 1 : 0, HdLook.level[2]]); };
      window.__hurt = []; const h = fallHurts; fallHurts = (p, now, mine) => { if (BodyPlace.state(p).hurt) __hurt.push(now); h(p, now, mine); }; return 1; })()""")
    g = game.js("JUMP.g")
    T = (2 * 8 / g) ** .5 * 1000                                                                 # ms in the air from eight layers, by the jump's weight
    # (walked off the edge: the key held until you are in the air. It was held 450 ms, a tile and a half at the walk's
    # pace: on a machine whose first frames are slow you stopped on the tower's last tile, and nothing fell)
    game.page.keyboard.down("d")
    game.wait("__f.some((r) => r[1] === 1)", timeout=5000)
    game.page.keyboard.up("d")
    game.wait("fallQuake !== null && flashes.has('agent' + myId)", timeout=3000)                # it hurt: the ground shakes, you flash
    assert any(f["text"] == "-2.5" for f in game.js("floats"))                                  # (8 layers: 5 over what is safe, half a heart each)
    # (until the world's own `fall` event is in: it clears what your landing told (state.js), and must add no second hurt.
    #  It was 1.2 s, the event later than that on a loaded runner)
    game.wait("BodyPlace.state(ents.get('agent' + myId)).told === null", 8000)
    game.wait("fallQuake === null && wind === null", 8000)                                       # (the shake and the wind over, by the game's own time)
    game.still()
    rec = game.js("__f")
    down = next(r[0] for r in rec if r[1] == 0 and any(q[1] == 1 for q in rec if q[0] < r[0]))     # the frame you are down
    hurt = game.js("__hurt")
    assert len(hurt) == 1 and hurt[0] - down < 40, (hurt, down)                                  # what it cost shown as you land, once: it came most of a second after (the world's word, then 0.7 s more)
    # (the game's time of a frame: the frame's own, FRAME_MS at the most, render.js update. Judged by frames of 17 ms on the
    # Mac; on a machine drawing on the CPU (the runners) a fall is five frames of 70 to 180 ms, which a frame's drops
    # compared one to the next cannot tell from a slow one)
    game_ms = lambda i: min(rec[i][0] - rec[i - 1][0], FRAME_MS)
    first = next(i for i, r in enumerate(rec) if r[1] == 1 and r[2] < 8 - 1e-6)                 # (off the edge: under the tower's top)
    last = rec.index(next(r for r in rec[first:] if r[1] == 0))                                 # the frame you are down
    air = rec[first:last]
    flown = sum(game_ms(i) for i in range(max(first, 1), last + 1))                                   # from the frame on the edge to the one on the ground
    frame = max(game_ms(i) for i in range(max(first, 1), last + 1))
    assert .78 * T - frame < flown < 1.22 * T + frame, (flown, T, frame)                        # by the fall's own time, not a step's 0.2
    heights = [r[2] for r in air]
    speeds = [(rec[i - 1][2] - rec[i][2]) / game_ms(i) for i in range(first + 1, last)]          # (layers a ms of the game's time, frame by frame)
    assert heights[0] > 7.5 and all(b > a for a, b in zip(speeds, speeds[1:])) and speeds[-1] > 2 * speeds[0], (heights, speeds)   # from eight levels up, faster and faster
    assert max(r[4] for r in air) == 1 and game.js("wind") is None                               # the wind while you fall, gone once you are down
    assert any(r[1] == 1 for r in rec) and max(r[3] for r in rec) >= 12                         # dust where you land
    k = len(air) // 2
    assert air[k][5] - heights[k] < 2.5, (air[k], heights[k])                                    # the camera with you as you fall: a level or two behind at the most, never left on the tower
    assert game.js("fallQuake") is None and game.server()["hp"] < 16
    assert game.pos() == (game.server()["x"], game.server()["y"]) and not game.errors


def test_a_drop_of_two_layers_is_still_a_hop_and_three_a_short_fall(game):
    game.clear_area(10)
    game.stamp(-1, -1, ["..."] * 3, levels=["222"] * 3); game.rest()
    x, y = game.pos()
    step = lambda f: game.js(f"(() => {{ const p = {{x: {x + 1} + {f}, y: {y}, tx: {x + 2}, ty: {y}, fx: 1, fy: 0}}; return [fallOf(p, 1000) !== null, jumpOf(p) !== null]; }})()")
    assert step(.6) == [False, True]                           # two layers: the hop's arc
    game.stamp(-1, -1, ["..."] * 3, levels=["333"] * 3); game.rest()
    assert step(.3) == [True, True] and step(.6)[0]            # three: a fall (it walks to the edge, then drops)
    assert game.server()["hp"] == 20
