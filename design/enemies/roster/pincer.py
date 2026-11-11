"""Pincer: a shore crab. A flat, pointed shell, two raised claws, eyes on stalks, six jointed legs.

A crab walks sideways, so it always shows its face (or its back): going left or right it is the same crab, looking and
reaching that way. Animation: the shell stays level and the legs ripple through three positions, fast. At rest one claw
clicks, then the other. The snap: it rears up with both claws open and holds, then drops and shuts them, holds, settles.
"""
from art import G, edit, shift, pad

PAL = {"o": "7a3340", "r": "e0664a", "R": "b94a3f", "h": "f2906a", "c": "f3d8c5", "e": "2b1f2a", "w": "f4f0e6", "y": "fff1a8"}


def both(text):
    """The crab is symmetric: draw the left half, get the whole."""
    return pad([r + r[::-1] for r in G(text)], top=1)


FRONT = both("""
.o.o......oo..
oroho....oweo.
orrro.....oo..
.oRo...ooooooo
..oo..ohhhhhhh
...ooorrrrrrrr
..ooorrrrrrrrr
.o..ooRrrrrrrr
.o.o.ooRRrrrro
o..o.o.ooccccc
..o..o...ooooo
....o.........
...sssssssssss
""")
BACK = edit(FRONT, {
    2: "oroho....oRRo..oRRo....ohoro",
    7: "..ooorrhrrrrrrrrrrrrhrrooo..",
    8: ".o..ooRrrrrhrrrrhrrrrRoo..o.",
    9: ".o.o.ooRRrrrrrrrrrrRRoo.o.o.",
    10: "o..o.o.ooRRRRRRRRRRoo.o.o..o",
})
LEGS = [{},
        {10: None, 11: "...o.o...oooooooooo...o.o...", 12: ".....o................o....."},
        {10: None, 11: ".o...o...oooooooooo...o...o.", 12: "....o..................o...."}]
SHUT_L, SHUT_R = (".ooo......", "orrro....."), ("......ooo.", ".....orrro")


def crab(g, legs=0, shut="", look=0, spark=False):
    rows = {}
    if legs:
        a = g[10]
        left = [".o.o.o.", "o.o..o."][legs - 1]
        rows[10] = left + a[7:-7] + left[::-1]
        rows |= {k: v for k, v in LEGS[legs].items() if v}
    if "l" in shut:
        rows |= {1: SHUT_L[0] + g[1][10:], 2: SHUT_L[1] + g[2][10:]}
    if "r" in shut:
        rows |= {1: rows.get(1, g[1])[:-10] + SHUT_R[0], 2: rows.get(2, g[2])[:-10] + SHUT_R[1]}
    out = edit(g, rows)
    if look:                                             # both pupils to the left
        out = edit(out, {2: out[2].replace("oewo", "oweo")})
    if spark:
        out = edit(out, {0: "y.y" + out[0][3:-3] + "y.y"})
    return out


def frames(g, look=0):
    c = lambda **kw: crab(g, look=look, **kw)
    rear = shift(c(), 0, -1, keep=3)                     # up on its legs, claws open
    rear = edit(rear, {-4: c()[-4], -3: c()[-3], -2: c()[-2]})
    return dict(idle=[c(), c(shut="l"), c(), c(shut="r")],
                walk=[c(legs=1), c(legs=2), c(legs=1), c()],
                act=[rear, c(shut="lr", spark=True), c(shut="lr"), c()])


ENEMY = dict(
    key="pincer", name="Pincer", pal=PAL, ground="sand", role="guard", cell=(32, 16), act="snap", stride=.8,
    ms=dict(idle=[900, 130, 700, 130], walk=80, act=[420, 80, 220, 220]),
    where="beaches and river banks", when="day and night",
    behaviour="Walks sideways only, so it must turn its flank to chase you. Hits from the front bounce off its claws; "
              "hit it from the side or from behind. It buries itself in sand when hurt and comes back later.",
    stats=dict(hp=5, damage=2, speed="quick sideways, slow forward", drops="shell, claw meat"),
    dirs={"left": frames(FRONT, look=1), "down": frames(FRONT), "up": frames(BACK)},
)
