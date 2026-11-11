"""Pincer: a shore crab. Wide and flat, two raised claws, eyes on stalks; it walks sideways.

Animation: the shell stays level and the legs ripple through three positions, fast. At rest one claw clicks, then the other.
The snap: it rears up with both claws open and holds, then drops and shuts them, holds, and settles.
"""
from art import G, edit, shift, pad

PAL = {"o": "7a3340", "r": "e0664a", "R": "b94a3f", "h": "f2906a", "c": "f3d8c5", "e": "2b1f2a", "w": "f4f0e6", "y": "fff1a8"}

DOWN = pad(G("""
.o.o..............o.o.
oroho..oo....oo..ohoro
orrro.oweo..oweo.orrro
.oRo...oooooooo...oRo.
..oo.oohhhhhhhhoo.oo..
..oroorrrrrrrrrrooro..
...oorrrrrrrrrrrroo...
...orrrrrrrrrrrrrro...
...oRrrrrroorrrrrRo...
..o.oRRccccccccRRo.o..
.o.o.oooooooooooo.o.o.
.o.o..o........o..o.o.
...ssssssssssssssss...
"""), top=1)
UP = edit(DOWN, {
    3: "orrro.oRRo..oRRo.orrro",
    7: "...oorrrhrrrrhrrroo...",
    8: "...orrrrrrRRrrrrrro...",
    9: "...oRrrhrrrrrrhrrRo...",
    10: "..o.oRRRRRRRRRRRRo.o..",
})
LEGS = [{}, {-3: "o..o.oooooooooooo.o..o", -2: "o.o...o........o...o.o"}, {-3: "..oo.oooooooooooo.oo..", -2: ".o..o..o......o..o..o."}]
SHUT_L = {1: ".ooo..............o.o.", 2: "orrro..oo....oo..ohoro"}
SHUT_R = {1: ".o.o..............ooo.", 2: "oroho..oo....oo..orrro"}
SHUT = {1: ".ooo..............ooo.", 2: "orrro..oo....oo..orrro"}
SPARK = {0: "y.y................y.y"}

LEFT = pad(G("""
.o.o............
oroho..oo.......
orrro.oweo......
.oRo...oooooo...
..oo.oohhhhhho..
..oroorrrrrrrro.
...oorrrrrrrrro.
....orrrrrrrrRo.
....oRrrrrrrRRo.
....oRccccRRRo..
...o.oooooooo.o.
...o..o..o...o..
..ssssssssssss..
"""), top=1, left=1)
L_LEGS = [{}, {-3: "...o..oooooooo..o", -2: "...o.o...o.....o."}, {-3: "....oooooooooo.o.", -2: "...o...o..o....o."}]
L_SHUT = {1: "..ooo............", 2: ".orrro..oo......."}
L_SPARK = {0: "y.y.............."}


def frames(g, legs, shut, shut_l, shut_r, spark, lunge):
    rear = shift(g, 0, -1, keep=3)                       # up on its legs, claws open
    rear = edit(rear, {-4: g[-4], -3: g[-3], -2: g[-2]})   # the belly row again: the shell stands a pixel taller
    strike = shift(edit(g, shut), *lunge, keep=1)
    return dict(idle=[g, edit(g, shut_l), g, edit(g, shut_r)],
                walk=[edit(g, legs[1]), edit(g, legs[2]), edit(g, legs[1]), g],
                act=[rear, edit(strike, spark), strike, g])


ENEMY = dict(
    key="pincer", name="Pincer", pal=PAL, ground="sand", role="guard", cell=(32, 16), act="snap", stride=.8,
    ms=dict(idle=[900, 130, 700, 130], walk=80, act=[420, 80, 220, 220]),
    where="beaches and river banks", when="day and night",
    behaviour="Walks sideways only, so it must turn its flank to chase you. Hits from the front bounce off its claws; "
              "hit it from the side or from behind. It buries itself in sand when hurt and comes back later.",
    stats=dict(hp=5, damage=2, speed="quick sideways, slow forward", drops="shell, claw meat"),
    dirs={"left": frames(LEFT, L_LEGS, L_SHUT, L_SHUT, {}, L_SPARK, (-1, 0)),
          "down": frames(DOWN, LEGS, SHUT, SHUT_L, SHUT_R, SPARK, (0, 0)),
          "up": frames(UP, LEGS, SHUT, SHUT_L, SHUT_R, SPARK, (0, 0))},
)
