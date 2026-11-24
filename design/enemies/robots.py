"""The robots' sheets, for local/design/robots.html (~/nexel/local, not in git): each race and its robot, as the game's own code draws them
(web/js/races.js raceSheet(key, tint, bot)), saved as PNG. Starts a server of its own on a world of its own.

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
RACES = ["cat", "bunny", "bear", "frog", "duck"]
TINTS = {"cream": "#f3f2c0", "rose": "#f0a6b4", "sky": "#9cc8ee"}     # three people: the robot keeps a little of each one's colour


def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    proc = subprocess.Popen([sys.executable, "-m", "nexel_worlds.server", "--saves", tempfile.mkdtemp(), "--world", "robots", "--port", str(port), "--seed", "7"],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(4)
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            page = b.new_page()
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_function("typeof ready !== 'undefined' && IMG.character && IMG.character.complete && IMG.character.width")
            sheets = {}
            for key in RACES:
                for name, tint in TINTS.items():
                    for bot in (False, True):
                        url = page.evaluate("([k, t, bot]) => raceSheet(k, t, bot).toDataURL()", [key, tint, bot])
                        img = Image.open(io.BytesIO(base64.b64decode(url.split(",")[1]))).convert("RGBA")
                        sheets[(key, name, bot)] = img
                        if name == "cream" or bot:
                            img.save(OUT / f"{'robot' if bot else 'race'}_{key}_{name}.png")
            b.close()
    finally:
        proc.terminate()
    cell = 48
    look = Image.new("RGBA", (cell * 9 * 4, cell * len(RACES) * 4), (120, 170, 110, 255))      # for the eye: the race, then its robot from all sides, walking, working
    for j, key in enumerate(RACES):
        frames = [(False, 0, 0), (True, 0, 0), (True, 2, 0), (True, 1, 0), (True, 3, 0), (True, 4, 2), (True, 6, 2), (True, 16, 3), (True, 18, 3)]
        for i, (bot, row, col) in enumerate(frames):
            f = sheets[(key, "cream", bot)].crop((col * cell, row * cell, col * cell + cell, row * cell + cell)).resize((cell * 4, cell * 4), Image.NEAREST)
            look.alpha_composite(f, (i * cell * 4, j * cell * 4))
    look.save(OUT / "robots_look.png")
    (OUT / "robots.json").write_text(json.dumps({"races": RACES, "tints": TINTS, "cell": cell}))
    print("saved", len(sheets), "sheets;", look.size)


if __name__ == "__main__":
    main()
