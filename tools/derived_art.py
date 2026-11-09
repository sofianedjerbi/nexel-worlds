"""Sprites derived from the pack's own sheets at build time (bare fruit trees, the thin tree's stump and felling)."""

from pathlib import Path

from PIL import Image

# The thin tree is cut at sprite row 23 (just under its crown): the crown above falls, the stump below stays.
THIN_CUT = 23

def thin_stump(assets: Path) -> Image.Image:
    """The young thin tree's stump, cut flat like the felling sheet's stump: dark rim, light cut wood with a
    highlight, then the tree's own trunk and roots. 16x16, drawn on the tree's tile (sprite row r -> tile y r-13)."""
    thin = Image.open(assets / "trees.png").convert("RGBA").crop((0, 0, 16, 32))
    rim, cut, light, bark = (0x90, 0x62, 0x5d, 255), (0xdc, 0xb9, 0x8a, 255), (0xe8, 0xcf, 0xa6, 255), (0xb6, 0x89, 0x62, 255)
    out = Image.new("RGBA", (16, 16))
    out.alpha_composite(thin.crop((0, THIN_CUT + 3, 16, 32)), (0, THIN_CUT + 3 - 13))   # trunk foot and roots
    px, y = out.load(), THIN_CUT - 13                                                      # the cut, rows y..y+2
    for x in range(6, 10):
        px[x, y] = rim
    px[5, y + 1], px[10, y + 1], px[5, y + 2], px[10, y + 2] = rim, rim, rim, rim
    for x in range(6, 10):
        px[x, y + 1] = light if x in (6, 9) else cut
        px[x, y + 2] = bark if x in (6, 9) else light
    return out

def thin_fall_sheet(assets: Path) -> Image.Image:
    """A felling animation for the young thin tree, derived frame by frame from the pack's round-tree sheet.

    The round sheet (13 frames of 64x48, trunk foot at x 40, tile at (32, 28)) wobbles, tips over with a white swoosh,
    lands, then its crown bursts into leaves. For the thin tree: its crown (the sprite minus the stump) is rotated
    about the top of the stump by the angle the round crown has in each frame (measured from its centroid, the
    landing frame snapped flat), the swoosh pixels are kept, and the burst frames break the lying thin crown apart
    following the round crown's burst (BURST). The stump is left out: the game draws the stump tile underneath."""
    fall = Image.open(assets / "tree_fall.png").convert("RGBA")
    thin = Image.open(assets / "trees.png").convert("RGBA").crop((0, 0, 16, 32))
    PIVOT = (40, 15 + THIN_CUT)                     # thin sprite drawn at tile (0, -13) = frame (32, 15); the cut line
    whole = Image.new("RGBA", (64, 48))
    whole.alpha_composite(thin, (32, 15))
    crown = Image.new("RGBA", (64, 48))
    crown.alpha_composite(thin.crop((0, 0, 16, THIN_CUT)), (32, 15))
    angles = [-2, -4, -5, -32, -64, -90]            # frames 0-5, measured on the round crown (frame 5: it lands)
    lying = crown.rotate(90, resample=Image.NEAREST, center=PIVOT)   # PIL turns counter-clockwise: falls left
    out = Image.new("RGBA", (64 * 13, 48))
    for f in range(13):
        frame = fall.crop((f * 64, 0, f * 64 + 64, 48))
        fpx = frame.load()
        new = Image.new("RGBA", (64, 48))
        if f < 3:                                   # still standing (only wobbling): the whole tree, stump included
            new.alpha_composite(whole.rotate(-angles[f], resample=Image.NEAREST, center=(40, 15 + 28)))
        elif f < len(angles):                       # cut: the crown tips over about the cut, the stump stays
            new.alpha_composite(crown.rotate(-angles[f], resample=Image.NEAREST, center=PIVOT))
        elif f - 6 < len(BURST):
            burst_frame(new, lying, *BURST[f - 6])
        npx = new.load()
        for y in range(48):
            for x in range(64):
                r, g, b, a = fpx[x, y]
                if a and r > 215 and g > 215 and b > 215 and not (32 <= x < 48 and y >= 30):   # the swoosh
                    npx[x, y] = (r, g, b, a)
        out.alpha_composite(new, (f * 64, 0))
    return out

# The round crown's burst (frames 6-10): it swells, breaks into clumps that fly apart and drift up, thins, fades.
# (spread px, share of the crown still there, opacity, drift up px), one row per frame
BURST = [(1, .95, 1, 0), (3, .8, 1, 1), (5, .6, .9, 2), (7, .2, .6, 3), (8, .12, .4, 4)]

def burst_frame(dst: Image.Image, crown: Image.Image, spread: float, keep: float, alpha: float, up: int):
    """Draw `crown` broken into 2x2 clumps pushed out from its centre (deterministic, so frames chain smoothly)."""
    src, out = crown.load(), dst.load()
    pts = [(x, y) for y in range(crown.height) for x in range(crown.width) if src[x, y][3]]
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    for by in range(0, crown.height, 2):
        for bx in range(0, crown.width, 2):
            cells = [(bx + i, by + j) for j in (0, 1) for i in (0, 1)
                     if src[bx + i, by + j][3] and src[bx + i, by + j][1] >= src[bx + i, by + j][0]]   # leaves only
            if not cells:
                continue
            h = ((bx * 73856093) ^ (by * 19349663)) & 0xFFFF
            if (h % 100) / 100 >= keep:
                continue
            dx, dy = bx - cx, by - cy
            d = max(1.0, (dx * dx + dy * dy) ** .5)
            k = spread * (.5 + (h >> 8) % 100 / 100)
            ox, oy = round(dx / d * k), round(dy / d * k) - up
            for x, y in cells:
                nx, ny = x + ox, y + oy
                if 0 <= nx < dst.width and 0 <= ny < dst.height:
                    r, g, b, a = src[x, y]
                    out[nx, ny] = (r, g, b, round(a * alpha))

def largest_shape(img: Image.Image) -> Image.Image:
    """Only the largest 4-connected group of non-transparent pixels of `img` (drops loose bits around it)."""
    px, (w, h) = img.load(), img.size
    seen, best = set(), []
    for y in range(h):
        for x in range(w):
            if px[x, y][3] and (x, y) not in seen:
                group, stack = [], [(x, y)]
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    group.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and px[nx, ny][3]:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
                best = max(best, group, key=len)
    out = Image.new("RGBA", img.size)
    op = out.load()
    for x, y in best:
        op[x, y] = px[x, y]
    return out


RAMP_VARIANTS = 4


def ramp_art(hill: Path, below: tuple) -> Image.Image:
    """Slopes down a hill's south cliff: RAMP_VARIANTS pieces of 32x32 side by side. The west and east halves of a
    piece sit on the pair of slope tiles (top 16 rows) and the landing below them (bottom 16). The cliff either side
    ends in the hill sheet's own rounded corners (the client treats the slope tiles as low ground for their
    neighbours), so the slope is a pass between two hill ends: its ground runs from the hilltop's colour down to the
    ground below (`below`), staying within the gap (nothing juts out onto the land below). Each variant dresses it differently: soft grass with contours, a worn earth path winding up, stone steps,
    log steps. Colours come from the hill sheet (and the cliff's browns for earth and logs)."""
    sheet = Image.open(hill).convert("RGBA")
    col = [sheet.getpixel((1 * 16 + 8, 2 * 16 + y)) for y in range(16)]     # a south-edge column: top to cliff foot
    top, rim, line, dark, light = col[0], col[9], col[11], col[12], col[13]
    out = Image.new("RGBA", (32 * RAMP_VARIANTS, 32))
    for v in range(RAMP_VARIANTS):
        img = Image.new("RGBA", (32, 32))
        px = img.load()
        y0, y1 = 4, 20                               # from the hilltop down to just past the cliff's foot
        for y in range(y0, y1 + 1):
            k = (y - y0) / (y1 - y0)
            k = k * k * (3 - 2 * k)                  # eased: it rolls over at the top and settles at the bottom
            for x in range(32):
                c = _mix(top, below, k)
                if y == y1:
                    c = _mix(c, below, .5)
                px[x, y] = c
        _ramp_dress(px, v, y0, y1, top=top, rim=rim, line=line, dark=dark, light=light, below=below)
        out.alpha_composite(img, (32 * v, 0))
    return out


def _ramp_dress(px, v, y0, y1, top, rim, line, dark, light, below):
    """What's on the slope: 0 soft grass and contours, 1 an earth path, 2 stone steps, 3 log steps."""
    shade = lambda c, t: _mix(c, (60, 40, 30), t)
    glow = lambda c, t: _mix(c, (255, 252, 230), t)
    if v == 0:                                       # grass: two soft contours, the upper one tighter
        for cy, w in ((y0 + 4, 9), (y0 + 9, 11)):
            for x in range(16 - w, 16 + w):
                dy = 1 if abs(x - 16) < w - 4 else 0
                px[x, cy + dy] = shade(px[x, cy + dy], .12)
                px[x, cy + dy + 1] = glow(px[x, cy + dy + 1], .18)
        for x, y in ((6, y0 + 6), (24, y0 + 3), (21, y0 + 12), (9, y0 + 13)):   # tufts
            px[x, y], px[x + 1, y - 1] = rim, rim
    elif v == 1:                                     # a worn path of earth winding down the middle
        earth, earth_dark = light, _mix(light, dark, .45)
        for y in range(y0, y1):
            cx = 16 + round(3 * __import__("math").sin((y - y0) * .45))
            half = 3 + (y - y0) // 6
            for x in range(cx - half, cx + half + 1):
                edge = x in (cx - half, cx + half)
                px[x, y] = _mix(px[x, y], earth_dark if edge else earth, .55 if edge else .85)
            if (y - y0) % 4 == 1:
                px[cx + 1, y] = glow(earth, .3)
    elif v == 2:                                     # stone steps set into the grass
        stone, stone_dark, stone_light = (193, 200, 185, 255), (128, 134, 128, 255), (226, 230, 218, 255)
        for i, sy in enumerate((y0 + 2, y0 + 7, y0 + 12)):
            w = 7 + i                                # wider as they come towards you
            for x in range(16 - w, 16 + w):
                px[x, sy] = stone_light
                px[x, sy + 1] = stone
                px[x, sy + 2] = stone_dark
                px[x, sy + 3] = shade(px[x, sy + 3], .15)   # its shadow on the grass
            px[16 - w, sy + 1] = px[16 + w - 1, sy + 1] = stone_dark
    else:                                            # log steps: round ends, bark lines
        bark, bark_dark, cut = dark, line, light
        for i, sy in enumerate((y0 + 2, y0 + 7, y0 + 12)):
            w = 7 + i
            for x in range(16 - w, 16 + w):
                px[x, sy] = _mix(bark, (255, 240, 210), .25)
                px[x, sy + 1] = bark
                px[x, sy + 2] = bark_dark
                px[x, sy + 3] = shade(px[x, sy + 3], .15)
            for x in (16 - w, 16 + w - 1):           # the cut ends of the log
                px[x, sy], px[x, sy + 1], px[x, sy + 2] = cut, cut, bark_dark


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)
