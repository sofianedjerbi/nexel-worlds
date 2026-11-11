"""Strawman: a scarecrow that gets off its pole. The only one shaped like a person: hat, sack head, arms straight out.

Animation: an 8-frame walk like the player's, but the arms never swing: that is what makes it wrong. Side-on the legs
are generated (art.leg). At rest it stands dead still and now and then its head tips. The grab: the arm goes up and
holds, then comes down as it drops forward, holds, and it straightens.
"""
from art import G, edit, pad, nudge, squat, shift, leg

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
    """Front or back. Like the player: a foot lifts as the body rises a pixel, then both are down and it sinks."""
    tall = lambda f: pad(f, top=1, left=1, right=1)
    low = lambda f: squat(tall(f), len(f) - 5)                   # both feet down: the legs lose a row, the body sinks
    twitch = nudge(tall(g), range(1, 13), 1)                     # the whole head tips to one side
    return dict(idle=[tall(g), tall(g), tall(g), twitch],
                walk=[tall(edit(g, LIFT_R)), tall(edit(g, LIFT_R)), low(g), low(g), tall(edit(g, LIFT_L)), tall(edit(g, LIFT_L)), low(g), low(g)],
                act=[tall(edit(g, up_arms)), low(edit(g, down_arms)), low(edit(g, down_arms)), tall(g)])


TOP = G("""
....oooooo....
...ohhhhhho...
...ohhhhhho...
.oooHHHHHHooo.
.ohhhhhhhhhho.
..oooooooooo..
...occccccCo..
...oecccccCo..
...occccCCCo..
...ooocccCCo..
....occcCCo...
.....ooooo....
....orrrrRo...
....oroorRo...
....ororoRo...
....ororoRo...
....oroyoRo...
....oyyoyyo...
""")
ARM_UP = {10: ".yo.occcCCo...", 11: "..oo.ooooo....", 12: "...ooorrrRo...", 13: "....orrrrRo...", 14: "....orrrrRo...",
          15: "....orrrrRo...", 16: "....orrrrRo..."}
ARM_DOWN = {13: ".oooorrrrRo...", 14: "yorrrrrrrRo...", 15: "yoooorrrrRo...", 16: "....orrrrRo..."}


def side(step=None, top=TOP, lean=0):
    """Facing left, upright, the near arm hanging. The legs are generated: the far one (darker) a half step behind the near."""
    g = pad(top, top=1, left=2, right=2) + ["." * 18] * 5 + ["...sssssssssss...."]
    g = leg(g, 9, 19, 3, (0, 0) if step is None else step + 4, w=2, fill="B", boot="y")
    g = leg(g, 7, 19, 3, (0, 0) if step is None else step, w=2, fill="b", boot="y")
    return shift(g, lean, 0, keep=1) if lean else g


def side_frames():
    grab = side(top=edit(TOP, ARM_DOWN), lean=-1)                # it drops forward as the arm comes down
    return dict(idle=[side(), side(), side(), side(top=nudge(TOP, range(0, 12), -1))],
                walk=[side(i) for i in range(8)],
                act=[side(top=edit(TOP, ARM_UP)), grab, grab, side()])


ENEMY = dict(
    key="strawman", name="Strawman", pal=PAL, role="stalker", cell=(32, 32), act="grab", stride=.9,
    ms=dict(idle=[900, 900, 500, 180], walk=110, act=[520, 90, 260, 300]),
    where="crop fields and old farms", when="night",
    behaviour="By day it is a scarecrow on a pole and does nothing. At night it steps down and walks, slowly, toward whoever is "
              "nearest, and only while nobody is looking at it. Look at it and it freezes. It tramples crops on its way. Fire ends it.",
    stats=dict(hp=8, damage=2, speed="slow, never stops", drops="straw, cloth, hat"),
    dirs={"left": side_frames(), "down": facing(DOWN, ARMS_UP, ARMS_DOWN), "up": facing(UP, ARMS_UP_BACK, ARMS_DOWN_BACK)},
)
