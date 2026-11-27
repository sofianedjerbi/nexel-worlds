"""Chaos: random keys and clicks for a while, then everything must still agree."""

import random

KEYS = ["w", "a", "s", "d", "Space", "x", "e", "q", "0", "1", "2", "3", "c", "b", "Escape", "f", "+", "-", "h"]


def test_random_play_keeps_screen_and_server_in_step(game):
    rnd = random.Random(7)
    game.give(wood=20, stone=10, fiber=10, fence=5, seed=3, hoe=1, axe=1, berries=5, torch=1, path=4)
    game.stamp(-4, -4, ["T.b.M.f.Q", ".........", "f..T..b..", ".........", "M...#...T"])
    game.js("""(() => { const o = onTick; window.__tk = []; onTick = (d) => { const me = (d.entities || []).find((e) => e.kind === 'agent' && e.id === myId); __tk.push([d.tick, Math.round(performance.now()), me ? [me.x, me.y] : null]); if (__tk.length > 300) __tk.shift(); return o(d); }; return 1; })()""")   # (each tick: its number, when it came, where it has you (null: not in it); said if the page and the world disagree)
    for i in range(60):
        r = rnd.random()
        if r < .55:
            k = rnd.choice(KEYS)
            hold = rnd.choice([30, 80, 200, 400]) if k in "wasd" else 40
            game.hold(["Shift", k] if rnd.random() < .2 else [k], hold)
        elif r < .85:
            game.page.mouse.click(rnd.randint(200, 1000), rnd.randint(150, 650), button=rnd.choice(["left", "right"]))
        else:
            game.page.mouse.move(rnd.randint(0, 1200), rnd.randint(0, 800))
        game.sleep(rnd.choice([20, 80, 150]))
    game.press("Escape", 200)
    for k in ("w", "a", "s", "d", "Shift"):
        game.page.keyboard.up(k)
    # (until the walk is over and the action done, a click's way there with them, then the screen and the world compared. A sleep
    # of 1.5 s read a click's walk half way on an 83 ms runner: "(7, -11) == (8, -10)", a tile on, as it went)
    game.wait("!walking && !pred && !myAction && (() => { const p = ents.get('agent' + myId); return !!p && p.e.x === Math.round(p.x) && p.e.y === Math.round(p.y); })()", 15000)
    # (and until the world's own answer agrees: the page had caught up with the last place it was told while the world's walk
    # to a click went on, "(-9, -11) == (-9, -10)". 15 s at the most: past that, the screen and the world disagree)
    for _ in range(60):
        here, s = game.pos(), game.server()
        if here == (s["x"], s["y"]):
            break
        game.sleep(250)
    # (the page's side of it, said if it disagrees: what it was last told of you, where it has you, its stop and its trail, the walk)
    mine = game.js("(() => { const p = ents.get('agent' + myId); return p && {e: [p.e.x, p.e.y, p.e.z, p.e.vn], at: [p.x, p.y, p.tx, p.ty], srv, pred, trail: trail.length, walking: !!walking, act: myAction && myAction.tool}; })()")
    ticks = game.js("[__tk.length, __tk.slice(-8), Math.round(performance.now())]")   # (the last ticks: their number, when they came, you in them or not)
    assert game.pos() == (game.server()["x"], game.server()["y"]), (game.server(), mine, "ticks", ticks, "page errors", game.errors[:5])
    m = game.rpc("metrics")["metrics"]
    # the world's tick in its last 250: the usual one is quick, and no key or click made one run away. (A ceiling of 60 ms
    # on the slowest measured the machine: on a runner's two cores, shared with Chrome drawing on the CPU, it was 83.)
    assert m["tick_ms_p50"] < 20 and m["tick_ms_max"] < 250, (m["tick_ms_p50"], m["tick_ms_max"], m["tick_worst"])   # (worst: its step's ms, whether it flushed)

