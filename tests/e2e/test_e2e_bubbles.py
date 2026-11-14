"""Speech bubbles in Chrome: drawn in pixels, wrapped, piled oldest lowest, and coming down when one goes."""

import os

SHOT = os.environ.get("BUBBLE_SHOTS")        # a folder to keep a picture of each scene in

SAY = "(text, ago = 0, shout = false) => bubbles.push({name: me, text, t: performance.now() / 1000 - ago, shout})"
MINE = "bubbles.filter((b) => b.name === me && b.at).map((b) => ({text: b.text, x: b.at[0], y: b.at[1], w: b.w, h: b.h, rows: b.rows}))"


def shot(game, name):
    if SHOT:
        v = game.page.viewport_size
        game.page.screenshot(path=f"{SHOT}/{name}.png", clip={"x": v["width"] / 2 - 230, "y": v["height"] / 2 - 330, "width": 460, "height": 400})


def test_bubbles_are_pixels_pile_up_and_come_down(game):
    game.clear_area(6)
    game.js(f"({SAY})('hi!', 3)")
    game.sleep(300)
    one = game.js(MINE)[0]
    edge = game.js(f"""(() => {{ const d = (x, y) => [...ctx.getImageData(x, y, 1, 1).data].slice(0, 3).join(), x = {one['x']}, y = {one['y']}, w = {one['w']}, h = {one['h']};
      const top = new Set(); for (let i = 2; i < w - 2; i++) top.add(d(x + i, y)); for (let i = 2; i < w - 2; i++) top.add(d(x + i, y + 1));
      return {{top: [...top], corner: d(x, y), in1: d(x + 4, y + 2), side: d(x, y + 2), foot: d(x + 4, y + h - 3)}}; }})()""")
    assert edge["top"] == ["91,63,54"] and edge["side"] == "91,63,54", edge       # a hard dark edge, two px thick: no smoothing
    assert edge["corner"] != "91,63,54" and edge["in1"] == "255,246,226" and edge["foot"] == "236,215,176", edge   # the corner stepped off; paper; the foot's shade
    shot(game, "one")
    long = "I found a cave full of iron past the river, bring a pickaxe and some torches when you come"
    game.js(f"({SAY})({long!r}, 4); ({SAY})('ok, coming', 4, true)")
    game.sleep(400)
    a, b, c = game.js(MINE)
    assert [a["text"], c["text"]] == ["hi!", "ok, coming"]
    assert 2 <= len(b["rows"]) <= 5 and " ".join(b["rows"]) == long and b["w"] <= 304 + 16, b   # wrapped whole, no wider than a bubble
    assert a["y"] > b["y"] + b["h"] and b["y"] > c["y"] + c["h"]                 # the oldest lowest, then the next, none on another
    assert a["y"] - (b["y"] + b["h"]) == 2 and b["y"] - (c["y"] + c["h"]) == 2   # one gap between them
    shot(game, "three")
    game.js(f"({SAY})('wait for me', 4)")                                        # a fourth: the oldest goes at once
    game.sleep(500)
    now = game.js(MINE)
    assert [m["text"] for m in now] == [long, "ok, coming", "wait for me"]
    assert now[0]["y"] + now[0]["h"] == a["y"] + a["h"], (now[0], a)             # and the pile has come down onto its place
    assert now[1]["y"] + now[1]["h"] == now[0]["y"] - 2
    shot(game, "after_one_went")
    game.js("bubbles.length = 0")
    game.js(f"({SAY})({'a' * 200!r}, 11)")                                       # one endless word: broken into rows, ended with …
    game.sleep(300)
    rows = game.js(MINE)[0]["rows"]
    assert len(rows) == 5 and rows[4].endswith("…"), rows
    shot(game, "endless")
    assert not game.errors
