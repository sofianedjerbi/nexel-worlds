"""The robots' sheets, for design/enemies/site/robots.html: five robots for the cat (robots_cat.js), as the game's own
code draws them (web/js/races.js raceSheet(key, tint, design)), saved as PNG. Starts a server of its own on a world of
its own.

    uv run --with pillow python design/enemies/robots.py
"""
import base64
import io
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parents[2]
OUT = Path(__file__).with_name("site") / "sheets"
TINTS = {"cream": "#f3f2c0", "rose": "#f0a6b4", "sky": "#9cc8ee"}     # three people: what each robot keeps of a person's colour
DESIGNS = Path(__file__).with_name("robots_cat.js")


def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", tempfile.mkdtemp(), "--world", "robots", "--port", str(port), "--seed", "7"],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(4)
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            page = b.new_page()
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_function("typeof ready !== 'undefined' && IMG.character && IMG.character.complete && IMG.character.width")
            page.add_script_tag(content=DESIGNS.read_text() + "\nwindow.CATBOTS = CATBOTS;")
            bots = page.evaluate("CATBOTS.map((b) => ({id: b.id, name: b.name, text: b.text}))")
            sheets = {}
            for old in OUT.glob("robot_*.png"):
                old.unlink()
            grab = lambda js, arg: Image.open(io.BytesIO(base64.b64decode(page.evaluate(js, arg).split(",")[1]))).convert("RGBA")
            cat = grab("(t) => raceSheet('cat', t).toDataURL()", TINTS["cream"])
            cat.save(OUT / "race_cat_cream.png")
            for i, bot in enumerate(bots):
                for name, tint in TINTS.items():
                    sheets[(bot["id"], name)] = grab("([i, t]) => raceSheet('cat', t, CATBOTS[i]).toDataURL()", [i, tint])
                    sheets[(bot["id"], name)].save(OUT / f"robot_cat_{bot['id']}_{name}.png")
            b.close()
    finally:
        proc.terminate()
    cell = 48
    frames = [(0, 0), (2, 0), (1, 0), (3, 0), (4, 2), (6, 2), (16, 3), (18, 3)]      # for the eye: from all sides, walking, working
    look = Image.new("RGBA", (cell * (len(frames) + 1) * 4, cell * len(bots) * 4), (120, 170, 110, 255))
    for j, bot in enumerate(bots):
        for i, (row, col) in enumerate([(0, 0)] + frames):
            src = cat if i == 0 else sheets[(bot["id"], "cream")]
            f = src.crop((col * cell, row * cell, col * cell + cell, row * cell + cell)).resize((cell * 4, cell * 4), Image.NEAREST)
            look.alpha_composite(f, (i * cell * 4, j * cell * 4))
    look.save(OUT / "robots_look.png")
    (OUT / "robots.json").write_text(json.dumps({"designs": bots, "tints": TINTS, "cell": cell}))
    print("saved", len(sheets), "sheets;", look.size)


if __name__ == "__main__":
    main()
