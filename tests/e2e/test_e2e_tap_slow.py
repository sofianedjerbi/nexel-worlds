"""A tap on a page whose frames are slow (#65): one ArrowUp tap, on the runners, took a player three tiles through a
door, the page stopped on the first. Every frame here is made 150 ms long on purpose (a busy wait in it): the tap is a
tile, on the page and in the world."""

import pytest

pytestmark = pytest.mark.e2e

# every frame 150 ms of work; when each key was handled; what the page asked the world
SLOW = """() => { const raf = requestAnimationFrame; window.__slow = true; window.__keys = []; window.__acts = [];
  const spin = () => { const t = performance.now(); while (performance.now() - t < 150); if (__slow) raf(spin); }; raf(spin);
  for (const ty of ['keydown', 'keyup']) addEventListener(ty, (e) => __keys.push([ty, Math.round(e.timeStamp), Math.round(performance.now())]), true);
  const r = rpc; rpc = (op, a) => { if (op === 'act') __acts.push([Math.round(performance.now()), a.tool, JSON.stringify(a.args || {})]); return r(op, a); }; return 1; }"""


@pytest.mark.realtime
@pytest.mark.parametrize("where", ["meadow", "door"])
def test_a_tap_on_a_slow_page_is_one_tile_in_the_world_too(game, where):
    game.clear_area(8)
    x, y = game.pos()
    if where == "door":
        game.stamp(-2, -4, ["WWWWW", "WnnnW", "WnnnW", "WW+WW"])          # a room north of you, its door just in front (x, y-1)
    game.js(SLOW)
    game.page.keyboard.down("ArrowUp")
    game.page.wait_for_timeout(90)
    game.page.keyboard.up("ArrowUp")
    game.wait("!walking && !pred", 8000)
    game.page.wait_for_timeout(600)                                     # (the world's last ticks in)
    game.js("__slow = false")
    s = game.server()
    said = {"page": game.pos(), "world": (s["x"], s["y"]), "from": (x, y), "keys": game.js("__keys"), "acts": game.js("__acts")}
    assert (s["x"], s["y"]) == (x, y - 1) and game.pos() == (x, y - 1), said
