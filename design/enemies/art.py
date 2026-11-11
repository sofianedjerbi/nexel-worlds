"""Pixel art written as text: one character = one pixel, '.' or ' ' = empty. Each enemy file gives its own palette.

A sprite is a list of equal-length strings. The helpers below make a second frame from a first one
(change a few rows, shift it, mirror it), so a walk cycle stays consistent from frame to frame.
"""


def G(text):
    rows = [r.rstrip() for r in text.strip("\n").split("\n")]
    w = max(len(r) for r in rows)
    return [r.replace(" ", ".").ljust(w, ".") for r in rows]


def edit(g, rows):
    """A copy with some rows replaced: {row index: new row}. Negative indexes count from the bottom."""
    out = list(g)
    w = len(g[0])
    for i, r in rows.items():
        assert len(r) <= w, f"row {i} is {len(r)} wide, the sprite is {w}"
        out[i] = r.replace(" ", ".").ljust(w, ".")
    return out


def shift(g, dx=0, dy=0, keep=0):
    """Move the pixels by (dx, dy) inside the same box. The last `keep` rows (the ground shadow) stay put."""
    h, w = len(g), len(g[0])
    body, tail = g[:h - keep], g[h - keep:]
    out = [["."] * w for _ in body]
    for y, row in enumerate(body):
        for x, ch in enumerate(row):
            if ch != "." and 0 <= y + dy < len(body) and 0 <= x + dx < w:
                out[y + dy][x + dx] = ch
    return ["".join(r) for r in out] + tail


def mirror(g):
    return [r[::-1] for r in g]


def over(g, top, x=0, y=0):
    """Paint `top` over `g` at (x, y); '.' in `top` leaves `g` showing."""
    out = [list(r) for r in g]
    for j, row in enumerate(top):
        for i, ch in enumerate(row):
            if ch != "." and 0 <= y + j < len(out) and 0 <= x + i < len(out[0]):
                out[y + j][x + i] = ch
    return ["".join(r) for r in out]


def blank(g, n):
    return ["." * len(g[0])] * n


def turn_left(g):
    """Rotate a quarter turn anticlockwise: what pointed up now points left (for creatures seen from straight above)."""
    return ["".join(row[x] for row in g) for x in range(len(g[0]))]


def pad(g, top=0, left=0, right=0, bottom=0):
    w = len(g[0]) + left + right
    return ["." * w] * top + ["." * left + r + "." * right for r in g] + ["." * w] * bottom


def nudge(g, rows, dx):
    """Slide some rows sideways by dx (a head thrust, a lean). Pixels pushed off the edge are an error."""
    out = list(g)
    for i in rows:
        r = out[i]
        if dx < 0:
            assert set(r[:-dx]) <= {"."}, f"row {i} has no room to move {dx}"
            out[i] = r[-dx:] + "." * -dx
        elif dx > 0:
            assert set(r[-dx:]) <= {"."}, f"row {i} has no room to move {dx}"
            out[i] = "." * dx + r[:-dx]
    return out


def squat(g, row):
    """Take one row out (a leg row) and add an empty one on top: everything above sinks by one pixel."""
    return ["." * len(g[0])] + g[:row] + g[row + 1:]


def stack(*parts):
    """Rows of several sprites of the same width, one under the other."""
    return [r for p in parts for r in p]


def outline(fill, ink="o"):
    """Give a filled shape its outline: every empty pixel that touches a filled one (4 neighbours)."""
    h, w = len(fill), len(fill[0])
    out = [list(r) for r in fill]
    for y in range(h):
        for x in range(w):
            if fill[y][x] == "." and any(0 <= y + j < h and 0 <= x + i < w and fill[y + j][x + i] not in ".s"
                                         for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = ink
    return ["".join(r) for r in out]
