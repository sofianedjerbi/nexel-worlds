"""Strawman: a scarecrow that gets off its pole. The only one shaped like a person: hat, sack head, arms straight out.

Animation: a stiff shamble. Seen from the front, one foot lifts and the whole upper body leans over the other, then straightens.
The arms never swing: that is what makes it wrong. At rest it only twitches its head. The grab: both arms go up and
hold, then come down as it drops forward, hold, and it straightens.
"""
from art import G, edit, pad, nudge, squat, shift

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
UP = edit(DOWN, {7: "...occccccCCo...", 8: "...occcggcCCo...", 9: "...occccccCCo...",
                 13: "yorrrrrrrrrrrRoy", 14: "yoooorrrrrRRoooy", 16: "....orrgrRRRo..."})
LIFT_R = {-5: "....obbo.oooo...", -4: "....oooo.oyyo...", -3: "....oyyo.oooo...", -2: "....oooo........"}
LIFT_L = {-5: "....oooo.oBBo...", -4: "....oyyo.oooo...", -3: "....oooo.oyyo...", -2: ".........oooo..."}
ARMS_UP = {9: "y..ocoocoocCo..y", 10: "yo..occccCCo..oy", 11: ".oo..oooooo..oo.", 12: "..ooorrrrrrooo..",
           13: "...orrrgrrrrRo..", 14: "....orrggrRRo..."}
ARMS_UP_BACK = ARMS_UP | {9: "y..occccccCCo..y", 13: "...orrrrrrrrRo..", 14: "....orrrrrRRo..."}
ARMS_DOWN = {12: "...oorrrrrrrroo.", 13: "..oroorgrrrrooro", 14: ".oro.orggrRo.oro", 15: ".oyo.orrrRRo.oyo", 16: "..o..orrrRRo..o."}
ARMS_DOWN_BACK = ARMS_DOWN | {13: "..oroorrrrrrooro", 14: ".oro.orrrrRo.oro"}


def facing(g, up_arms, down_arms):
    low = lambda f: squat(f, len(f) - 6)                         # both feet down: the legs lose a row, the body sinks
    tall = lambda f: pad(f, top=1, left=1, right=1)
    return dict(idle=[tall(g), nudge(tall(g), range(1, 7), 1)],
                walk=[nudge(tall(edit(g, LIFT_R)), range(1, 19), -1), tall(g), nudge(tall(edit(g, LIFT_L)), range(1, 19), 1), tall(g)],
                act=[tall(edit(g, up_arms)), low(tall(edit(g, down_arms))), low(tall(edit(g, down_arms))), tall(g)])


LEFT = pad(G("""
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
"""), left=1, right=1)
STRIDE = {-6: "....obboBBo...", -5: "...obbo.oBBo..", -4: "...oooo.oooo..", -3: "..oyyo..oyyo..", -2: "..oooo..oooo.."}
STRIDE2 = {k: v.replace("bb", "xx").replace("BB", "bb").replace("xx", "BB") for k, v in STRIDE.items()}   # the other leg leads
ARM_UP = {10: ".yo.occcCCo...", 11: "..oo.ooooo....", 12: "...ooorrrro...", 13: "....orrrrRo...", 14: ".....orrrRo..."}
ARM_DOWN = {12: ".....orrrro...", 13: "...ooorrrRo...", 14: ".yorrrorrRo...", 15: ".yoooorrRRo..."}


def side(g):
    tall = lambda f: pad(f, top=1)
    low = lambda f: squat(tall(f), len(f) - 6)
    grab = shift(low(edit(g, ARM_DOWN)), -1, 0, keep=1)          # it drops forward as the arm comes down
    return dict(idle=[tall(g), tall(nudge(g, range(0, 6), -1))],
                walk=[low(edit(g, STRIDE)), tall(g), low(edit(g, STRIDE2)), tall(g)],
                act=[tall(edit(g, ARM_UP)), grab, grab, tall(g)])


ENEMY = dict(
    key="strawman", name="Strawman", pal=PAL, role="stalker", cell=(32, 32), act="grab", stride=.9,
    ms=dict(idle=[2200, 160], walk=180, act=[520, 90, 260, 300]),
    where="crop fields and old farms", when="night",
    behaviour="By day it is a scarecrow on a pole and does nothing. At night it steps down and walks, slowly, toward whoever is "
              "nearest, and only while nobody is looking at it. Look at it and it freezes. It tramples crops on its way. Fire ends it.",
    stats=dict(hp=8, damage=2, speed="slow, never stops", drops="straw, cloth, hat"),
    dirs={"left": side(LEFT), "down": facing(DOWN, ARMS_UP, ARMS_DOWN), "up": facing(UP, ARMS_UP_BACK, ARMS_DOWN_BACK)},
)
