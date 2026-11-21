"""The floors' showcase clip (tools/pages/floors.mp4, on the demo's "What's new" page): a house of three storeys, up
its stairs and its ladder to the roof, down the ladder again; then build mode's cursor a floor up, and a floor down
under your own, seen through it. How it is filmed: tools/filmkit.py.

    uv run python tools/film_floors.py                (about three minutes; writes tools/pages/floors.mp4 and .jpg)
    uv run python tools/film_floors.py --frames       (the frames only, to look at first)"""

import sys
from pathlib import Path

from filmkit import ROOT, SLOT, caption, shoot

W_, D_ = 9, 8                      # the house, 9 x 8: walls round the ground floor, the front door at (4, 7)
HOLE = {(1, 4), (1, 5)}            # the stairwell in the first floor: the flight comes up at (1, 3)
PART = {(4, 1), (4, 2), (4, 3)}    # a short wall upstairs, from the back wall into the room: the ladder leans on it
HATCH = (5, 1)                     # the ladder (on the first floor) and its hole in the attic floor over it
ROOM2 = (0, 8, 0, 6)               # the first floor's room (i0, i1, j0, j1); row 7 a terrace over the front door
ATTIC = (3, 8, 0, 4)               # the attic, on the first floor's roof; the rest of it a roof terrace
DOWN = [(5, 2, "table"), (4, 2, "chair"), (6, 2, "chair"), (7, 1, "chest"), (6, 5, "rug"), (7, 6, "plant"), (3, 1, "clock")]
TAKEN = {0: {(i, j) for i, j, it in DOWN if it != "rug"}, 3: HOLE | PART | {HATCH, (7, 2), (2, 2), (3, 1), (7, 5)}, 6: set()}


def house(x0, y0) -> list:
    """The house at (x0, y0) as the game's own requests, [[op, args]]: walls and a floor stamped on the ground, the
    rest put by `place` like anyone's, each from a tile beside it (a teleport there first)."""
    ops = []

    def stand(i, j, z, box):                               # the nearest free tile to place (i, j) from, at height z, in box
        i0, i1, j0, j1 = box
        spots = [(a, b) for a in range(i0, i1 + 1) for b in range(j0, j1 + 1) if (a, b) not in TAKEN[z] and (a, b) != (i, j)]
        a, b = min(spots, key=lambda s: (abs(s[0] - i) + abs(s[1] - j), s))
        return a, b, z

    def put(i, j, z, item, st):
        ops.append(["dev_teleport", {"x": x0 + st[0], "y": y0 + st[1], "z": st[2]}])
        ops.append(["act", {"tool": "place", "args": {"x": x0 + i, "y": y0 + j, "item": item, **({} if z is None else {"z": z})}}])
    GROUND, UP, TOP = (1, 7, 1, 6), (1, 7, 1, 5), (4, 7, 1, 3)
    ops.append(["dev_give", {"items": {"plank": 140, "roof": 30, "wood_wall": 48, "door": 2, "stairs": 2, "ladder": 1,
                "table": 2, "chair": 4, "bed": 1, "rug": 3, "plant": 3, "chest": 1, "clock": 1, "flower": 4}}])
    rows = ["".join("+" if (j == D_ - 1 and i == 4) else "W" if i in (0, W_ - 1) or j in (0, D_ - 1) else "n" for i in range(W_)) for j in range(D_)]
    ops.append(["dev_stamp", {"x": x0, "y": y0, "rows": rows}])
    ops.append(["dev_stamp", {"x": x0 + 4, "y": y0 + D_, "rows": ["_", "_"]}])           # a path to the door
    for i, j, it in DOWN:
        put(i, j, None, it, stand(i, j, 0, GROUND))
    for j in range(D_):                                    # the first floor: planks on the walls, block to block; the stairwell open
        for i in range(W_):
            if (i, j) not in HOLE:
                put(i, j, 3, "plank", stand(i, j, 0, GROUND))
    put(1, 4, None, "stairs", (3, 5, 0))                   # the stairs: down from the floor's edge at (1, 3), towards the door
    i0, i1, j0, j1 = ROOM2                                 # the first floor's walls, the short one by the ladder; a door onto the terrace
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            if i in (i0, i1) or j in (j0, j1):
                put(i, j, 3, "door" if (i, j) == (4, j1) else "wood_wall", stand(i, j, 3, UP))
    for i, j in sorted(PART):
        put(i, j, 3, "wood_wall", stand(i, j, 3, UP))
    for i, j, it in [(7, 2, "bed"), (3, 1, "plant"), (2, 2, "table"), (7, 5, "chair"), (5, 4, "rug")]:
        put(i, j, 3, it, stand(i, j, 3, UP))
    for j in range(j0, j1 + 1):                            # the attic floor, on the first floor's walls; the hatch open
        for i in range(i0, i1 + 1):
            if (i, j) != HATCH:
                put(i, j, 6, "plank", stand(i, j, 3, UP))
    put(HATCH[0], HATCH[1], 3, "ladder", stand(*HATCH, 3, UP))     # under the hatch, against the short wall
    a0, a1, b0, b1 = ATTIC                                 # the attic: walls, a door onto the roof terrace, a roof
    for j in range(b0, b1 + 1):
        for i in range(a0, a1 + 1):
            if i in (a0, a1) or j in (b0, b1):
                put(i, j, 6, "door" if (i, j) == (5, b1) else "wood_wall", stand(i, j, 6, TOP))
    for i, j, it in [(7, 1, "chair"), (7, 3, "plant"), (6, 3, "rug")]:
        put(i, j, 6, it, stand(i, j, 6, TOP))
    for j in range(b0, b1 + 1):
        for i in range(a0, a1 + 1):
            put(i, j, 9, "roof", stand(i, j, 6, TOP))
    for i in (1, 2, 6, 7):                                 # flowers along the front
        put(i, D_, None, "flower", (i, D_ + 1, 0))
    return ops


BUILD = """async (ops) => { const fails = [];
  for (const [op, a] of ops) { const r = await rpc(op, a); if (r && r.ok === false) fails.push([op, JSON.stringify(a), r.error, r.detail]); }
  return fails; }"""


def scene(g, rec):
    g.clear_area(14)
    x, y = g.pos()
    x0, y0 = x - 4, y - 12                                 # the house north of us; its door at (x, y - 5)
    fails = g.js(BUILD, house(x0, y0))
    assert not fails, fails
    g.rpc("dev_teleport", x=x0 + 4, y=y0 + 10, z=0)
    g.sleep(1500)
    kb = g.page.keyboard
    cap = lambda t: caption(g, t)
    at = lambda i, j: f"myPos().x === {x0 + i} && myPos().y === {y0 + j}"

    def walk(key, cond, ms=12000):                         # held until there
        kb.down(key); g.wait(cond, ms); kb.up(key); g.sleep(120)

    def where(what):
        s = g.server()
        print(f"  {what}: {s['x'] - x0}, {s['y'] - y0}, z {s['z']}, hp {s['hp']}")
    rec.start()
    cap("A house of three floors"); g.sleep(2600)
    walk("ArrowUp", at(4, 6)); walk("ArrowLeft", at(1, 6))
    cap("Stairs: walk up them")
    walk("ArrowUp", "myAt.z === 3"); g.sleep(900); where("upstairs")
    cap("The first floor: a bedroom, a terrace over the door"); g.sleep(1400); rec.poster(); g.sleep(600)
    cap("A ladder: walk into the wall it leans on")
    walk("ArrowRight", at(3, 3)); walk("ArrowDown", at(3, 4)); walk("ArrowRight", at(5, 4)); walk("ArrowUp", at(5, 1)); g.sleep(700)
    walk("ArrowLeft", "myAt.z === 6"); g.sleep(900); where("attic")
    cap("The attic, and a door onto the roof")
    walk("ArrowDown", at(4, 3)); walk("ArrowRight", at(5, 3)); walk("ArrowDown", at(5, 5)); g.sleep(600); where("roof")
    cap("A roof terrace, three floors up"); g.sleep(2600)
    cap("Back down: walk off the top onto the ladder")
    walk("ArrowUp", at(5, 3)); walk("ArrowLeft", at(4, 3)); walk("ArrowUp", at(4, 1)); g.sleep(400)
    walk("ArrowRight", "myAt.z === 3"); g.sleep(700); where("down the ladder")
    walk("ArrowDown", f"myPos().y === {y0 + 4}"); g.sleep(500)
    # build mode upstairs: the cursor a floor up, and a floor down, under your own floor, seen through it
    g.press(g.js(SLOT, "plank"))                            # (eight planks left from the house)
    cap("Build mode: E lifts the cursor a floor")
    g.press("b"); g.sleep(900)
    cur = lambda: g.js("Build.S.at")

    def cursor_to(i, j, wait=220):
        c = cur()
        for _ in range(abs(x0 + i - c["x"])):
            g.press("ArrowRight" if x0 + i > c["x"] else "ArrowLeft", wait)
        for _ in range(abs(y0 + j - c["y"])):
            g.press("ArrowDown" if y0 + j > c["y"] else "ArrowUp", wait)
    cursor_to(5, 3); g.sleep(500)
    g.press("e", 1800)
    cap("Q: down again, and under your own floor")
    g.press("q", 1100); g.press("q", 1500)
    for k in ["ArrowLeft"] * 3 + ["ArrowDown"] * 2 + ["ArrowRight"] * 2:
        g.press(k, 260)
    g.sleep(1200); where("the cursor " + str(g.js("[Build.S.at, Build.level(), HdLook.win.a > .5]")))
    cap("B: out of build mode"); g.press("b"); g.sleep(1300)
    cap("Nexel Worlds: a house, floor by floor"); g.sleep(3000)
    rec.stop()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shoot(scene, Path(args[0]) if args else ROOT / "tools" / "pages", "floors", frames_only="--frames" in sys.argv)
