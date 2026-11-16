"""The build mode's showcase clip (tools/pages/build_mode.mp4, on the demo's "What's new" page): a house built by
keys alone. How it is filmed: tools/filmkit.py.

    uv run python tools/film_build_mode.py            (about two minutes; writes tools/pages/build_mode.mp4 and .jpg)"""

import sys
from pathlib import Path

from filmkit import ROOT, SLOT, caption, keys, shoot


def scene(g, rec):
    g.clear_area(5)
    g.give(wood_wall=14, door=1, plank=6, roof=20, axe=1)
    kb = g.page.keyboard
    cap = lambda t: caption(g, t)

    def row(seq, wait=190):                                    # Space held while the cursor moves
        kb.down("Space"); g.sleep(250); keys(g, seq, wait); g.sleep(150); kb.up("Space")
    done = lambda ms=90000: g.wait("Build.S.plans.size === 0", ms)
    g.sleep(1200)
    rec.start()
    cap("Build mode: a house, by keyboard alone"); g.sleep(2600)
    cap("1 to 9: take a piece in hand"); g.sleep(700); g.press(g.js(SLOT, "wood_wall")); g.sleep(1500)
    cap("B: build mode. The arrows move a cursor, not you"); g.sleep(600); g.press("b"); g.sleep(1400)
    keys(g, ["ArrowRight"] * 2 + ["ArrowUp"] * 3, 230); g.sleep(500)
    cap("Hold Space and move: a row of plans")
    row(["ArrowRight"] * 4 + ["ArrowDown"] * 3 + ["ArrowLeft"] * 4 + ["ArrowUp"] * 2)
    g.sleep(700); cap("Your character builds them, one by one"); done(); g.sleep(900)
    cap("A door goes in a wall's place"); g.press(g.js(SLOT, "door")); g.sleep(500)
    keys(g, ["ArrowDown"] * 2 + ["ArrowRight"] * 2, 230); g.sleep(500); g.press("Space"); done(); g.sleep(900)
    cap("A floor, the same way"); g.press(g.js(SLOT, "plank")); g.sleep(500)
    keys(g, ["ArrowUp"] * 2 + ["ArrowLeft"], 230)
    row(["ArrowRight"] * 2 + ["ArrowDown"] + ["ArrowLeft"] * 2); done(); g.sleep(900)
    cap("The roof is laid tile by tile"); g.press(g.js(SLOT, "roof")); g.sleep(500)
    keys(g, ["ArrowDown", "ArrowLeft"], 230)
    for i in range(4):
        row(["ArrowRight"] * 4 if i % 2 == 0 else ["ArrowLeft"] * 4)
        if i < 3: keys(g, ["ArrowUp"], 230)
    done(120000); g.sleep(900)
    cap("B: out of build mode"); g.press("b"); g.sleep(1300)
    door = g.js("(() => { for (const b of blocks.values()) for (const [i, c] of b.objs) if (c === '+') return [b.bx * B + i % B, b.by * B + (i / B | 0)]; })()")
    g.js("([x, y]) => act('move_to', {x, y})", [door[0], door[1] + 2]); g.sleep(400)
    g.wait(f"myPos().x === {door[0]} && myPos().y === {door[1] + 2}", 20000); g.sleep(600)
    cap("Home. From under your roof you see through it")
    kb.down("ArrowUp"); g.wait(f"myPos().y <= {door[1] - 1}", 8000); kb.up("ArrowUp"); g.sleep(3200)
    kb.down("ArrowDown"); g.wait(f"myPos().y >= {door[1] + 3}", 8000); kb.up("ArrowDown"); g.sleep(900)
    cap("Nexel Worlds: built block by block"); g.sleep(3200)
    rec.stop()


if __name__ == "__main__":
    shoot(scene, Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tools" / "pages", "build_mode")
