"""A hit farm animal runs away smoothly: drawn at the server's own pace, never falling behind and then snapping ahead
(the cow was drawn slower than the server moved it, then jumped to catch up: it looked like it teleported)."""

def test_a_hit_cow_runs_off_without_jumping(game):
    game.clear_area(8)
    cid = game.spawn("cow", 1, 0, still=10 ** 6)
    game.sleep(600)
    game.face(1, 0)
    game.js("""(() => {                                     // where the cow is drawn, and where the server has it
      window._cow = [];
      (function f() { const c = [...ents.values()].find((q) => q.e && q.e.kind === 'cow');
        if (c) window._cow.push([c.x, c.y, c.tx, c.ty]);
        if (window._cow.length < 220) requestAnimationFrame(f); })(); })()""")
    game.act("attack", target=cid)                             # (fists: it lives and runs; Space would milk it)
    game.sleep(3200)
    rec = game.js("window._cow")
    steps = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(rec, rec[1:])]
    behind = [abs(r[2] - r[0]) + abs(r[3] - r[1]) for r in rec]
    moved = abs(rec[-1][2] - rec[0][2]) + abs(rec[-1][3] - rec[0][3])
    assert moved >= 3, rec[-1]                                 # it did run
    assert max(steps) < .35, max(steps)                        # no frame jumps (a snap is a tile or more)
    assert max(behind) <= 1.2, max(behind)                     # never lagging behind the server
