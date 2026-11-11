"""Build one sheet per enemy and the showcase data.

    uv run --with pillow python design/enemies/build.py            everything -> design/enemies/site/
    uv run --with pillow python design/enemies/build.py tusker out.png     a big preview of one enemy (for drawing)

A sheet is laid out like the game's character.png: one row per direction (down, up, left, right), one column per frame
(idle, then walk, then the action). Right is left mirrored. Sprites stand on the bottom centre of their cell.
"""

import importlib
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from art import mirror  # noqa: E402

SITE = HERE / "site"
ASSETS = HERE.parent.parent / "src" / "megastructure" / "web" / "assets"
ORDER = ["tusker", "pincer", "strawman", "wisp", "wyrm", "stag"]       # on the page (stilt, adder, lampwing, snapjaw are kept in roster/, off it)
DIRS = ["down", "up", "left", "right"]
ANIMS = ["idle", "walk", "act"]
IN_GAME = ["tusker", "pincer", "strawman", "wisp", "wyrm"]     # (their frame columns and timings are also in web/js/world_decor.js WILD)
SHADOW = (80, 64, 134, 46)        # the cow's and chicken's shadow colour, a touch stronger for the lighter page grass
FOOT = 2                       # empty pixels under the sprite in its cell


def rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in range(0, len(h), 2)) + ((255,) if len(h) == 6 else ())


def load(key):
    return importlib.import_module(f"roster.{key}").ENEMY


def cell_image(g, pal, cell, name):
    cw, chh = cell
    h, w = len(g), len(g[0])
    assert w <= cw and h + FOOT <= chh, f"{name}: {w}x{h} does not fit a {cw}x{chh} cell"
    img = Image.new("RGBA", cell)
    px = img.load()
    x0, y0 = (cw - w) // 2, chh - FOOT - h
    for y, row in enumerate(g):
        assert len(row) == w, f"{name} row {y}: {len(row)} wide, expected {w}"
        for x, ch in enumerate(row):
            if ch in ".s":
                continue
            assert ch in pal, f"{name} row {y}: unknown colour {ch!r}"
            px[x0 + x, y0 + y] = pal[ch]
    for y, row in enumerate(g):                               # a row of 's' marks the ground under the feet: paint the game's
        if "s" in row:                                        # soft oval there, three rows deep, behind the sprite
            a, b = row.index("s"), row.rindex("s")
            for dy, inset in ((-2, 1), (-1, 0), (0, 1)):
                for x in range(a + inset, b + 1 - inset):
                    if 0 <= y0 + y + dy < chh and px[x0 + x, y0 + y + dy][3] == 0:
                        px[x0 + x, y0 + y + dy] = SHADOW
    return img


def sheet(e):
    pal = {k: rgba(v) for k, v in e["pal"].items()} | {"s": SHADOW}
    dirs = dict(e["dirs"])
    dirs.setdefault("right", {k: [mirror(g) for g in v] for k, v in dirs["left"].items()})
    names = [(a, i) for a in ANIMS for i in range(len(dirs["down"][a]))]
    for d in DIRS:
        assert [len(dirs[d][a]) for a in ANIMS] == [len(dirs["down"][a]) for a in ANIMS], f"{e['key']}.{d}: frame counts differ"
    cw, chh = e["cell"]
    img = Image.new("RGBA", (cw * len(names), chh * 4))
    for r, d in enumerate(DIRS):
        for c, (a, i) in enumerate(names):
            img.alpha_composite(cell_image(dirs[d][a][i], pal, e["cell"], f"{e['key']}.{d}.{a}{i}"), (c * cw, r * chh))
    anims = {a: [c for c, (b, _) in enumerate(names) if b == a] for a in ANIMS}
    ms = {a: (e["ms"][a] if isinstance(e["ms"][a], list) else [e["ms"][a]] * len(anims[a])) for a in ANIMS}
    for a in ANIMS:
        assert len(ms[a]) == len(anims[a]), f"{e['key']}.{a}: {len(anims[a])} frames, {len(ms[a])} durations"
    return img, anims, ms


def preview(key, out, k=6):
    img, _, _ = sheet(load(key))
    bg = Image.new("RGBA", img.size, (155, 201, 132, 255))
    bg.alpha_composite(img)
    bg.resize((img.width * k, img.height * k), Image.NEAREST).save(out)
    print(out, img.size)


def references():
    """The game's own sheets, copied beside the page so it can animate the player, cow and chicken for comparison."""
    (SITE / "game").mkdir(exist_ok=True)
    for name in ("character", "cow", "chicken"):
        shutil.copyfile(ASSETS / f"{name}.png", SITE / "game" / f"{name}.png")


def build():
    (SITE / "sheets").mkdir(parents=True, exist_ok=True)
    meta = []
    for key in ORDER:
        e = load(key)
        img, anims, ms = sheet(e)
        img.save(SITE / "sheets" / f"{key}.png")
        box = img.getbbox()
        meta.append({k: v for k, v in e.items() if k not in ("pal", "dirs")} | {
            "sheet": f"sheets/{key}.png", "anims": anims, "ms": ms, "palette": [v for v in e["pal"].values() if len(v) == 6],
            "frames": img.width // e["cell"][0], "tall": box[3] - box[1]})
    (SITE / "enemies.json").write_text(json.dumps(meta, indent=1))
    references()
    for key in IN_GAME:                                       # the ones the game uses: their sheets go to its assets
        shutil.copyfile(SITE / "sheets" / f"{key}.png", ASSETS / f"{key}.png")
    print(f"{len(meta)} enemies, {sum(m['frames'] * 4 for m in meta)} frames -> {SITE}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        preview(sys.argv[1], sys.argv[2])
    else:
        build()
