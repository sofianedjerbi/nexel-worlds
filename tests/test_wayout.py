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


def play(s, a, moves, tool=None):
    """The moves, done by the game's own actions, as the key shown on the block sends them (web/js/digup.js route): the
    block by its place and height, with the pickaxe when you carry one ("tool"), by hand when not. -> how many"""
    tool = {"with": "pickaxe"} if tool is None else tool
    for m in moves:
        h = s.height(a)
        if m["t"] == "step":
            r = run(s, a, "step", {"dir": m["d"]})
            assert r["ok"] and (a.x, a.y, s.height(a)) == (m["x"], m["y"], m["z"]), (m, r, a.x, a.y, s.height(a))
        elif m["key"] == "alt":
            assert run(s, a, "dig_down", dict(tool))["ok"]
        else:
            assert m["z"] == h + (2 if m["key"] == "up" else 1)
            r = run(s, a, "dig", {"x": m["x"], "y": m["y"], "z": m["z"], **tool})
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


def by_hand_out(world):
    """No pickaxe at all ("Grey boxes. No key works": stuck for good): the way is the same one, and every block of it
    goes by hand, as the key on it sends it: the cell over your head, the step's, the wall in front (Space), slower."""
    s, a = world
    flat(s, a)
    assert not a.count("pickaxe")
    for _ in range(6):
        assert run(s, a, "dig_down", {})["ok"]
    r = find(s, a)
    assert r["trapped"] and r["blocks"] == 9
    t0 = s.tick
    play(s, a, r["moves"], tool={})
    by_hand = s.tick - t0
    assert out(s, a) and s.height(a) == 0 and a.hp == 20
    # a wall in front (Space's block): a pit in a hill four high, a tile of it between you and the open land east
    for y in range(a.y + 10, a.y + 21):
        for x in range(a.x - 8, a.x + 2):
            for z in range(1, 5):
                s.world.set_cell(x, y, z, True)
    for z in range(1, 5):
        s.world.set_cell(a.x, a.y + 15, z, False)
    a.y += 15
    assert s.height(a) == 0 and s.world.level(a.x, a.y) == 0 and s.world.level(a.x + 1, a.y) == 4
    r = find(s, a)
    digs = [(m["x"] - a.x, m["y"] - a.y, m["z"], m["key"]) for m in r["moves"] if m["t"] == "dig"]
    assert r["trapped"] and len(digs) == 1, digs               # (through the wall, or a step cut onto it: a block either way)
    play(s, a, r["moves"], tool={})
    assert out(s, a) and find(s, a)["out"] and a.hp == 20
    a.x, a.y, a.z = a.x - 1, a.y + 4, 0                        # ...and Space's block itself, by hand: the wall in front, at your body's height
    while s.world.level(a.x, a.y) != 0 or s.world.level(a.x + 1, a.y) != 0:
        a.x += 1
    s.world.set_cell(a.x + 1, a.y, 1, True)
    s.world.set_cell(a.x + 1, a.y, 2, True)
    r = run(s, a, "dig", {"x": a.x + 1, "y": a.y, "z": 1})
    assert r["ok"] and r["cell"] == [a.x + 1, a.y, 1] and s.world.solid(a.x + 1, a.y, 2), r
    return by_hand


def test_with_bare_hands_the_same_way_is_dug_and_you_are_out(world):
    assert by_hand_out(world) > 0


def test_a_pickaxe_you_carry_is_used_though_something_else_is_in_your_hand(world):
    """The key sends "with: pickaxe" whenever you carry one (the server asks that you have it, not that you hold it):
    the same shaft is left in a third of the time it takes by hand."""
    s, a = world
    by_hand = by_hand_out((s, a))
    flat(s, a)
    a.add("pickaxe")
    a.add("plank", 3)
    for _ in range(6):
        assert run(s, a, "dig_down", {"with": "pickaxe"})["ok"]
    r = find(s, a)
    t0 = s.tick
    play(s, a, r["moves"])
    assert out(s, a) and a.hp == 20 and a.count("pickaxe") == 1
    assert (s.tick - t0) * 2 < by_hand, (s.tick - t0, by_hand)


def test_at_the_bottom_of_a_gorge_you_are_not_out_and_the_way_up_hurts_nobody(world):
    """A floor six wide between two cliffs of twelve, far both ways (the river's canyon by the stone mountain): under
    the open sky, and not out: a way is found (a stair cut up a cliff), and playing it by hand ends on top, no heart
    lost. And no way shown drops you more than three levels while a stair can be cut."""
    s, a = world
    flat(s, a)
    for y in range(a.y - 40, a.y + 41):
        for x in range(a.x - 40, a.x + 41):
            if abs(x - a.x) > 3:
                for z in range(1, 13):
                    s.world.set_cell(x, y, z, True)
    assert s.height(a) == 0 and not s.world.covered(a.x, a.y, 0)
    r = find(s, a, r=38)
    assert not r["out"] and r["path"] and r["blocks"] > 0, (r["out"], r["blocks"])
    assert not r["trapped"]                                  # (the floor goes on past your reach: you walk or swim along it)
    assert find(s, a, r=38, sky=True)["path"] is None        # (and under the open sky the page asks only for a trap's way)
    falls = [p["z"] - q["z"] for p, q in zip(r["path"], r["path"][1:])]
    assert max(falls) <= 3, falls
    play(s, a, r["moves"], tool={})
    assert s.height(a) >= 11 and a.hp == 20 and find(s, a, r=38)["out"]


def test_a_canyon_closed_at_both_ends_is_a_trap_and_one_open_past_your_reach_is_not(world):
    """"The escape detection triggers when swimming between canyons": a gorge is no trap while it goes on. Trapped is
    geometry: the floor you reach on foot (a river's face is a floor: you swim) is all inside your reach, no way out."""
    s, a = world
    flat(s, a)
    for y in range(a.y - 40, a.y + 41):
        for x in range(a.x - 40, a.x + 41):
            if abs(y - a.y) > 1:
                for z in range(1, 10):
                    s.world.set_cell(x, y, z, True)
    r = find(s, a, r=38, sky=True)
    assert not r["out"] and not r["trapped"] and r["path"] is None, (r["out"], r["trapped"])
    for y in range(a.y - 1, a.y + 2):
        for x in (a.x - 20, a.x + 20):
            for z in range(1, 10):
                s.world.set_cell(x, y, z, True)
    r = find(s, a, r=38, sky=True)
    assert r["trapped"] and r["path"] and r["blocks"] > 0, (r["trapped"], r["blocks"])
