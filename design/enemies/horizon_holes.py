"""Count the pixels where no shape is drawn under the horizon (magenta in ?audit=1), place by place, spot by spot."""
import io, os, sys
from playwright.sync_api import sync_playwright
from PIL import Image
T = os.environ.get("TMPDIR", "/tmp") + "/horizon_holes/"; os.makedirs(T, exist_ok=True)
def magenta(png):
    im = Image.open(io.BytesIO(png)).convert("RGB"); px = im.load(); n = 0; box = None
    for y in range(0, im.height): 
        for x in range(0, im.width):
            r, g, b = px[x, y]
            if r > 200 and g < 90 and b > 200:
                n += 1; box = (x, y, x, y) if box is None else (min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y))
    return n, box, im
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True); bad = []
    for name, vp in (("desk", {"width": 1200, "height": 900}), ("phone", {"width": 390, "height": 800})):
        pg = b.new_page(viewport=vp); pg.goto("http://127.0.0.1:8098/horizon.html?audit=1"); pg.wait_for_timeout(4500)
        for sc in ("meadow", "village", "inside", "hills", "hills_tall", "under", "under_tall"):
            for pr in (1, 2):
                for w in range(0, 101, 10):
                    pg.evaluate("([sc, pr, w]) => { document.getElementById('auto').checked = false; if (document.getElementById('play').checked) document.getElementById('play').click(); pick(PRESETS[pr]); state.scene = sc; state.walk = w; show(); }", [sc, pr, w]); pg.wait_for_timeout(130)
                    n, box, im = magenta(pg.locator("#main").screenshot())
                    if n: bad.append((n, name, sc, pr, "walk", w, box)); im.save(T + f"hole_{name}_{sc}_{pr}_w{w}.png")
            # in play: a grid of spots over the place (a spot you cannot stand on is still a camera to look from)
            pg.evaluate("(sc) => { pick(PRESETS[2]); state.scene = sc; show(); if (!document.getElementById('play').checked) document.getElementById('play').click(); }", sc)
            size = pg.evaluate("[SCENES[state.scene].ground.width, SCENES[state.scene].ground.height]")
            for x in range(150, size[0] - 100, 300):
                for r in range(900, size[1] - 100, 220):
                    pg.evaluate("([x, r]) => { const a = youAt(); a.x = a.px = x; a.r = a.pr = r; }", [x, r]); pg.wait_for_timeout(110)
                    n, box, im = magenta(pg.locator("#main").screenshot())
                    if n: bad.append((n, name, sc, 2, "play", (x, r), box)); im.save(T + f"hole_{name}_{sc}_p{x}_{r}.png")
            pg.evaluate("() => { SCENES[state.scene].at = null; }")
    bad.sort(key=lambda q: -q[0])
    print(len(bad), "views with holes")
    for q in bad[:40]: print(q)
