"""A body's place, frame by frame, pinned (body_place.js): for each way a body moves (a walk down steps, a hop, a jump
through the air on the level, up a step and over a gap, a fall, a ladder, a swim, a boat) the record BodyPlace.of(you)
over a scripted move is compared with a saved trace (body_traces.json): z, ground, mode, air, line, tx, ty (from where
you stood), fx, fy.
The safety net for moving each mode's working-out into BodyPlace: a change of one number in one frame fails here.

The move is played on the page's own code with nothing left to chance: the land laid out first, then, in ONE call, the
page's clock set by hand (a frame is 1/60 s), its frame loop driven by hand, the keys sent as events, and nothing heard
from the world meanwhile (the call does not yield: no tick, no answer; what is asked of the world is not answered,
and the walk's wait for the world is off). So the same code gives the same trace, on any machine, at any load.

BODY_TRACES=write: the traces are written, not compared (after a change that is meant: say why in the commit)."""

import json
import os
from pathlib import Path

import home
import pytest

TRACES = Path(__file__).with_name("body_traces.json")
WRITE = os.environ.get("BODY_TRACES") == "write"
pytestmark = pytest.mark.realtime      # (the page's clock is set by hand here: not the tests' fast one)

# steps: [frames, keys to press down before them, keys to let go before them]; a key: "d", " ", "Shift", ...
PLAY = """(steps) => { const p = ents.get('agent' + myId), x0 = Math.round(p.x), y0 = Math.round(p.y), CODE = {' ': 'Space', Shift: 'ShiftLeft', ArrowUp: 'ArrowUp'}, out = [];
  const T0 = 1e9; let T = T0, f = 0, shift = false; performance.now = () => T;   // (a clock of its own, the same in every run: the first frame's step and every rounding with it)
  lastT = T0 + 1000 / 60 - 100;   // (the first frame 0.1 s, as the traces were made: the jump to T0 was cut at the old cap)
  requestAnimationFrame = () => 0;
  rpc = () => new Promise(() => {}); srv = null;
  const key = (type, k) => { if (k === 'Shift') shift = type === 'keydown'; dispatchEvent(new KeyboardEvent(type, {key: k, code: CODE[k] || 'Key' + k.toUpperCase(), shiftKey: shift, bubbles: true, cancelable: true})); };
  const r = (v) => Math.round(v * 1000) / 1000;
  for (const [n, down, up] of steps) { for (const k of up || []) key('keyup', k); for (const k of down || []) key('keydown', k);
    if (!f && walking) walking.off = lastT;   // (the first frame's 0.1 s walked whole, as the traces were made: a key down since its start)
    for (let i = 0; i < n; i++) { T = T0 + ++f * 1000 / 60; frame(T); const b = BodyPlace.of(p); out.push([r(b.z), r(b.ground), b.mode, b.air ? 1 : 0, r(b.line), b.tx - x0, b.ty - y0, b.fx, b.fy]); } }
  return out; }"""


@pytest.fixture(autouse=True)
def place(game):
    """Every move on the same land: the HD tests' place (home.py), the meadow laid out 16 tiles round (a move runs 15
    tiles on; where the player woke, the land a test before had laid out lay in its way: another trace)."""
    x, y = home.PLACE
    game.rpc("dev_teleport", x=x, y=y); game.arrive()
    game.clear_area(16)
    game.rpc("dev_teleport", x=x, y=y); game.arrive()
    game.face(0, 1)                      # (a teleport turns you the way it took you: from wherever you woke)


def play(game, name, steps):
    game.rest()
    got = game.js(PLAY, steps)
    saved = json.loads(TRACES.read_text()) if TRACES.exists() else {}
    if WRITE:
        saved[name] = got
        TRACES.write_text("{\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}" for k, v in sorted(saved.items())) + "\n}\n")
        return got
    want = saved.get(name)
    assert want is not None, f"no trace saved for {name}: BODY_TRACES=write"
    first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), None)
    assert first is None and len(got) == len(want), (name, "first frame that differs", first, got[first] if first is not None else len(got), want[first] if first is not None else len(want))
    return got


def modes(trace):
    return [m for i, m in enumerate(r[2] for r in trace) if i == 0 or trace[i - 1][2] != m]


def test_walking_down_steps_of_one_and_two_levels(game):
    x, y = game.pos()
    game.stamp(-1, -1, ["." * 9] * 3, levels=["333211000"] * 3)
    game.rpc("dev_teleport", x=x, y=y, z=3); game.arrive()
    t = play(game, "steps_down", [[70, ["d"]], [20, [], ["d"]]])
    assert t[-1][0] == 0 and t[-1][5] > 3 and "fall" not in modes(t), (t[-1], modes(t))


def test_a_hop_on_the_spot(game):
    t = play(game, "hop", [[5], [40, [" "]], [5, [], [" "]]])
    assert modes(t) == ["walk", "jump", "walk"] and max(r[0] for r in t) >= 1, (modes(t), max(r[0] for r in t))


def test_a_sprint_jump_on_the_level_up_a_step_and_over_a_gap(game):
    x, y = game.pos()
    game.stamp(-1, -1, ["." * 16] * 3, levels=["0000111" + "ddd" + "000000"] * 3)      # flat, a step up, a gap three wide and four deep, flat
    game.rest()
    t = play(game, "jumps", [[12, ["Shift", "d"]], [30, [" "]], [40, [], [" "]], [1, [" "]], [50, [], [" "]], [30, [], ["d", "Shift"]]])
    assert "jump" in modes(t) and max(r[0] for r in t) > 1.5 and t[-1][5] > 6, (modes(t), t[-1])


def test_a_fall_of_five_levels(game):
    x, y = game.pos()
    game.stamp(-1, -1, ["." * 8] * 3, levels=["55500000"] * 3)
    game.rpc("dev_teleport", x=x, y=y, z=5); game.arrive()
    t = play(game, "fall", [[80, ["d"]], [20, [], ["d"]]])
    assert "jump" in modes(t) and t[0][0] == 5 and t[-1][0] == 0, (modes(t), t[0], t[-1])     # (walked off, the jump's own fall through the air: leap.js ledge; it was a fall of its own)


def test_up_a_ladder(game):
    x, y = game.pos()
    game.stamp(-2, -8, ["....."] * 6, levels=["66666"] * 6)
    game.give(ladder=1)
    game.rpc("dev_teleport", x=x, y=y - 1, z=0); game.arrive()
    game.hold_item("ladder"); game.face(0, -1)
    game.press("e", 700)
    game.wait(f"combAt({x}, {y - 2}) === 'l'")
    t = play(game, "ladder", [[85, ["ArrowUp"]], [15, [], ["ArrowUp"]]])
    assert "climb" in modes(t) and t[-1][0] == 6, (modes(t), t[-1])


def test_into_the_water_and_across(game):
    game.stamp(2, -2, ["~~((=="] * 5)
    t = play(game, "swim", [[10], [120, ["d"]], [10, [" "]], [30, [], [" ", "d"]]])
    assert modes(t)[:2] == ["walk", "swim"], modes(t)


def test_in_a_boat(game):
    game.stamp(1, -6, ["~~~~~~"] * 6)
    game.give(boat=1)
    game.rpc("dev_teleport", x=game.pos()[0] + 1, y=game.pos()[1]); game.arrive()
    game.hold_item("boat"); game.face(0, -1)
    game.press("e", 800)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")
    game.wait("meObs.self.sailing && ents.get('agent' + myId).e.sail", 5000)
    t = play(game, "boat", [[10], [20, [" "]], [40, ["ArrowUp"], [" "]], [10, [], ["ArrowUp"]]])
    assert modes(t) == ["boat"], modes(t)
