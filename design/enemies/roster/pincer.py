"""Pincer: a small shore crab. A round shell, one big claw and one small, eyes on short stalks, stubby legs.

It is deliberately lopsided: a symmetric crab with both claws up reads as a space invader. The big claw leads when it
goes left or right (a crab walks sideways, so it shows its face, or its back, whichever way it goes).
  idle   the eyes glance the other way and back; the big claw clicks, then the small one
  walk   8 frames: the outer legs lift, then the inner, and the big claw bobs
  snap   it crouches, rears up with the big claw high and open (held: the warning), lunges and shuts it with a spark, holds, settles
"""
from art import G, edit, shift, pad, stamp

PAL = {"o": "7a3340", "r": "e0664a", "R": "b94a3f", "h": "f2906a", "c": "f3d8c5", "e": "2b1f2a", "w": "f4f0e6", "y": "fff1a8"}

FRONT = pad(G("""
.o.o..............
oroho...we.we.....
orrro...o..o...o.o
.oRo.ooooooooo.oro
..ooohhhhhhhhhooo.
...orrrrrrrrrrro..
...orrrrrrrrrrro..
...oRrrrroorrrRo..
..o.oRRcccccRRo.o.
.o.o.ooooooooo.o.o
.o.o...........o.o
"""), top=1, left=2)
BACK = edit(FRONT, {
    2: "..oroho...oR.oR.....",
    6: ".....orrhrrrrrhrro..",
    7: ".....orrrrrhrrrrro..",
    8: ".....oRrrrrrrrrRo...",
    9: "....o.oRRRRRRRRRo.o.",
})
SHADOW = ["...ssssssssssssssss."]
CLAW = dict(shut=[".....", ".ooo.", "orrro", ".oRo."],                       # stamped over the big claw, rows 1-4
            up=[".o.o.", "oroho", "orrro", ".oRo.", "..oo."])                # raised a pixel, rows 0-4
SMALL_SHUT = {3: None}                                                         # the small claw's tips close
LEGS = [{}, {-1: "..........o......o.o"}, {-1: "...o.o...........o.."}]      # all down; outer left and inner right up; the reverse


def crab(g, claw="open", small_shut=False, glance=False, legs=0, dx=0, dy=0, spark=False):
    if claw != "open":
        g = stamp(g, CLAW[claw], 2, 1 if claw == "shut" else 0)
    if small_shut:
        g = edit(g, {3: g[3][:17] + ".o."})
    if glance:
        g = edit(g, {2: g[2].replace("we", "ew")})
    g = edit(g, LEGS[legs])
    if spark:
        g = edit(g, {0: "y" + g[0][1:], 1: g[1][:1] + "y" + g[1][2:], 3: "y" + g[3][1:]})
    if dx or dy:
        g = shift(g, dx, dy)
    return g + SHADOW


def frames(g, lunge):
    c = lambda **kw: crab(g, **kw)
    return dict(idle=[c(), c(glance=True), c(glance=True), c(), c(claw="shut"), c(), c(small_shut=True), c()],
                walk=[c(legs=1, claw="up"), c(claw="up"), c(legs=2), c(), c(legs=1, claw="up"), c(claw="up"), c(legs=2), c()],
                act=[c(dy=1), c(claw="up", dy=-1), c(claw="shut", dx=lunge[0], dy=lunge[1], spark=True),
                     c(claw="shut", dx=lunge[0], dy=lunge[1]), c()])


ENEMY = dict(
    key="pincer", name="Pincer", pal=PAL, ground="sand", role="guard", cell=(24, 16), act="snap", stride=.8,
    ms=dict(idle=[800, 300, 300, 600, 140, 500, 140, 600], walk=80, act=[140, 420, 80, 220, 220]),
    where="beaches and river banks", when="day and night",
    behaviour="Small and quick. It walks sideways only, so it must turn its flank to chase you. Hits from the front bounce off its "
              "big claw; hit it from the other side or from behind. It buries itself in sand when hurt and comes back later.",
    stats=dict(hp=4, damage=2, speed="quick sideways, slow forward", drops="shell, claw meat"),
    dirs={"left": frames(FRONT, (-2, 0)), "down": frames(FRONT, (0, 1)), "up": frames(BACK, (0, -1))},
)
