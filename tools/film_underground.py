"""The underground showcase clip (tools/pages/underground.mp4, on the demo's "What's new" page): one way of being
seen when you are hidden (xray.js). Down a stair dug under a hill; into a cave with a fire; a tunnel by night; V
through the four views; then over it all, where the land is the land. How it is filmed: tools/filmkit.py.

    uv run python tools/film_underground.py           (about a minute; writes tools/pages/underground.mp4 and .jpg)"""

import sys
from pathlib import Path

from filmkit import ROOT, caption, shoot

NAMES = {"cut": "Cut away", "outline": "Outline", "faded": "Faded", "circle": "Circle"}


def scene(g, rec):
    g.rpc("dev_creatures", clear=80)
    x, y = g.pos()
    stamp = lambda ax, ay, rows, levels, **kw: g.rpc("dev_stamp", x=ax, y=ay, rows=rows, levels=levels, **kw)
    stamp(x - 50, y - 30, ["." * 101] * 61, [], roofs=[], heads=[])             # a meadow to build on
    g.sleep(600)
    ax, ay = x - 14, y                                                            # a hill rising west, a stair dug west
    stamp(ax, ay - 3, ["." * 10] * 7, ["3322110000"] * 7)                         #  under it from a pit
    stamp(ax, ay, ["." * 10], ["ffedcbba00"], roofs=["9976400000"], heads=["2222200000"])
    bx, by = x + 6, y - 12                                                        # a hill, a cave in it with a fire,
    stamp(bx, by, ["." * 9] * 7, ["4" * 9] * 7)                                   #  its mouth south
    stamp(bx + 1, by + 1, [".......", "..^....", ".......", "......."], ["0" * 7] * 4, roofs=["4" * 7] * 4, heads=["2" * 7] * 4)
    stamp(bx + 4, by + 5, [".", "."], ["0", "0"], roofs=["4", "4"], heads=["2", "2"])
    cx, cy = x + 4, y + 8                                                         # a stair down to two tunnels side by
    stamp(cx, cy, ["...."], ["abcd"])                                             #  side under the meadow, a fire in one
    stamp(cx + 4, cy, [".....^..", ".", "........"], ["d" * 8, "d", "d" * 8], roofs=["4" * 8, "4", "4" * 8], heads=["2" * 8, "2", "2" * 8])
    g.rpc("dev_time", phase=.4)

    def tp(tx, ty, z, wait=1100):
        g.rpc("dev_teleport", x=tx, y=ty, z=z)
        g.wait(f"myAt && myAt.x === {tx} && myAt.y === {ty}", 8000)
        g.wait("dirtyTiles.length === 0", 20000); g.sleep(wait)
    tp(ax + 9, ay, 0)
    rec.start()
    caption(g, "Under ground: you are seen through what hides you"); g.sleep(2400)
    caption(g, "A stair dug under a hill")
    g.hold(["ArrowLeft"], 2300); g.sleep(900)
    rec.poster()
    g.hold(["ArrowLeft"], 1300); g.sleep(1200)
    g.hold(["ArrowRight"], 1600); g.sleep(500)
    tp(bx + 4, by + 8, 0, 700)
    caption(g, "A cave: its room, the wall behind it, a fire")
    g.hold(["ArrowUp"], 1900); g.sleep(700)
    g.hold(["ArrowRight"], 800); g.sleep(500)
    g.hold(["ArrowLeft"], 1500); g.sleep(900)
    for i in range(4):                                         # V through the four views, in the cave (from the usual one, the outline)
        if i:
            g.press("v", 0)
        caption(g, f"V: {NAMES[g.js('opt(`above`)')]}"); g.sleep(1500)
    g.press("v", 0)
    g.rpc("dev_time", phase=.85)
    tp(cx + 3, cy, -4, 900)
    caption(g, "By night: you and the fires light it")
    g.hold(["ArrowRight"], 2000); g.sleep(1400)
    g.rpc("dev_time", phase=.4)
    tp(cx + 7, cy - 1, 0, 700)
    caption(g, "From above, the land is the land")
    g.hold(["ArrowDown"], 1200); g.sleep(1300)
    caption(g, "")
    rec.stop()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shoot(scene, Path(args[0]) if args else ROOT / "tools" / "pages", "underground", frames_only="--frames" in sys.argv)
