"""The game's emblem: a gold coin struck with a brown N (the wordmark's own letter), drawn on a 16 x 16 grid so that it
is a crisp favicon; every larger size is the same pixels, each a square of pixels. Writes, into web/assets/:

    emblem.png        16 x 16    the favicon
    emblem_32.png     32 x 32    the favicon on a dense screen
    emblem_180.png   180 x 180   a phone's home screen (the coin x10 on the island's grass: a phone wants it opaque)

The README's banner lays it beside the wordmark at the wordmark's own pixel size (tools/build_banner.py).

    uv run --with pillow python tools/build_emblem.py
"""

from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "src" / "nexel_worlds" / "web" / "assets"
N = 16
INK = (91, 63, 54)                                          # the wordmark's outline
GOLD, GOLD_D, GOLD_HI = (255, 205, 96), (214, 150, 66), (255, 232, 150)
GRASS = (192, 212, 112)                                     # the island's meadow


def letter(w: int, h: int) -> set:
    """The wordmark's N, its strokes 2 px: two stems, and the diagonal down from the top of the left one."""
    on = set()
    for y in range(h):
        on |= {(0, y), (1, y), (w - 2, y), (w - 1, y)}
        on |= {(x, y) for x in (y, y + 1) if 2 <= x <= w - 3}
    return on


def coin() -> Image.Image:
    """16 x 16: a disc, dark rim, gold face, a shine on its upper left, the N struck in the middle."""
    im = Image.new("RGBA", (N, N))
    for y in range(N):
        for x in range(N):
            d = (x + .5 - 8) ** 2 + (y + .5 - 8) ** 2
            if d <= 64:
                im.putpixel((x, y), (*(INK if d > 49 else GOLD_D if d > 36 else GOLD), 255))
    for x, y in ((4, 5), (5, 4), (6, 3), (4, 6), (3, 7)):
        im.putpixel((x, y), (*GOLD_HI, 255))
    for x, y in letter(8, 8):
        im.putpixel((4 + x, 4 + y), (*INK, 255))
    return im


def build():
    c = coin()
    c.save(ASSETS / "emblem.png")
    c.resize((32, 32), Image.NEAREST).save(ASSETS / "emblem_32.png")
    home = Image.new("RGBA", (180, 180), (*GRASS, 255))
    home.alpha_composite(c.resize((160, 160), Image.NEAREST), (10, 10))
    home.convert("RGB").save(ASSETS / "emblem_180.png")
    print("emblem.png, emblem_32.png, emblem_180.png")


if __name__ == "__main__":
    build()
