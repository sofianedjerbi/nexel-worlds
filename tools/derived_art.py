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
    """Grassy slopes down a hill's south cliff: RAMP_VARIANTS pieces of 32x32 side by side. The west and east halves
    of a piece sit on the pair of slope tiles (top 16 rows) and the landing below them (bottom 16). The hill's grass
    runs out through a gap in the cliff and fans out onto the ground below: one evenly lit plane (no brighter patch
    in the middle), its foot fading into the ground below (`below`) with no edge; along each side the cliff face
    turns and runs diagonally down beside it, tapering to nothing. Colours are the hill sheet's own (sampled from a
    south-edge tile), so it matches each terrace.
    Variants, differing only in what's on the grass: 0 soft contour dashes; 1 the dashes staggered, with tufts;
    2 two shallow grass steps; 3 curved contours (a rounded rise)."""
    sheet = Image.open(hill).convert("RGBA")
    col = [sheet.getpixel((1 * 16 + 8, 2 * 16 + y)) for y in range(16)]     # a south-edge column: top to cliff foot
    top, rim, line, dark, light = col[0], col[9], col[11], col[12], col[13]
    plane = _mix(top, (255, 255, 230), .1)           # the slope faces the light a little more than flat ground
    out = Image.new("RGBA", (32 * RAMP_VARIANTS, 32))
    for v in range(RAMP_VARIANTS):
        img = Image.new("RGBA", (32, 32))
        px = img.load()
        y0, y1 = 9, 26                               # the slope: from where the hill's rim was, down onto the landing
        for y in range(y0, y1 + 1):
            k = (y - y0) / (y1 - y0)                 # 0 at the top, 1 at the foot
            left = round(3 - 3 * k)                  # it fans out as it comes down
            right = 31 - left
            for x in range(left, right + 1):
                f = _foot(k, x, left, right)
                c = _mix(plane if y > y0 else _mix(top, plane, .5), below, f)
                mark = _mark(v, x, y, y0, y1, left, right)
                if mark:                             # contours and steps: shade below a line, light on its lip
                    c = _mix(c, rim if mark < 0 else (255, 255, 230), (.45 if mark < 0 else .22) * (1 - f))
                px[x, y] = c
            wall = round(4 * max(0, 1 - k * 1.6))    # the cliff face beside it, turning down the side and tapering
            for i in range(wall):
                for x in (left - 1 - i, right + 1 + i):
                    if 0 <= x < 32:
                        px[x, y] = (line, dark, light, light)[i]
        if v == 1:                                   # tufts of grass
            for x, y in ((7, y0 + 4), (23, y0 + 7), (13, y0 + 12), (25, y0 + 13)):
                px[x, y], px[x + 1, y - 1], px[x + 2, y] = rim, rim, rim
        out.alpha_composite(img, (32 * v, 0))
    return out


def _mark(v, x, y, y0, y1, left, right) -> int:
    """-1 a shade line on the grass here, +1 a lit lip, 0 nothing."""
    if v == 2:                                       # two shallow steps: a soft drop with a lit lip, edge to edge
        if not left + 1 < x < right - 1:
            return 0
        for yb in (y0 + 5, y0 + 11):
            if y == yb:
                return -1
            if y == yb - 1:
                return 1
        return 0
    if not left + 3 <= x <= right - 3:
        return 0
    if v == 3:                                       # curved: each line bows down in the middle, a rounded rise
        cy = y - y0 - round(1.5 * (1 - ((x - 15.5) / 12) ** 2))
        return -1 if cy % 4 == 2 and (x + y // 4) % 7 < 5 else 0
    if v == 1:                                       # staggered the other way, a little wider apart
        return -1 if (y - y0) % 5 == 2 and (x - y // 5 * 2) % 8 < 5 else 0
    return -1 if (y - y0) % 4 == 2 and (x + y // 4) % 7 < 5 else 0


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def _foot(k, x, left, right):
    """How far the slope has faded into the ground below: from halfway down, eased, and sooner at its sides, so its
    foot has no edge (no line, no rectangle)."""
    side = min(x - left, right - x) / 6
    t = max(0, k - .3 - .25 * (1 - min(1, side))) / .55
    t = min(1, t)
    return t * t * (3 - 2 * t)
