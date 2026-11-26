"""A tap of an arrow key in the browser tests: one tile, let go by the page itself."""


def step(game, key):
    """A tap: a tile (the tile it sets out for is walked, and no more) -> where the world has you, (x, y, z)."""
    # (a tap: a tile. Down until the body has set out, then up, let go by the page itself on the first frame that moved
    # you: the tile it set out for is walked, and no more. It was held 90 ms of the game's time with a frame drawn first:
    # frames of 50 to 130 ms on the runners made it longer than a stride, and it went two tiles, "(16, -11, 0) == (15, -11,
    # 2)", up the ladder too. Let go when the walk was set, before a frame had moved you, it was a stop where you stood. Let
    # go by the test once it saw you move, the key was down 620 ms on a page drawing every 130 to 200 ms (the question
    # and the key's answer a frame each): two tiles, "(23, 2, 0)" from 21, and the frames said so)
    at = game.js("(() => { const p = ents.get('agent' + myId); return [p.x, p.y]; })()")
    game.js(TRACE)
    game.js(LET_GO, [key, at])
    game.page.keyboard.down(key)
    game.wait("window.__let", 3000)
    game.page.keyboard.up(key)                                 # (the page has let go already: this one changes nothing)
    game.sleep(550)
    # (the walk over AND the world come to where the screen stopped. It was settle(): a wait that gives up without a word after 3 s; on a busy
    # machine a climb down six layers was not over, and the world's place read was the top's: "(2, -3, 6) != (2, -2, 0)")
    try:
        game.wait("!walking && !pred && (() => { const p = ents.get('agent' + myId); return !!p && p.e.x === Math.round(p.x) && p.e.y === Math.round(p.y) && Math.abs(p.x - p.e.x) + Math.abs(p.y - p.e.y) < .01; })()", 10000)
    except Exception as e:
        raise AssertionError(game.js("(() => { const p = ents.get('agent' + myId); return {walking: !!walking, pred: !!pred, at: [p.x, p.y], world: [p.e.x, p.e.y, p.e.z], myAt, climb: !!Climb.climbOf(p)}; })()")) from e
    s = game.server()
    trace = game.js("(() => { cancelAnimationFrame(window.__tr.raf); return window.__tr.l; })()")
    if (s["x"], s["y"]) != (round(at[0]), round(at[1])) and abs(s["x"] - round(at[0])) + abs(s["y"] - round(at[1])) != 1:
        raise AssertionError(("more than one tile", (s["x"], s["y"], s["z"]), at, trace))
    return s["x"], s["y"], s["z"]


# (the key let go on the frame the body has moved, from the page: a keyup as the browser sends it)
LET_GO = """([key, at]) => { window.__let = false; const f = () => { const p = ents.get('agent' + myId);
  if (p && Math.abs(p.x - at[0]) + Math.abs(p.y - at[1]) > .05) { window.__let = true; dispatchEvent(new KeyboardEvent('keyup', {key, code: key})); } else requestAnimationFrame(f); };
  requestAnimationFrame(f); return 1; }"""
# (each frame of a step, while #65 is open: when it goes two tiles, which frame took the second: [ms, x, y, the tile it is
# entering, the walk's way (0: none), in the air, a stop awaited, the key held])
TRACE = """(() => { if (window.__tr) cancelAnimationFrame(window.__tr.raf); const t = window.__tr = {l: [], t0: performance.now()};
  const f = () => { const p = ents.get('agent' + myId); if (p) t.l.push([Math.round(performance.now() - t.t0), +p.x.toFixed(2), +p.y.toFixed(2), p.tx, p.ty,
    walking ? walking.dir : 0, Leap.on() ? 1 : 0, pred ? 1 : 0, [...keys].filter((k) => KEYDIR[k]).join()]); t.raf = requestAnimationFrame(f); };
  t.raf = requestAnimationFrame(f); return 1; })()"""
