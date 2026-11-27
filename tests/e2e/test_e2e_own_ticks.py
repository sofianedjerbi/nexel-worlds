"""Your own place on a page that misses the ticks carrying you (#328): the observe every 700 ms (agent.js refresh) does
what such a tick does (walk.js myTick: the world's word, your trail drained by vn, your tile when you stand), so the page
comes to where the world has you, whatever its frames. Counted in observes, not in time."""

import pytest

pytestmark = pytest.mark.e2e

# every tick's word on you dropped from here on (each one counted); and the observes answered counted, those not older
# than the last tick here apart (the ones the page takes: an older one is passed over, agent.js refresh)
DROP = """(() => { window.__dropped = 0; window.__fresh = 0; const tick0 = onTick, rpc0 = rpc;
  onTick = (d) => { d.entities = d.entities.filter((e) => !(e.kind === 'agent' && e.id === myId && ++__dropped)); return tick0(d); };
  rpc = async (op, a) => { const r = await rpc0(op, a); if (op === 'observe' && r && r.ok && !(clock && r.obs.tick < clock.tick)) __fresh++; return r; };
  return 1; })()"""
MINE = "(() => { const p = ents.get('agent' + myId); return {at: [p.tx, p.ty], body: [p.x, p.y], walking: !!walking, pred: !!pred, dropped: __dropped}; })()"


def observed(game, n):
    """Until n more observes the page takes have come (and what the first of them did is done: a frame on)."""
    f0 = game.js("__fresh")
    game.wait(f"__fresh >= {f0 + n}", timeout=15000)


def test_standing_a_tile_from_where_the_world_has_you_the_next_observe_puts_you_there(game):
    game.clear_area(6)
    x, y = game.pos()
    game.js(DROP)
    game.rpc("dev_teleport", x=x + 1, y=y, z=0)          # (a tile east, told in no tick: under the 4 tiles a far move is snapped by)
    observed(game, 1)
    m = game.js(MINE)
    assert m["dropped"] > 0 and m["at"] == [x + 1, y], m                     # your tile: the world's, an observe on
    game.wait(f"(() => {{ const p = ents.get('agent' + myId); return Math.abs(p.x - {x + 1}) < 1e-3 && Math.abs(p.y - {y}) < 1e-3; }})()", timeout=8000)
    assert not game.errors, game.errors                                     # ...and your body on it


def test_walking_with_no_tick_that_has_you_the_page_ends_on_the_worlds_tile(game):
    game.clear_area(8)
    x, y = game.pos()
    game.js(DROP)
    game.hold(["d"], 600)                                                    # a walk east, every tick of it without you
    for _ in range(60):                                                      # (until the world's walk is over: its answer, not a time)
        s = game.server()
        if not s.get("action"):
            break
        game.sleep(100)
    s = game.server()
    observed(game, 1)                                                        # one observe the page takes, after it
    m = game.js(MINE)
    assert m["dropped"] > 0 and s["x"] > x and m["at"] == [s["x"], s["y"]] and not m["walking"] and not m["pred"], (m, s)
    game.wait(f"(() => {{ const p = ents.get('agent' + myId); return Math.abs(p.x - {s['x']}) < 1e-3 && Math.abs(p.y - {s['y']}) < 1e-3; }})()", timeout=8000)
    assert not game.errors, game.errors
