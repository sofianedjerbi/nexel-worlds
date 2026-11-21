"""The first screen's island as a still picture (web/assets/title_hd.webp, and _s for a small phone): what the
game itself paints at the island's first moment in its HD look (hd.js: the tilted land, its shadows, its sky), nobody
on it, one art pixel a pixel. (title_poster.webp and _s were the flat picture of the classic look: no longer shown.) The page shows it at once, in
the very place the island will be drawn (index.html), and the island comes in over it (title_scene.js): the first
screen had the sea's flat colour behind its window until every picture of the game had come.

    uv run python tools/build_title_poster.py        (a few seconds; after the island or its art changes:
                                                      tools/build_title_scene.py, the tiles)

It starts a game server of its own on a throwaway world, opens the first screen in Chrome at one screen pixel an art
pixel, waits for the island to be painted, holds its clock, takes its people and animals out of the picture and
keeps the canvas as it is, lossless (WebP: half a PNG's size here; checked pixel for pixel against the canvas)."""

import base64
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "megastructure" / "web" / "assets"
SIZES = {"title_hd.webp": (864, 480), "title_hd_s.webp": (480, 480)}     # (art px: a desk's screen to 2592 x 1440; a phone's, either way up)
BUILT = "document.body.classList.contains('scene') && HdLook.live && HdLook.builds > 0 && !HdLook.busy && !dirtyTiles.length"      # (the HD look has made its land: hd.js)
SHOT = """async () => { const S = TitleScene.S; clearInterval(S.timer);
  cam.x = camT.x = S.ox + S.C.centre[0]; cam.y = camT.y = S.oy + S.C.centre[1] + TITLE_DY;
  ents.clear(); bubbles.length = 0; emotes.clear();
  for (let i = 0; i < 400 && (i < 3 || HdLook.busy); i++) frame(performance.now());
  const cv = HdView.el, ctx = cv.getContext('2d');           // (the HD look's own canvas, an art px a px: hd_view.js)
  const a = ctx.getImageData(0, 0, cv.width, cv.height).data, url = cv.toDataURL('image/webp', 1), img = new Image();   // (both before the game paints its next frame)
  img.src = url; await img.decode();
  const c = document.createElement('canvas'); c.width = cv.width; c.height = cv.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const b = g.getImageData(0, 0, cv.width, cv.height).data; let differ = 0;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) differ++;
  return {url, differ, size: [cv.width, cv.height]}; }"""


def build():
    from playwright.sync_api import sync_playwright
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    work = tempfile.mkdtemp()
    server = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", work, "--world", "poster", "--port", str(port), "--seed", "7"],
                              cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=.2).close(); break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            for name, (w, h) in SIZES.items():
                page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                page.goto(f"http://127.0.0.1:{port}/?zoom=1" + ("&touch=1" if name.endswith("_s.webp") else ""))      # (a phone's picture has no lens, hd_view.js: as a phone draws it, and two thirds the size)
                page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on", timeout=30000)
                page.wait_for_function(BUILT, timeout=60000)
                out = page.evaluate(SHOT)
                assert out["differ"] == 0 and out["size"] == [w, h], (name, out["differ"], out["size"])
                raw = base64.b64decode(out["url"].split(",", 1)[1])
                (ASSETS / name).write_bytes(raw)
                print(f"{name}: {w} x {h}, {len(raw) // 1024} KB")
                page.close()
            browser.close()
    finally:
        server.terminate(); shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    build()
