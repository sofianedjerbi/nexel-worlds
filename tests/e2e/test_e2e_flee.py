"""A hit farm animal runs away smoothly: drawn at the server's own pace, never falling behind and then snapping ahead
(the cow was drawn slower than the server moved it, then jumped to catch up: it looked like it teleported)."""

import math


def test_a_hit_cow_runs_off_without_jumping(game):
    game.clear_area(8)
    cid = game.spawn("cow", 1, 0, still=10 ** 6)
    game.sleep(600)
    game.face(1, 0)
    game.js("""(() => {                                     // where the cow is drawn, and where the server has it
      window._cow = [];
      (function f(now) { const c = [...ents.values()].find((q) => q.e && q.e.kind === 'cow');
        if (c && now !== undefined) window._cow.push([c.x, c.y, c.tx, c.ty, now]);
        if (window._cow.length < 220) requestAnimationFrame(f); })(); })()""")
    game.act("attack", target=cid)                             # (fists: it lives and runs; Space would milk it)
    game.sleep(3200)
    rec = game.js("window._cow")
    # how fast it is drawn going, tiles a second of the frame's own time (render.js: a frame moves a body by its time,
    # 0.1 s at the most). Its steps a frame were 0.35 at most at 10 frames a second, a slow machine's: a step's size is
    # the machine's; its speed is the game's
    speeds = [math.hypot(b[0] - a[0], b[1] - a[1]) / min(.1, (b[4] - a[4]) / 1000) for a, b in zip(rec, rec[1:]) if b[4] > a[4]]
    behind = [abs(r[2] - r[0]) + abs(r[3] - r[1]) for r in rec]
    moved = abs(rec[-1][2] - rec[0][2]) + abs(rec[-1][3] - rec[0][3])
    assert moved >= 3, rec[-1]                                 # it did run
    assert max(speeds) < 20, max(speeds)                        # no frame jumps: it runs a tile every FLEE_STRIDE, 3.3 tiles a second, faster for a frame as the world sets its pace (13); a snap goes at 20 and more (render.js `far`). A step of .35 at 60 frames a second was 21
    # never lagging behind the server: never so far that it is put there (render.js `far`, 2.5 tiles: the snap this was),
    # about a tile on the whole. (Uneven ticks on a busy runner leave it a tile and a half off for a while: render.js)
    assert max(behind) < 2.5 and sorted(behind)[len(behind) // 2] <= 1.2, sorted(behind)[-12:]
