"""The way out of the ground, found (web/js/wayout.js): the finder runs here alone under node on the columns of a
simulated world, and what it answers is PLAYED on that simulation with the game's own actions: it has to end under
the open sky. The owner's pocket is the one of tests/test_dig_out.py (their world's own columns)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from helpers import run
from test_dig_out import out, pocket

from megastructure.gen import HIGH, LOW

JS = Path(__file__).parent.parent / "src" / "megastructure" / "web" / "js" / "wayout.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

RUN = r"""
const WayOut = require(process.argv[1]), q = JSON.parse(require("fs").readFileSync(0, "utf8")), cols = q.cols;
const col = (x, y) => cols[x + "," + y] || [0];
const has = (c, z) => { for (let i = 0; i < c.length; i += 2) if (z <= c[i]) return i === 0 || z > c[i - 1]; return false; };
const W = {solid: (x, y, z) => z < q.low + 2 || has(col(x, y), z), top: (x, y) => { const c = col(x, y); return c[c.length - 1]; }, down: () => true};
W.land = (x, y, z) => z > q.low + 2 && W.solid(x, y, z);
let slices = 0, r; const g = WayOut.find(W, q.at, q.opts || {}); for (;;) { const s = g.next(); slices++; if (s.done) { r = s.value; break; } }
console.log(JSON.stringify({...r, moves: WayOut.moves(r.path), slices}));
"""


def runs(c):
    """A column's bits -> the heights where it changes, from the bottom (as the page keeps it: web/js/cells.js)."""
    o, last = [], True
    for z in range(LOW + 1, HIGH + 2):
        solid = z <= HIGH and bool(c >> (z - LOW) & 1)
        if solid != last:
            o.append(z - 1)
            last = solid
    return o


def find(s, a, r=34, **opts):
    cols = {f"{x},{y}": runs(s.world.col(x, y)) for x in range(a.x - r, a.x + r + 1) for y in range(a.y - r, a.y + r + 1)}
    q = {"cols": cols, "at": {"x": a.x, "y": a.y, "z": s.height(a)}, "low": LOW, "opts": opts}
    p = subprocess.run([NODE, "-e", RUN, str(JS)], input=json.dumps(q), capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout)


def play(s, a, moves):
    """The moves, done by the game's own actions, as the keys send them. -> how many"""
    for m in moves:
        h = s.height(a)
        if m["t"] == "step":
            r = run(s, a, "step", {"dir": m["d"]})
            assert r["ok"] and (a.x, a.y, s.height(a)) == (m["x"], m["y"], m["z"]), (m, r, a.x, a.y, s.height(a))
        elif m["key"] == "alt":
            assert run(s, a, "dig_down", {"with": "pickaxe"})["ok"]
        elif m["key"] == "use":
            r = run(s, a, "dig", {"dir": m["d"], "with": "pickaxe"})
            assert r["ok"] and r["cell"] == [m["x"], m["y"], m["z"]], (m, r)
        else:
            assert m["z"] == h + 2
            r = run(s, a, "dig", {"dir": "up", "with": "pickaxe"} if (m["x"], m["y"]) == (a.x, a.y) else {"dir": m["d"], "z": m["z"], "with": "pickaxe"})
            assert r["ok"] and r["cell"] == [m["x"], m["y"], m["z"]], (m, r)
    return len(moves)


def flat(s, a, r=40):
    for y in range(a.y - r, a.y + r + 1):
        for x in range(a.x - r, a.x + r + 1):
            s.world.set(x, y, ground="dirt", block="none", level=0)


def test_the_owners_pocket_two_blocks_then_their_own_stair(world):
    s, a = world
    flat(s, a)
    pocket(s, a)
    for x, z in zip(range(-21, -12), range(-8, 1)):          # (the stair goes on up east to the meadow, as theirs does)
        for zz in range(z + 1, 1):
            s.world.set_cell(x, -3, zz, False)
    a.add("pickaxe")
    r = find(s, a)
    digs = [(m["x"], m["y"], m["z"], m["key"]) for m in r["moves"] if m["t"] == "dig"]
    assert r["trapped"] and not r["out"] and r["blocks"] == 2
    assert digs == [(-26, -3, -11, "up"), (-25, -3, -11, "up")]                          # the tread over your head, the wall at your head's height: no other block
    assert [m["t"] for m in r["moves"][:3]] == ["dig", "dig", "step"] and all(m["d"] == "E" for m in r["moves"][:6])
    n = play(s, a, r["moves"])
    assert out(s, a) and a.hp == 20 and n <= 16, n
    assert r["sky"] >= 3 and r["path"][r["sky"]]["x"] >= -21                           # the daylight: on the stair past the hill, not in the pocket
    again = find(s, a)
    assert again["out"] and again["path"] is None                                        # on the surface: nothing


def test_once_on_the_stair_the_way_is_steps_alone(world):
    s, a = world
    flat(s, a)
    pocket(s, a, at=(-24, -3, -11))
    for x, z in zip(range(-21, -12), range(-8, 1)):
        for zz in range(z + 1, 1):
            s.world.set_cell(x, -3, zz, False)
    r = find(s, a)
    assert not r["trapped"] and r["blocks"] == 0 and r["path"] and all(m["t"] == "step" for m in r["moves"])
    play(s, a, r["moves"])
    assert out(s, a)


def test_a_shaft_a_tile_wide_six_deep_a_stair_of_the_fewest_blocks(world):
    s, a = world
    flat(s, a)
    a.add("pickaxe")
    for _ in range(6):
        assert run(s, a, "dig_down", {"with": "pickaxe"})["ok"]
    r = find(s, a)
    assert r["trapped"] and r["blocks"] == 9, r["blocks"]                                # one for the first step (the sky is over you), two a layer, the last a hop: as tests/test_dig_out.py climbs it
    assert all(m["key"] == "up" for m in r["moves"] if m["t"] == "dig")
    play(s, a, r["moves"])
    assert out(s, a) and s.height(a) == 0 and a.hp == 20
    assert find(s, a)["blocks"] == 0


def test_a_cave_with_a_way_out_on_foot_is_walked_however_long_and_nothing_is_broken(world):
    s, a = world
    flat(s, a)
    x0, y0 = a.x, a.y
    for i in range(0, 13):                                   # a tunnel 12 tiles west at -6, then a stair up east of its far end, back over it
        s.world.set_cell(x0 - i, y0, -5, False)
        s.world.set_cell(x0 - i, y0, -4, False)
    for k in range(1, 7):                                    # the stair: from (x0 - 12, -6) north one row, climbing east
        for zz in range(-6 + k, 1):
            s.world.set_cell(x0 - 12 + k, y0 - 1, zz, False)
    for zz in range(-5, 1):
        s.world.set_cell(x0 - 12, y0 - 1, zz, False)
    a.z = -6
    assert s.height(a) == -6 and s.world.covered(a.x, a.y, -6)
    r = find(s, a)
    assert not r["trapped"] and r["blocks"] == 0 and len(r["moves"]) >= 14               # (two blocks straight up would be "nearer": not while a way is there)
    play(s, a, r["moves"])
    assert out(s, a)


def test_deep_in_solid_rock_it_still_answers_and_in_small_slices(world):
    s, a = world
    flat(s, a)
    for z in range(1, 5):                                    # 20 under a hill, in a cell of your own
        for y in range(a.y - 20, a.y + 21):
            for x in range(a.x - 20, a.x + 21):
                s.world.set_cell(x, y, z, True)
    s.world.set_cell(a.x, a.y, -19, False)
    a.z = -20
    a.add("pickaxe")
    assert s.height(a) == -20
    r = find(s, a, dig=1500)                                 # (the plain search runs out: the hurried one goes up)
    assert r["trapped"] and r["path"] and r["slices"] > 20 and r["n"] < 16000
    play(s, a, r["moves"])
    assert out(s, a) and a.hp == 20
