"""Chaos: random keys and clicks for a while, then everything must still agree and run smoothly."""

import random

KEYS = ["w", "a", "s", "d", "Space", "x", "e", "q", "0", "1", "2", "3", "c", "b", "Escape", "f", "+", "-", "h"]


def test_random_play_keeps_screen_and_server_in_step(game):
    rnd = random.Random(7)
    game.give(wood=20, stone=10, fiber=10, fence=5, seed=3, hoe=1, axe=1, berries=5, torch=1, path=4)
    game.stamp(-4, -4, ["T.b.M.f.Q", ".........", "f..T..b..", ".........", "M...#...T"])
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
    game.sleep(1500)
    assert game.pos() == (game.server()["x"], game.server()["y"])
    m = game.rpc("metrics")["metrics"]
    assert m["tick_ms_max"] < 60, m


def test_smooth_frames_while_sprinting(game):
    game.js("""(() => { window.__gaps = []; let last = performance.now();
      (function f(n) { __gaps.push(n - last); last = n; if (__gaps.length < 400) requestAnimationFrame(f); })(last); })()""")
    game.hold(["Shift", "d"], 1500)
    game.hold(["Shift", "a"], 1500)
    gaps = sorted(game.js("__gaps.slice(5)"))
    p95 = gaps[int(len(gaps) * .95)]
    assert p95 < 34, f"frame gaps p95 {p95:.1f} ms"
