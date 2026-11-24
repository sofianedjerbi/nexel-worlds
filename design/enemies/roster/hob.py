"""Hob: a walking clay hearth, the one creature on your side. A round oven on two chunky feet, a fire in the firebox low
in its belly, two ember eyes above it and a chimney that smokes. Build one by a home and it stays there.

Every frame is computed from parts that move against each other: the dome (shaded clay, faint courses of brick, a rim
of brick at its foot), the firebox (an arch of brick, soot, an ember bed and three tongues of flame, its glow warming the
clay round it), the face (ember eyes with a glint, warm cheeks), two mitten arms, two feet, the chimney and its smoke.
  idle   a slow breath (the dome rises and settles), the fire flickering, a puff leaving the chimney, a blink
  walk   heavy: the body sinks on each footfall, leans into the step, the arms swing against the feet, smoke trails
  flare  the warning, turned round: it hunches and the fire draws in, eyes narrowed (held); then the firebox bursts:
         its whole front lit, a flame out of the chimney, sparks thrown out in a ring. Night things back off.
  sit    it settles onto its base, eyes closed in two happy arcs, the fire low, smoke curling: how it keeps a door all night
"""
import math

from art import canvas, dot, ell, ground, over, part, rows

PAL = {"o": "6f3f33", "c": "de8f5f", "l": "f0ac78", "h": "fcd4a2", "d": "bf6e4b", "D": "a35a3f", "m": "93503b",
       "k": "4d2b2e", "f": "fff09a", "r": "ffb54c", "R": "ee6b45", "y": "ffe38a", "w": "ffffff", "x": "f59a7a",
       "g": "f7b98a", "z": "efe9ee9c", "Z": "efe9ee55"}
W, H, CX, BASE = 32, 40, 16, 38
FIRE = [(2, 3, 2), (3, 2, 3), (3, 3, 2), (2, 2, 3), (3, 3, 3), (2, 3, 2), (3, 2, 2), (2, 3, 3)]   # flame heights, 3 tongues


def feet(c, cx, top, step, sit, side):
    """Two chunky feet: clay on top, toes marked at the front; the lifted one a row up."""
    for name, x0 in ((("l", cx - 7), ("r", cx + 2)) if not side else (("l", cx - 5), ("r", cx + 1))):
        up = 1 if step == name else 0
        for y in range(top - 1, BASE - up - sit):
            for x in range(x0, x0 + 5):
                c[y][x] = "c" if y == top - 1 else ("D" if y == BASE - up - sit - 1 else "d")
        for x in (x0 + 1, x0 + 3) if not side else (x0,):
            dot(c, x, BASE - up - sit - 1, "m")


def dome(c, cx, cy, rx, ry, top, back):
    ell(c, cx, cy, rx, ry, "D", clip=(0, top))
    ell(c, cx - .8, cy - .4, rx - .9, ry - .7, "d", on="D")
    ell(c, cx - 1.8, cy - 1, rx - 2.2, ry - 1.8, "c", on="d")
    ell(c, cx - 3.2, cy - 3.6, 3, 2.2, "l", on="c")
    ell(c, cx - 3.8, cy - 4.6, 1.3, .8, "h", on="l")
    for k, y in enumerate((round(cy) - 2, round(cy) + 2)):    # faint courses of brick: short dashes, staggered
        for x in range(W):
            if c[y][x] in "cd" and (x + k * 2) % 4 == 0:
                c[y][x] = "d" if c[y][x] == "c" else "D"
    for x in range(W):                                   # the rim of brick at its foot
        if c[top - 2][x] != ".":
            c[top - 2][x] = "m"
        if c[top - 1][x] != ".":
            c[top - 1][x] = "D" if x % 3 else "m"


def firebox(c, cx, rx, top, side, i, fire, glow):
    """The arch, the soot, the ember bed, the flames; `glow` warms the clay round it."""
    dw = 6 if not side else 3
    dx0 = cx - dw // 2 if not side else round(cx - rx + 1)
    dtop = top - 6
    if glow:                                             # the light of the fire on the clay round the door
        for y in range(dtop - 3, top - 1):
            for x in range(dx0 - 3, dx0 + dw + 3):
                if c[y][x] in "dD" and math.hypot(x - (dx0 + dw / 2), (y - top) * 1.2) < 5 + glow * 3:
                    c[y][x] = "c" if glow < 2 else "l"
                elif c[y][x] == "c" and glow >= 2 and math.hypot(x - (dx0 + dw / 2), (y - top) * 1.2) < 7:
                    c[y][x] = "g"
    for y in range(dtop - 1, top - 1):                   # the arch of brick
        for x in range(dx0 - 1, dx0 + dw + 1):
            if c[y][x] != "." and not (y == dtop - 1 and x in (dx0 - 1, dx0 + dw)):
                c[y][x] = "m"
    for y in range(dtop, top - 2):
        inset = 1 if y == dtop else 0
        for x in range(dx0 + inset, dx0 + dw - inset):
            c[y][x] = "k"
    for x in range(dx0, dx0 + dw):                      # the ember bed
        c[top - 3][x] = "R" if (x + i) % 2 else "r"
    heights = FIRE[i % 8]
    for t, x in enumerate(range(dx0 + (1 if not side else 0), dx0 + dw - (1 if not side else 0))):
        hgt = max(0, round(heights[t % 3] * fire))
        for k in range(hgt):
            y = top - 4 - k
            if y >= dtop:
                c[y][x] = "R" if k == hgt - 1 and hgt > 1 else ("f" if k == 0 and fire > .6 else "r")
    if fire > 1.5:                                       # burst: the door full of fire up to the arch
        for y in range(dtop, top - 3):
            for x in range(dx0 + (y == dtop), dx0 + dw - (y == dtop)):
                c[y][x] = "f" if y > dtop + 1 else "y"
    for x in (range(dx0 + 1, dx0 + dw - 1, 2) if not side else (dx0 + 1,)):   # the grate: iron bars across the fire
        for y in range(dtop + 1, top - 3):
            c[y][x] = "m" if fire <= 1.5 else "r"
    return dtop


def face(g, cx, cy, rx, side, eyes):
    ey = round(cy) - 3
    xs = (cx - 4, cx + 2) if not side else (round(cx - rx) + 2,)
    for x in xs:
        if eyes == "open":                               # ember eyes: a glint top left
            g[ey][x] = g[ey][x + 1] = g[ey + 1][x] = g[ey + 1][x + 1] = "y"
            g[ey][x] = "w"
            g[ey + 1][x + 1] = "r"
        elif eyes == "narrow":
            g[ey + 1][x] = g[ey + 1][x + 1] = "R"
            g[ey][x] = g[ey][x + 1] = "k"
        elif eyes == "happy":                            # two arcs, content
            g[ey][x] = g[ey][x + 1] = "k"
            g[ey + 1][x - 1 if not side else x] = "k"
            if not side:
                g[ey + 1][x + 2] = "k"
        else:
            g[ey + 1][x] = g[ey + 1][x + 1] = "k"
    for x in (cx - 6, cx + 5) if not side else (round(cx - rx) + 4,):
        if g[ey + 3][x] in "cdlDg":
            g[ey + 3][x] = "x"


def chimney(c, cx, cy, ry, side):
    chx = cx + (2 if not side else 3)
    ctop = round(cy - ry) - 3
    for y in range(ctop, round(cy - ry) + 3):
        for x in range(chx, chx + 4):
            c[y][x] = "D" if x == chx + 3 else ("d" if y > ctop + 1 else "m")
    for x in range(chx - 1, chx + 5):                   # its cap
        c[ctop][x] = "m"
    return chx, ctop


def frame(facing, i=0, bob=0, lean=0, step=None, arm=0, squash=0, fire=1.0, eyes="open", sit=0, smoke=None, sparks=0,
          glow=0.6, flame=0):
    side, back = facing == "left", facing == "up"
    top = BASE - 4 + sit
    rx, ry = 8.5 + squash, 8.8 - squash
    cy = top - ry + 1 + bob
    cx = CX + lean
    out = rows(canvas(W, H))
    if sit < 3:
        ft = canvas(W, H)
        feet(ft, CX, top, step, sit, side)
        out = over(out, part(ft))
    ch = canvas(W, H)
    chx, ctop = chimney(ch, cx, cy, ry, side)
    out = over(out, part(ch))
    b = canvas(W, H)
    dome(b, cx, cy, rx, ry, top, back)
    if not back:
        firebox(b, cx, rx, top, side, i, fire, glow)
    out = over(out, part(b))
    a = canvas(W, H)                                     # mitten arms, swinging against the feet
    if not (back and sit >= 3):
        arm_y = cy + 1.5 - (2 if sparks == 1 else 0)
        for ax, sw in (((cx - rx - .3, -arm), (cx + rx + .3, arm)) if not side else ((cx + rx - .5 + arm * 1.2, 0),)):
            ell(a, ax + sw * .5, arm_y + abs(sw) * .5, 2.2, 3, "c")
            ell(a, ax + sw * .5, arm_y + abs(sw) * .5 + 1.4, 2, 1.4, "d", on="c")
            dot(a, ax - .6 + sw * .5, arm_y - 1.4, "l")
        out = over(out, part(a))
    g = [list(r) for r in out]
    if not back:
        face(g, cx, cy, rx, side, eyes)
    if flame:                                            # flare: fire out of the chimney
        for k in range(flame * 2 + 1):
            for x in range(chx + 1, chx + 3):
                dot(g, x + (k % 2) * (1 if x == chx + 1 else 0), ctop - 1 - k, "f" if k < flame else ("r" if k < flame * 2 else "R"), on=".")
    if smoke is not None:                                # a puff leaving the chimney: rises, swells, fades, drifts back
        sx = chx + 2 - (smoke * .6 if side else -smoke * .3)
        sy = ctop - 1 - smoke * 1.4
        r = .8 + smoke * .35
        for y in range(H):
            for x in range(W):
                if g[y][x] == "." and math.hypot(x + .5 - sx, y + .5 - sy) <= r:
                    g[y][x] = "z" if smoke < 4 else "Z"
    for k in range(12 if sparks else 0):                # sparks thrown out in a ring from the firebox
        a_ = k * math.pi / 6 + sparks * .4
        rad = 6 + 3.5 * sparks
        x, y = cx + rad * math.cos(a_), min(BASE - 2, top - 4 + rad * .7 * math.sin(a_))
        dot(g, x, y, "f" if sparks < 3 else "r", on=".")
        if sparks == 2 and k % 3 == 0:
            dot(g, x + math.cos(a_), y + math.sin(a_) * .7, "y", on=".")
    return ground(rows(g), CX + lean, 17 + squash)


def frames(d):
    idle = [frame(d, i, smoke=[0, 1, 2, 3, 4, 5, None, None][i], eyes="shut" if i == 6 else "open",
                  bob=1 if i in (3, 4, 5) else 0, squash=0) for i in range(8)]
    walk = []
    for i in range(8):
        down = i % 4 in (2, 3)                           # the foot lands: the body sinks a pixel
        walk.append(frame(d, i, bob=1 if down else 0, step=None if down else ("l" if i < 4 else "r"),
                          arm=(1 if i < 4 else -1) * (0 if down else 1), lean=-1 if d == "left" and not down else 0,
                          smoke=[1, 2, 3, 4, 1, 2, 3, 4][i]))
    flare = [frame(d, 0, squash=1, fire=.5, eyes="narrow", glow=.3), frame(d, 1, squash=1, fire=.25, eyes="narrow", bob=1, glow=0),
             frame(d, 2, squash=-1, fire=2, sparks=1, glow=2, flame=2), frame(d, 3, squash=-1, fire=2, sparks=2, glow=2, flame=3),
             frame(d, 4, fire=1.6, sparks=3, glow=1.5, flame=1), frame(d, 5, fire=1.2, glow=1, smoke=2), frame(d, 6, smoke=4)]
    sit = [frame(d, 0, sit=1), frame(d, 1, sit=2, eyes="happy"), frame(d, 2, sit=3, eyes="happy", fire=.6, glow=.4),
           frame(d, 3, sit=3, eyes="happy", fire=.6, smoke=1, glow=.4), frame(d, 4, sit=3, eyes="happy", fire=.6, smoke=3, glow=.4),
           frame(d, 5, sit=3, eyes="happy", fire=.6, smoke=5, glow=.4), frame(d, 6, sit=2), frame(d, 7, sit=1)]
    return dict(idle=idle, walk=walk, flare=flare, sit=sit)


ENEMY = dict(
    key="hob", name="Hob", pal=PAL, role="ally", cell=(32, 42), move="waddle", side="ally",
    beats=dict(flare="wwsssrr"), hit=dict(flare="burn"),
    ms=dict(idle=[260, 220, 220, 260, 300, 260, 140, 260], walk=110, flare=[260, 320, 80, 140, 180, 220, 260],
            sit=[160, 200, 300, 520, 520, 520, 200, 160]),
    where="wherever you build one: a dome of clay, a hearthstone and a coal", when="always; it matters at night",
    behaviour="A hearth that walks. Feed it wood and it follows you, or tell it to stay and it sits by your door. At night "
              "it keeps a ring of light round itself; anything that comes into it, it <b>flares</b> at: it hunches, the fire "
              "draws in, then the firebox bursts in a blaze of light, a flame leaps from the chimney and sparks fly: what "
              "is close is burnt and thrown back, and night creatures flee and do not come near again for a while. It never "
              "chases, and never hurts a player or their animals. It also cooks what you "
              "put in its firebox.",
    stats=dict(hp=60, damage="3, burns (night creatures only)", speed="slow", eats="wood, coal"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
