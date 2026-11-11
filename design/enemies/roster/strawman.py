"""Strawman: a scarecrow that gets off its pole. The only one shaped like a person: hat, sack head, arms straight out."""
from art import G, edit

PAL = {"o": "5b3f36", "h": "b98a5e", "H": "8e3f3c", "c": "e8d9b0", "C": "cdb98a", "r": "b5544a", "R": "8e3f3c",
       "b": "5f6f9a", "B": "47557a", "y": "e8cf7a", "g": "97bb8e", "e": "2b1f2a"}

DOWN = G("""
.....oooooo.....
....ohhhhhho....
....ohhhhhho....
.oooohHHHHhoooo.
ohhhhhhhhhhhhhho
.oooooooooooooo.
...occccccCCo...
...ocecccceCo...
...occccccCCo...
...ocoocoocCo...
....occccCCo....
.....oooooo.....
yoooorrrrrrooooy
yorrrrrgrrrrrRoy
yoooorrggrRRoooy
....orrrrrRRo...
....orrrrRRRo...
....oyyoyyoyo...
....obbbbbBBo...
....obbo.oBBo...
....obbo.oBBo...
....oooo.oooo...
....oyyo.oyyo...
....oooo.oooo...
...sssssssssss..
""")
STEP = {-5: "....obbo.oooo...", -4: "....oooo.oyyo...", -3: "....oyyo.oooo...", -2: "....oooo........"}
ARMS_UP = {9: "y..ocoocoocCo..y", 10: "yo..occccCCo..oy", 11: ".oo..oooooo..oo.", 12: "..ooorrrrrrooo..",
           13: "...orrrgrrrrRo..", 14: "....orrggrRRo..."}
UP = edit(DOWN, {7: "...occccccCCo...", 8: "...occcggcCCo...", 9: "...occccccCCo...",
                 13: "yorrrrrrrrrrrRoy", 14: "yoooorrrrrRRoooy", 16: "....orrgrRRRo..."})
UP_ARMS = edit(UP, ARMS_UP | {9: "y..occccccCCo..y", 13: "...orrrrrrrrRo..", 14: "....orrrrrRRo..."})

LEFT = G("""
...oooooo...
..ohhhhhho..
..ohhhhhho..
oooHHHHHhooo
ohhhhhhhhhho
.oooooooooo.
..occccccCo.
..oecccccCo.
..occccCCCo.
..ooocccCCo.
...occcCCo..
....ooooo...
yoooorrrro..
yorrrrrrRo..
yooooorrRo..
....orrRRo..
....orrRRo..
....oyoyyo..
....obbBBo..
....obbBBo..
....obbBBo..
....ooooo...
...oyyyyo...
...oooooo...
..sssssssss.
""")
LEFT_STEP = {-6: "...obboBBo..", -5: "..obbo.oBBo.", -4: "..oooo.oooo.", -3: ".oyyo..oyyo.", -2: ".oooo..oooo."}
LEFT_ARM = {10: "yo.occcCCo..", 11: ".oo.ooooo...", 12: "..ooorrrro..", 13: "...orrrrRo..", 14: "....orrrRo.."}

ENEMY = dict(
    key="strawman", name="Strawman", pal=PAL, role="stalker", cell=(32, 32), fps=dict(walk=3, act=3), act="grab",
    where="crop fields and old farms", when="night",
    behaviour="By day it is a scarecrow on a pole and does nothing. At night it steps down and walks, slowly, toward whoever is "
              "nearest, and only while nobody is looking at it. Look at it and it freezes. It tramples crops on its way. Fire ends it.",
    stats=dict(hp=8, damage=2, speed="slow, never stops", drops="straw, cloth, hat"),
    dirs={"left": dict(walk=[LEFT, edit(LEFT, LEFT_STEP)], act=[LEFT, edit(LEFT, LEFT_ARM)]),
          "down": dict(walk=[DOWN, edit(DOWN, STEP)], act=[DOWN, edit(DOWN, ARMS_UP)]),
          "up": dict(walk=[UP, edit(UP, STEP)], act=[UP, UP_ARMS])},
)
