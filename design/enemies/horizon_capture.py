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
  // The frame's own list of what stands (render.js hands it to sun.js: bodies, things, walls, built floors and roofs,
  // ladders), taken as it goes by; and from there on nothing that stands is painted: what is left is the ground.
  let skip = false, got = null; const d0 = Sun.draw, f0 = Shader.frame, di = ctx.drawImage.bind(ctx), de = drawEntity;
  Sun.draw = (list, vis, sx, sy, S, t, now) => { d0(list, vis, sx, sy, S, t, now); got = {list: [...list], sx, sy, S, t, now}; skip = true; };
  Shader.frame = (...a) => { skip = false; f0(...a); };
  ctx.drawImage = (...a) => { if (!skip) di(...a); };
  const kept = {};                                   // (a wall's lines, a ladder's rungs are strokes and fills: those too)
  for (const m of ["fillRect", "strokeRect", "fill", "stroke", "fillText"]) { kept[m] = ctx[m].bind(ctx); ctx[m] = (...a) => { if (!skip) kept[m](...a); }; }
  window.drawEntity = (...a) => { if (!skip) de(...a); };
  await frames();
  const ground = cv.toDataURL("image/png");
  Sun.draw = d0; Shader.frame = f0; ctx.drawImage = di; window.drawEntity = de; for (const m of Object.keys(kept)) ctx[m] = kept[m];
  // each one drawn alone on a canvas of its own, and cut to what is painted of it
  const {list, sx, sy, S, t, now} = got, off = document.createElement("canvas"); off.width = cv.width; off.height = cv.height;
  const og = off.getContext("2d", {willReadFrequently: true}), main = ctx, items = [];
  for (const o of list) {
    if (o.pile) continue;
    const p = o.p, x = p ? p.x : o.x, y = p ? p.y : o.ty ?? Math.floor(o.y + .006);
    const X = Math.max(0, Math.round(sx(x) - 4 * S)), Y = Math.max(0, Math.round(sy(y, Math.round(x)) - 9 * S)), w = Math.min(off.width - X, 9 * S), h = Math.min(off.height - Y, 12 * S);
    if (w <= 0 || h <= 0) continue;
    og.setTransform(DPR, 0, 0, DPR, 0, 0); og.globalAlpha = 1; og.clearRect(X, Y, w, h); og.imageSmoothingEnabled = false;
    ctx = og;
    try {
      if (o.spr) { const [img, a, b, sw, sh, dx, dy] = o.spr; og.drawImage(img, a, b, sw, sh, Math.round(sx(o.x) + dx * zoom), Math.round(sy(o.ty, o.x) + dy * zoom), sw * zoom, sh * zoom); }
      else if (p) drawEntity({...p}, sx, sy, S, t, now);
      else o.fx();
    } catch (e) { /* one that will not draw alone: left out */ } finally { ctx = main; }
    const d = og.getImageData(X, Y, w, h).data; let x0 = w, x1 = -1, y0 = h, y1 = -1;
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (d[(j * w + i) * 4 + 3] > 40) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (j < y0) y0 = j; if (j > y1) y1 = j; }
    if (x1 < 0) continue;
    const piece = document.createElement("canvas"); piece.width = x1 - x0 + 1; piece.height = y1 - y0 + 1;
    piece.getContext("2d").drawImage(off, X + x0, Y + y0, piece.width, piece.height, 0, 0, piece.width, piece.height);
    // its foot: where it meets the ground. A body or a thing: its lowest painted row. A built piece (a wall, a floor
    // up in the air, a roof): the foot of its tile, so that a floor stays as high over the ground as it is built.
    // (Its foot is a row of the ground as it lies flat, sea level's: the land's own height at its tile is added back,
    // so the page knows both where on the ground it is and how high over that it stands.)
    const bottom = Y + y1 + 1, foot = Math.round(p ? bottom + liftOf(p) : o.spr ? bottom + liftAt(o.x, o.ty) : Math.max(bottom + liftAt(Math.round(x), y), sy(y) + S));
    items.push({c: piece, x: X + x0, y: Y + y0, foot});
    og.clearRect(X, Y, w, h);
  }
  let aw = 2048, ax = 0, ay = 0, shelf = 0; const out = [];
  for (const it of items) { if (ax + it.c.width > aw) { ax = 0; ay += shelf + 1; shelf = 0; } it.ax = ax; it.ay = ay; ax += it.c.width + 1; shelf = Math.max(shelf, it.c.height); }
  const atlas = document.createElement("canvas"); atlas.width = aw; atlas.height = ay + shelf + 1;
  const ag = atlas.getContext("2d");
  for (const it of items) { ag.drawImage(it.c, it.ax, it.ay); out.push({x: it.x, y: it.y, w: it.c.width, h: it.c.height, ax: it.ax, ay: it.ay, foot: it.foot}); }
  // The land's height, tile by tile, as the picture has it: a picture of the same size where each pixel says which
  // level's top it shows (128 + level; 255: a wall's face). The land is drawn a level higher every 8 art px, so the
  // top of tile (x, y) at level L is the tile's square moved up by L steps, and where it stands higher than the tile
  // south of it, its wall hangs from its lower edge down to that one's height. Painted north to south, as the land is.
  const map = document.createElement("canvas"); map.width = cv.width; map.height = cv.height;
  const mg = map.getContext("2d"), [ox, oy] = screenOrigin(S), step = shOf(1) * zoom, levels = new Set(), faces = [];
  mg.fillStyle = "#000"; mg.fillRect(0, 0, map.width, map.height);
  const tx0 = Math.floor(-ox / S) - 1, ty0 = Math.floor(-oy / S) - 14, tw = Math.ceil(cv.width / S) + 2, th = Math.ceil(cv.height / S) + 30;
  for (let ty = ty0; ty <= ty0 + th; ty++) for (let tx = tx0; tx <= tx0 + tw; tx++) {
    if (!tile(tx, ty)) continue;
    const L = levelAt(tx, ty), Ls = tile(tx, ty + 1) ? levelAt(tx, ty + 1) : L, X = Math.round(ox + tx * S), Y = Math.round(oy + ty * S);
    levels.add(L);
    mg.fillStyle = `rgb(${128 + L},${128 + L},${128 + L})`; mg.fillRect(X, Y - L * step, S, S);
    if (L > Ls) { mg.fillStyle = "#fff"; mg.fillRect(X, Y + S - L * step, S, (L - Ls) * step);
      faces.push({x: X, y: Y + S - L * step, w: S, h: (L - Ls) * step, ax: X, ay: Y + S - L * step, foot: Y + S, g: 1}); }
  }
  return {ground, atlas: atlas.toDataURL("image/png"), levels: map.toDataURL("image/png"), sprites: [...out, ...faces.filter((f) => f.x < cv.width && f.x + f.w > 0 && f.y < cv.height && f.y + f.h > 0)],
          size: [cv.width, cv.height], lv: [...levels].sort((a, b) => b - a), step};
}"""
SETUP = "rpc('dev_time', {phase: .3}); setOpt('names', false); setOpt('hints', false); setOpt('shader', 'natural'); setOpt('reflect', 0); setOpt('clouds', 0); setOpt('above', 'cut')"


def save(name, got):
    for part in ("ground", "atlas", "levels"):
        (OUT / f"{name}_{part}.png").write_bytes(base64.b64decode(got[part].split(",")[1]))
    (OUT / f"{name}.json").write_text(json.dumps({"size": got["size"], "sprites": got["sprites"], "lv": got["lv"], "step": got["step"]}))
    print(name, got["size"], len(got["sprites"]), "things; levels", got["lv"], flush=True)


def scatter(game, rnd, rows, width, keep=()):
    """Trees, bushes, rocks and flowers up and down the strip (not on the rows of `keep`, where a scene is built)."""
    for dy in rows:
        if dy in keep:
            continue
        row = "".join(rnd.choice("T" * 4 + "b" * 2 + "M" + "f" * 2 + " " * 50) for _ in range(width))
        game.js("([dy, row, half]) => rpc('dev_stamp', {x: myPos().x - half, y: myPos().y + dy, rows: [row]})", [dy, row, width // 2])


def meadow(game):
    scatter(game, random.Random(4), range(-26, 22, 2), 46)
    for dx, dy, w in ((-9, -20, 7), (3, -11, 6), (-8, 6, 5), (2, 15, 8), (-20, -6, 6), (12, -24, 9), (14, 3, 5)):
        game.js("([dx, dy, w]) => rpc('dev_stamp', {x: myPos().x + dx, y: myPos().y + dy, rows: ['~'.repeat(w), '~'.repeat(w), '~'.repeat(w)]})", [dx, dy, w])
    for kind, dx, dy in (("cow", 4, -3), ("chicken", -3, 2), ("cow", -6, -9), ("chicken", 8, -14), ("cow", 2, -19)):
        game.spawn(kind, dx, dy, still=9999)


def village(game):
    """Two houses of two floors with roofs north of you (tests/e2e/test_e2e_floors.py builds them), a fence, trees."""
    from test_e2e_floors import house
    x, y = game.pos()
    game.stamp(-11, -26, ["." * 23] * 46)
    scatter(game, random.Random(9), range(-26, 20, 2), 23, keep=range(-22, 0))
    house(game, x - 2, y - 9)
    house(game, x + 3, y - 20)
    game.stamp(-8, -6, ["T...T", ".....", "#####"])
    game.stamp(-9, -19, ["T.T.T.T"])
    game.rpc("dev_teleport", x=x, y=y, z=0)
    return x, y


def hills(game):
    """The world's own mountain (seed 12 wakes you on its terraces): a few trees and animals on it, nothing else staged."""
    for kind, dx, dy in (("cow", 3, -4), ("chicken", -4, -8), ("cow", -5, 5)):
        game.spawn(kind, dx, dy, still=9999)


def under(game):
    """A room dug four down with a stair up to the west, you in it; north of it a hill with a cave and its mouth."""
    x, y = game.pos()
    game.stamp(-11, -26, ["." * 23] * 46)
    scatter(game, random.Random(5), range(-26, 20, 2), 23, keep=range(-18, 6))
    game.stamp(-2, -1, ["....."] * 3, levels=["ddddd"] * 3)
    game.stamp(-6, 0, ["...."], levels=["0abc"])
    game.stamp(-8, -16, ["." * 16] * 7, levels=["4" * 16] * 7)
    game.stamp(-7, -15, ["." * 14] * 5, levels=["0" * 14] * 5, roofs=["4" * 14] * 5, heads=["2" * 14] * 5)
    game.stamp(-7, -10, ["."], levels=["0"], roofs=["4"], heads=["2"])
    game.stamp(3, -5, ["T.T"])
    game.rpc("dev_teleport", x=x, y=y, z=-4)


def main():
    sys.path.insert(0, str(Path(__file__).parents[2] / "tests" / "e2e"))
    from game import Game
    OUT.mkdir(exist_ok=True)
    servers = {}

    def url(seed):
        if seed not in servers:
            k = socket.socket(); k.bind(("127.0.0.1", 0)); port = k.getsockname()[1]; k.close()
            servers[seed] = (subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", tempfile.mkdtemp(), "--world", "horizon", "--port", str(port), "--seed", str(seed), "--dev"],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), port)
            time.sleep(4)
        return f"http://127.0.0.1:{servers[seed][1]}"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for name, width, seed, stage in (("meadow", 2200, 7, meadow), ("village", 1100, 7, village), ("under", 1100, 7, under), ("hills", 1100, 12, hills)):
                pg = b.new_page(viewport={"width": width, "height": 2600})
                game = Game(pg, url(seed))
                game.join("Sky" + name, zoom=3)
                if seed == 7:
                    game.rpc("dev_creatures", clear=60)
                game.js(SETUP)
                game.sleep(2500)
                at = stage(game)
                game.sleep(6000)
                save(name, game.js(GRAB))
                if name == "village":                               # the same village from inside the near house, downstairs
                    game.rpc("dev_teleport", x=at[0], y=at[1] - 6, z=0)
                    game.sleep(4000)
                    save("inside", game.js(GRAB))
                pg.close()
            b.close()
    finally:
        for proc, _ in servers.values():
            proc.terminate()


if __name__ == "__main__":
    main()
