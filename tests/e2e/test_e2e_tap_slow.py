"""A tap on a page whose frames are slow (#65): one ArrowUp tap, on the runners, took a player three tiles through a
door, the page stopped on the first. Every frame here is made 150 ms long on purpose (a busy wait in it): the tap is a
tile, on the page and in the world."""

import pytest

pytestmark = pytest.mark.e2e

# every frame 150 ms of work; when each key was handled; what the page asked the world; each frame
SLOW = """() => { const raf = requestAnimationFrame; window.__slow = true; window.__keys = []; window.__acts = []; window.__frames = [];
  const spin = (now) => { const t = performance.now(), e = ents.get('agent' + myId); __frames.push([Math.round(now), Math.round(t), e ? +e.y.toFixed(2) : null]); while (performance.now() - t < 150); if (__slow) raf(spin); }; raf(spin);
  for (const ty of ['keydown', 'keyup']) addEventListener(ty, (e) => __keys.push([ty, Math.round(e.timeStamp), Math.round(performance.now())]), true);
  const r = rpc; rpc = (op, a) => { if (op === 'act') __acts.push([Math.round(performance.now()), a.tool, JSON.stringify(a.args || {})]); return r(op, a); }; return 1; }"""


@pytest.mark.realtime
@pytest.mark.parametrize("hold", [90, 160, 230])
@pytest.mark.parametrize("where", ["meadow", "door", "step"])
def test_a_tap_on_a_slow_page_is_one_tile_in_the_world_too(game, where, hold):
    """(held less than a stride, 0.2 s: one tile. test_e2e_climb's tap up a flight of stairs went two tiles, on frames of 83 ms)"""
    game.clear_area(8)
    x, y = game.pos()
    if where == "door":
        game.stamp(-2, -4, ["WWWWW", "WnnnW", "WnnnW", "WW+WW"])          # a room north of you, its door just in front (x, y-1)
    if where == "step":
        game.stamp(-1, -3, ["..."] * 3, levels=["111"] * 3)                # a step up a level just in front, and on beyond it
    game.rest()
    game.js(SLOW)
    game.page.keyboard.down("ArrowUp")
    game.page.wait_for_timeout(hold)
    game.page.keyboard.up("ArrowUp")
    game.wait("!walking && !pred", 8000)
    game.page.wait_for_timeout(600)                                     # (the world's last ticks in)
    game.js("__slow = false")
    s = game.server()
    said = {"page": game.pos(), "world": (s["x"], s["y"]), "from": (x, y), "z": s["z"], "keys": game.js("__keys"), "acts": game.js("__acts"), "frames": game.js("__frames.slice(-12)")}   # (frames: each one's stamp, when it ran, your y)
    assert (s["x"], s["y"]) == (x, y - 1) and game.pos() == (x, y - 1), str(said)   # (a string: pytest cuts a dict short)


@pytest.mark.parametrize("where", ["meadow", "step"])
def test_a_tap_let_go_before_any_frame_is_still_a_tile(game, where):
    """A tap whose key down and key up are both handled before the page draws a frame (a slow page: both came in during
    one long frame) was a stop where you stood: step-90 above, "(-2, -1) == (-2, -2)". The walk goes on for one frame
    and lets go after it: a tile, on a meadow and up a step."""
    game.clear_area(8)
    x, y = game.pos()
    if where == "step":
        game.stamp(-1, -3, ["..."] * 3, levels=["111"] * 3)
    game.rest()
    game.js("""(() => { for (const ty of ['keydown', 'keyup']) dispatchEvent(new KeyboardEvent(ty, {key: 'ArrowUp', code: 'ArrowUp'})); return 1; })()""")
    game.wait("!walking && !pred && !Leap.on()", 8000)
    game.wait(f"(() => {{ const p = ents.get('agent' + myId); return !!p && p.e.x === {x} && p.e.y === {y - 1}; }})()", 8000)
    assert game.pos() == (x, y - 1) and (game.server()["x"], game.server()["y"]) == (x, y - 1)
