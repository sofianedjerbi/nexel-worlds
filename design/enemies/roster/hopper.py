"""Hopper: a marsh frog the size of a chicken. It does not walk: it hops.

Every frame is computed. One hop is 8 frames: crouch, push off (stretched, legs out behind), rise, peak, fall, land
(squashed), recover. The shadow stays on the ground and shrinks as it rises. At rest its throat pulses and it blinks.
Its action is the tongue: it leans back with its mouth open (the warning, held), then the tongue is out in one frame.
"""
from art import canvas, dot, ell, ground, part

PAL = {"o": "2f6672", "g": "74c9bd", "d": "4aa3a0", "c": "f4f3c4", "e": "2b2a3a", "y": "fff6b0", "p": "f08a9a", "P": "d9607a",
       "m": "7a3a4a"}
W, H, CX, BASE = 30, 26, 15, 24                       # BASE: the row the feet stand on
LIFT = [0, 0, 3, 6, 7, 5, 2, 0]
STRETCH = [-1, 1, 1, 0, 0, 0, 1, -1]
LEGS_OUT = [0, 1, 1, 1, 1, 0, 0, 0]


def frame(facing, lift=0, s=0, out=False, tongue=0, mouth=False, blink=False, throat=False):
    c = canvas(W, H)
    rx, ry = 6 - .6 * s, 4 + .6 * s
    cy = BASE - ry - lift + .5
    side = facing == "left"
    if side:
        if out:                                                    # hind leg flung out behind, in the air
            for t in range(4):
                ell(c, CX + 4 + t, cy + 1.5 + t * .7, 1.6, 1.6, "d")
            for x in (CX + 8, CX + 9):
                dot(c, x, cy + 4.6, "d")
        ell(c, CX, cy, rx, ry, "g")
        ell(c, CX - 1.5, cy + 2.2, rx - 1.6, ry - 1.6, "c", on="g")   # the pale belly
        ell(c, CX - 3, cy - ry + .8, 2, 2, "g")                       # the eye bump
        if not out:
            ell(c, CX + 4, cy + ry - 2.2, 3, 2.4, "d")                # the folded hind leg, and its long foot
            for x in range(CX + 1, CX + 8):
                dot(c, x, BASE - lift, "d")
        for y in range(2):                                         # the front leg
            dot(c, CX - 4 - (1 if out else 0), cy + ry - 1 + y + (0 if out else .5), "d")
        if throat:
            ell(c, CX - 5, cy + 1.5, 1.6, 1.6, "c")
    else:
        for sx in (-1, 1):
            if out:
                for t in range(4):                                 # legs dangling under it, feet turned out
                    for x in ((-5, -4) if sx < 0 else (3, 4)):
                        c[min(BASE, int(cy + ry) - 1 + t)][CX + x] = "d"
                c[min(BASE, int(cy + ry) + 2)][CX + (-6 if sx < 0 else 5)] = "d"
            else:
                ell(c, CX + sx * 5.5, cy + ry - 2.2, 2.4, 2.6, "d")
                for x in (5, 6, 7):
                    dot(c, CX + sx * x - (.5 if sx < 0 else -.5) - .5, BASE - lift, "d")
        ell(c, CX, cy, rx, ry, "g")
        for sx in (-1, 1):
            ell(c, CX + sx * 3.2, cy - ry + .8, 2, 2, "g")
        if facing == "down":
            ell(c, CX, cy + 2, rx - 1.8, ry - 1.4 + (1 if throat else 0), "c", on="g")
            for x in (CX - 3, CX + 2):
                dot(c, x, BASE - lift, "d")
        else:
            for x, y in ((-1, 0), (0, 1), (-2, 2), (1, 2)):           # spots down its back
                dot(c, CX + x, cy - 1 + y, "d", on="g")
    g = [list(r) for r in part(c)]
    ey = round(cy - ry + .3)
    if side:
        g[ey][CX - 4] = "g" if blink else "e"
        if mouth or tongue:
            for x in range(CX - 6, CX - 3):
                dot(g, x, cy + .5, "m", on="gco")
        for t in range(tongue):
            dot(g, CX - 7 - t, cy + .5, "p")
        if tongue:
            dot(g, CX - 7 - tongue, cy + .5, "P"); dot(g, CX - 7 - tongue, cy - .5, "P"); dot(g, CX - 6 - tongue, cy - .5, "P")
    elif facing == "down":
        for x in (CX - 4, CX + 3):
            g[ey + 1][x] = "g" if blink else "e"
        if mouth or tongue:
            for x in range(CX - 2, CX + 2):
                dot(g, x, cy + .2, "m")
        for t in range(tongue):
            dot(g, CX - 1, cy + 1.2 + t, "p"); dot(g, CX, cy + 1.2 + t, "p")
        if tongue:
            for x in (CX - 2, CX - 1, CX, CX + 1):
                dot(g, x, cy + 1.2 + tongue, "P")
    elif tongue:                                                   # seen from behind: the tongue goes up, past its head
        top = round(cy - ry) - 2
        for t in range(tongue):
            dot(g, CX - 1, top - t, "p"); dot(g, CX, top - t, "p")
        for x in (CX - 2, CX - 1, CX, CX + 1):
            dot(g, x, top - tongue, "P")
    return ground(g, CX, 12 - lift)


def frames(d):
    up = 4 if d == "down" else 0                                    # towards the camera it rears up, so the tongue has room
    idle = [frame(d, throat=t, blink=b, s=-1 if t else 0) for t, b in ((0, 0), (0, 0), (1, 0), (1, 0), (0, 0), (0, 1), (1, 0), (1, 0))]
    return dict(idle=idle, walk=[frame(d, lift=LIFT[i], s=STRETCH[i], out=LEGS_OUT[i]) for i in range(8)],
                act=[frame(d, s=-1, mouth=True, throat=True), frame(d, lift=up, s=1, tongue=7, out=bool(up)),
                     frame(d, lift=up, s=1, tongue=7, out=bool(up)), frame(d, lift=up // 2, tongue=3, mouth=True), frame(d)])


ENEMY = dict(
    key="hopper", name="Hopper", pal=PAL, role="thief", cell=(32, 32), act="tongue", move="hop",
    ms=dict(idle=240, walk=80, act=[450, 70, 180, 110, 220]),
    where="marsh, pond edges, wet fields after rain", when="day, louder at dusk",
    behaviour="Sits by the water and croaks. It moves only in hops, one tile at a time, with a pause between. It does not "
              "bite: its tongue snatches the item you hold (or one crop from a field) from two tiles away, and it hops off with it. "
              "Catch it within a few seconds and it drops what it took.",
    stats=dict(hp=6, damage=0, speed="a tile per hop, faster than you in bursts", drops="frog leg, whatever it stole"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
