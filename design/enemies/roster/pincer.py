"""Pincer: a shore crab. Wide and flat, two raised claws, eyes on stalks; it walks sideways."""
from art import G, edit

PAL = {"o": "7a3340", "r": "e0664a", "R": "b94a3f", "h": "f2906a", "c": "f3d8c5", "e": "2b1f2a", "w": "f4f0e6"}

DOWN = G("""
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
""")
LEGS2 = {-3: "o..o.oooooooooooo.o..o", -2: "o.o...o........o...o.o"}
SNAP = {0: ".ooo..............ooo.", 1: "orrro..oo....oo..orrro"}
UP = edit(DOWN, {
    2: "orrro.oRRo..oRRo.orrro",
    6: "...oorrrhrrrrhrrroo...",
    7: "...orrrrrrRRrrrrrro...",
    8: "...oRrrhrrrrrrhrrRo...",
    9: "..o.oRRRRRRRRRRRRo.o..",
})
LEFT = G("""
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
""")
LEFT_LEGS2 = {-3: "..o..oooooooo..o", -2: "..o.o...o.....o."}
LEFT_SNAP = {0: ".ooo............", 1: "orrro..oo......."}

ENEMY = dict(
    key="pincer", name="Pincer", pal=PAL, ground="sand", role="guard", cell=(32, 16), fps=dict(walk=7, act=5), act="snap",
    where="beaches and river banks", when="day and night",
    behaviour="Walks sideways only, so it must turn its flank to chase you. Hits from the front bounce off its claws; "
              "hit it from the side or from behind. It buries itself in sand when hurt and comes back later.",
    stats=dict(hp=5, damage=2, speed="quick sideways, slow forward", drops="shell, claw meat"),
    dirs={"left": dict(walk=[LEFT, edit(LEFT, LEFT_LEGS2)], act=[LEFT, edit(LEFT, LEFT_SNAP)]),
          "down": dict(walk=[DOWN, edit(DOWN, LEGS2)], act=[DOWN, edit(DOWN, SNAP)]),
          "up": dict(walk=[UP, edit(UP, LEGS2)], act=[UP, edit(UP, SNAP)])},
)
