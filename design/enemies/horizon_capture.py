"""The tall frame of the game that design/enemies/site/horizon.html bends (a strip of meadow, staged with trees and
ponds, drawn by the game itself on a server of its own): design/enemies/site/horizon/world.png.

    uv run python design/enemies/horizon_capture.py
"""
import base64, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
from playwright.sync_api import sync_playwright
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", tempfile.mkdtemp(), "--world", "horizon", "--port", str(port), "--seed", "7", "--dev"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
OUT = Path("design/enemies/site/horizon"); OUT.mkdir(exist_ok=True)
try:
    time.sleep(4)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True); pg = b.new_page(viewport={"width": 1100, "height": 2600})
        pg.goto(f"http://127.0.0.1:{port}/?zoom=3"); pg.wait_for_timeout(1000)
        pg.click("#name"); pg.keyboard.type("Sky"); pg.keyboard.press("Enter"); pg.wait_for_function("meObs && myPos()", timeout=20000)
        pg.evaluate("rpc('dev_time', {phase: .3}); rpc('dev_creatures', {clear: 3}); setOpt('names', false); setOpt('shader', 'natural'); setOpt('reflect', 0)")
        pg.wait_for_timeout(2500)
        import random
        rnd = random.Random(4)
        for dy in range(-26, 22, 3):                        # trees, bushes, rocks and a few ponds up and down the strip
            row = "".join(rnd.choice("T" * 3 + "b" * 2 + "M" + "f" * 2 + " " * 60) for _ in range(23))
            pg.evaluate("([dy, row]) => rpc('dev_stamp', {x: myPos().x - 11, y: myPos().y + dy, rows: [row]})", [dy, row])
        for dx, dy, w in ((-9, -20, 7), (3, -11, 6), (-8, 6, 5), (2, 15, 8)):
            pg.evaluate("([dx, dy, w]) => rpc('dev_stamp', {x: myPos().x + dx, y: myPos().y + dy, rows: ['~'.repeat(w), '~'.repeat(w), '~'.repeat(w)]})", [dx, dy, w])
        pg.evaluate("rpc('dev_creatures', {kind: 'cow', dx: 4, dy: -3, still: 9999}); rpc('dev_creatures', {kind: 'chicken', dx: -3, dy: 2, still: 9999})")
        pg.wait_for_timeout(5000)
        print(pg.evaluate("[cv.width, cv.height, blocks.size, [...blocks.values()].filter((b) => b.relief).length]"))
        url = pg.evaluate("cv.toDataURL('image/png')")
        (OUT / "world.png").write_bytes(base64.b64decode(url.split(",")[1]))
finally:
    proc.terminate()
