"""What design/enemies/site/horizon.html is made of: a tall, wide frame of the game drawn by the game itself on a
server of its own, in two parts, so that the page can bend the ground and leave what stands on it standing:
  ground.png    the land, the water and the shadows, with nothing standing on it
  atlas.png     every thing that stands (trees, rocks, flowers, animals, you), each cut out
  sprites.json  where each one is on the ground picture: its corner, its size, its place in the atlas, its foot

    uv run python design/enemies/horizon_capture.py
"""
import base64
import json
import random
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).with_name("site") / "horizon"
GRAB = """async () => {
  const frames = () => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(ok))));
  const S = TS(), [ox, oy] = screenOrigin(S), sx = (x) => ox + x * S, sy = (y, x) => oy + y * S - (x === undefined ? 0 : liftOf({x, y}));
  // what stands: each drawn alone, cut to what is painted of it
  const cut = (c) => { const g = c.getContext("2d"), d = g.getImageData(0, 0, c.width, c.height).data; let top = c.height, bottom = -1;
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) if (d[(y * c.width + x) * 4 + 3] > 40) { top = Math.min(top, y); bottom = y; break; }
    return bottom < 0 ? null : [top, bottom + 1]; };
  const items = [];
  for (const b of blocks.values()) for (const [i, c] of b.objs) {
    const x = b.bx * B + i % B, y = b.by * B + (i / B | 0), spr = objectSprite(c, x, y, 0);
    if (!spr) continue;
    const [img, a, bb, w, h, dx, dy] = spr, cv2 = document.createElement("canvas"); cv2.width = w * zoom; cv2.height = h * zoom;
    const g = cv2.getContext("2d"); g.imageSmoothingEnabled = false; g.drawImage(img, a, bb, w, h, 0, 0, w * zoom, h * zoom);
    const rows = cut(cv2); if (rows) items.push({c: cv2, X: Math.round(sx(x) + dx * zoom), Y: Math.round(sy(y, x) + dy * zoom), rows});
  }
  const off = document.createElement("canvas"); off.width = cv.width; off.height = cv.height;
  const og = off.getContext("2d"), main = ctx;
  for (const p of ents.values()) if (p.e) {
    og.setTransform(1, 0, 0, 1, 0, 0); og.clearRect(0, 0, off.width, off.height); og.imageSmoothingEnabled = false;
    ctx = og; try { drawEntity({...p}, sx, sy, S, performance.now() / 1000, performance.now()); } finally { ctx = main; }
    const X = Math.round(sx(p.x) - S), Y = Math.round(bodyY(p, sy) - 2 * S), cv2 = document.createElement("canvas"); cv2.width = 3 * S; cv2.height = 4 * S;
    cv2.getContext("2d").drawImage(off, X, Y, 3 * S, 4 * S, 0, 0, 3 * S, 4 * S);
    const rows = cut(cv2); if (rows) items.push({c: cv2, X, Y, rows});
  }
  const atlas = document.createElement("canvas"); atlas.width = 2048; atlas.height = 2048;
  const ag = atlas.getContext("2d"); let ax = 0, ay = 0, shelf = 0; const out = [];
  for (const it of items) {
    const w = it.c.width, h = it.rows[1] - it.rows[0];
    if (ax + w > atlas.width) { ax = 0; ay += shelf + 1; shelf = 0; }
    ag.drawImage(it.c, 0, it.rows[0], w, h, ax, ay, w, h);
    out.push({x: it.X, y: it.Y + it.rows[0], w, h, ax, ay}); ax += w + 1; shelf = Math.max(shelf, h);
  }
  // the ground alone: the frame draws its shadows (sun.js), and from there on nothing that stands
  let skip = false; const d0 = Sun.draw, f0 = Shader.frame, di = ctx.drawImage.bind(ctx), de = drawEntity;
  Sun.draw = (...a) => { d0(...a); skip = true; };
  Shader.frame = (...a) => { skip = false; f0(...a); };
  ctx.drawImage = (...a) => { if (!skip) di(...a); };
  window.drawEntity = (...a) => { if (!skip) de(...a); };
  await frames();
  const ground = cv.toDataURL("image/png");
  Sun.draw = d0; Shader.frame = f0; ctx.drawImage = di; window.drawEntity = de;
  return {ground, atlas: atlas.toDataURL("image/png"), sprites: out, size: [cv.width, cv.height], used: ay + shelf};
}"""


def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", tempfile.mkdtemp(), "--world", "horizon", "--port", str(port), "--seed", "7", "--dev"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    OUT.mkdir(exist_ok=True)
    try:
        time.sleep(4)
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 2200, "height": 2600})
            pg.goto(f"http://127.0.0.1:{port}/?zoom=3")
            pg.wait_for_timeout(1000)
            pg.click("#name"); pg.keyboard.type("Sky"); pg.keyboard.press("Enter")
            pg.wait_for_function("meObs && myPos()", timeout=20000)
            pg.evaluate("rpc('dev_time', {phase: .3}); rpc('dev_creatures', {clear: 3}); setOpt('names', false); setOpt('hints', false); setOpt('shader', 'natural'); setOpt('reflect', 0); setOpt('clouds', 0)")
            pg.wait_for_timeout(3000)
            rnd = random.Random(4)
            for dy in range(-26, 22, 2):                        # trees, bushes, rocks and flowers up and down the strip
                row = "".join(rnd.choice("T" * 4 + "b" * 2 + "M" + "f" * 2 + " " * 50) for _ in range(46))
                pg.evaluate("([dy, row]) => rpc('dev_stamp', {x: myPos().x - 23, y: myPos().y + dy, rows: [row]})", [dy, row])
            for dx, dy, w in ((-9, -20, 7), (3, -11, 6), (-8, 6, 5), (2, 15, 8), (-20, -6, 6), (12, -24, 9), (14, 3, 5)):
                pg.evaluate("([dx, dy, w]) => rpc('dev_stamp', {x: myPos().x + dx, y: myPos().y + dy, rows: ['~'.repeat(w), '~'.repeat(w), '~'.repeat(w)]})", [dx, dy, w])
            for kind, dx, dy in (("cow", 4, -3), ("chicken", -3, 2), ("cow", -6, -9), ("chicken", 8, -14), ("cow", 2, -19)):
                pg.evaluate("([kind, dx, dy]) => rpc('dev_creatures', {kind, dx, dy, still: 9999})", [kind, dx, dy])
            pg.wait_for_timeout(6000)
            got = pg.evaluate(GRAB)
            b.close()
    finally:
        proc.terminate()
    for name in ("ground", "atlas"):
        (OUT / f"{name}.png").write_bytes(base64.b64decode(got[name].split(",")[1]))
    (OUT / "sprites.json").write_text(json.dumps({"size": got["size"], "sprites": got["sprites"]}))
    print(got["size"], len(got["sprites"]), "things; atlas rows used:", got["used"])


if __name__ == "__main__":
    main()
