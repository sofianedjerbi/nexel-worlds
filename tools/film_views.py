"""The views' showcase clip (tools/pages/views.mp4, on the demo's "What's new" page): what hides you shown four ways
(options.js: VIEWS), V going through them in the places where something does: in a house of three storeys, behind
it, down a stair dug into the ground; then build mode upstairs, Q a floor down. How it is filmed: tools/filmkit.py.

    uv run python tools/film_views.py                 (about two minutes; writes tools/pages/views.mp4 and .jpg)"""

import sys
from pathlib import Path

from filmkit import ROOT, caption, shoot
from film_floors import BUILD, house

NAMES = {"cut": "Cut away", "outline": "Outline", "faded": "Faded", "circle": "Circle"}


def scene(g, rec):
    g.clear_area(14)
    x, y = g.pos()
    x0, y0 = x - 4, y - 12
    g.stamp(5, -6, ["......"] * 3, levels=["000000", "0abc00", "000000"])     # a stair dug down, east of the house
    fails = g.js(BUILD, house(x0, y0))
    assert not fails, fails
    g.js("setOpt('above', 'cut')")
    tp = lambda i, j, z: (g.rpc("dev_teleport", x=x0 + i, y=y0 + j, z=z), g.sleep(900))

    def views(what, ms=2300):                                   # V through the four (the caption said as V is pressed)
        for i in range(4):
            if i:
                g.press("v", 0)
            caption(g, f"{what} · V: {NAMES[g.js('opt(`above`)')]}"); g.sleep(ms)
        caption(g, ""); g.press("v", 0)                         # (back to the first, for the next place)
    tp(5, 4, 0)
    g.sleep(800)
    rec.start()
    caption(g, "What hides you, four ways: V goes from one to the next"); g.sleep(2600)
    views("In a house")
    rec.poster()
    tp(4, -1, 0)
    views("Behind it")
    tp(12, 7, -3)
    views("Down a dug stair")
    tp(5, 4, 3)
    g.press("b", 600)
    g.js(f"Build.S.at = {{x: {x0 + 5}, y: {y0 + 3}}}")
    caption(g, "Build mode upstairs: Q a floor down"); g.sleep(900)
    g.press("q", 2200)
    caption(g, "E a floor up again"); g.press("e", 1800)
    g.press("b", 600)
    caption(g, "Esc, Settings, Picture: What hides you"); g.sleep(2600)
    rec.stop()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shoot(scene, Path(args[0]) if args else ROOT / "tools" / "pages", "views", frames_only="--frames" in sys.argv)
