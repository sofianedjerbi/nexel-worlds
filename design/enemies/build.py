"""Build the enemy sheet and the showcase data from sprites.py.

    uv run --with pillow python design/enemies/build.py

Writes design/enemies/site/: enemies.png (every frame, one row per enemy), enemies.json (names, text, frame boxes, animations),
refs.png (the player, a cow, a chicken and the gloom from the game's own art, for scale).
"""

import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import sprites  # noqa: E402

SITE = HERE / "site"
ASSETS = HERE.parent.parent / "src" / "megastructure" / "web" / "assets"


def rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in range(0, len(h), 2)) + ((255,) if len(h) == 6 else ())


PAL = {k: rgba(v) for k, v in sprites.PAL.items()}


def draw(rows, size, name):
    img = Image.new("RGBA", (size, size))
    px = img.load()
    assert len(rows) <= size, f"{name}: {len(rows)} rows in a {size}px frame"
    for y, row in enumerate(rows):
        assert len(row) <= size, f"{name} row {y}: {len(row)} wide in a {size}px frame: {row!r}"
        for x, ch in enumerate(row):
            if ch != " ":
                assert ch in PAL, f"{name} row {y}: unknown colour {ch!r}"
                px[x, y] = PAL[ch]
    return img


def build():
    SITE.mkdir(exist_ok=True)
    cell = max(e["size"] for e in sprites.ENEMIES.values())
    cols = max(len(e["frames"]) for e in sprites.ENEMIES.values())
    sheet = Image.new("RGBA", (cols * cell, len(sprites.ENEMIES) * cell))
    meta = {}
    for r, (key, e) in enumerate(sprites.ENEMIES.items()):
        boxes = {}
        for c, (fname, rows) in enumerate(e["frames"].items()):
            sheet.alpha_composite(draw(rows, e["size"], f"{key}.{fname}"), (c * cell, r * cell))
            boxes[fname] = [c * cell, r * cell, e["size"], e["size"]]
        meta[key] = {k: e[k] for k in ("name", "size", "where", "when", "role", "behaviour", "stats", "anim")} | {"frames": boxes}
    sheet.save(SITE / "enemies.png")
    (SITE / "enemies.json").write_text(json.dumps(meta, indent=1))

    sources = [("player", "character.png", (0, 0, 48, 48)), ("cow", "cow.png", (0, 0, 32, 32)),
               ("chicken", "chicken.png", (0, 0, 16, 16)), ("gloom", "gen.png", (48, 0, 64, 16))]
    crops = []
    for label, f, box in sources:                             # trimmed to their pixels, so they stand on one ground line
        im = Image.open(ASSETS / f).convert("RGBA").crop(box)
        crops.append((label, im.crop(im.getbbox())))
    refs = Image.new("RGBA", (sum(c.width for _, c in crops), max(c.height for _, c in crops)))
    boxes, x = [], 0
    for label, c in crops:
        refs.alpha_composite(c, (x, 0))
        boxes.append({"label": label, "box": [x, 0, c.width, c.height]})
        x += c.width
    refs.save(SITE / "refs.png")
    (SITE / "refs.json").write_text(json.dumps(boxes))

    print(f"{len(meta)} enemies, {sum(len(m['frames']) for m in meta.values())} frames -> {SITE}")


if __name__ == "__main__":
    build()
