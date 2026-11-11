"""Tusker: a wild boar. Long and low, seen in profile like the game's cow; tusks, a bristly mane, a wedge of a head.

Animation, after the game's cow: the body stays level and only the legs move, in diagonal pairs (near front with far hind).
Seen from the front or back, the weight rolls a pixel from side to side instead of bouncing.
The charge has a warning (it paws the ground and snorts, twice), then a gallop: legs flung out, legs gathered under.
"""
from art import G, edit, shift, mirror, nudge, pad, stack

PAL = {"o": "4a3240", "b": "947567", "d": "765a55", "m": "5e4450", "h": "ab8d7b", "p": "e8b5ac", "n": "c98a8a",
       "t": "f3f2c0", "e": "2b1f2a", "w": "ece6cc"}

BODY = G("""
..........o.o.o.o..........
.......oo.omomomoo.........
......odpoommmmmmmooooo....
....ooodpobbmmmmbbbbbbbo...
...obbboobbbbbbbbbbbbbbbo.o
..obbbbbbbbbbbbbbbbbbbbbboo
.obbebbbbbbbbbbbbbbbbbbbbo.
obbbbbbbbbbbdbbbbbbbbbbbbo.
opbbtbbbbbbddbbbbbbbbbbbdo.
oppotbbbddddbbbbbbbbbbbddo.
.oooobdddddbbbbbbbbbbbddo..
....odddddddddddddddddddo..
""")
TAIL_DOWN = edit(BODY, {4: "...obbboobbbbbbbbbbbbbbbo..", 6: ".obbebbbbbbbbbbbbbbbbbbbboo"})
BLINK = edit(BODY, {6: ".obbbbbbbbbbbbbbbbbbbbbbbo."})
SHADOW = G("....ssssssssssssssssssssss.")
TOP = "....oddoomooooooomoooddoo.."           # the belly line with the leg tops; the far legs (m) are darker
LEGS = dict(
    stand=G(TOP + "\n....oddoomo.....omo.oddo...\n....ooooooo.....ooo.oooo..."),
    a=G(TOP + "\n...oddo..omo...omo...oddo..\n..oooo....ooo.ooo.....oooo."),      # near front and far hind reach forward
    pass1=G(TOP + "\n....oddoooo.....omo.oooo...\n....oooo........ooo........"),    # far front and near hind lifted, swinging forward
    b=G(TOP + "\n..omooddo........oddoomo...\n.ooo..oooo.......oooo..ooo."),      # far front and near hind reach forward
    pass2=G(TOP + "\n....ooooomo.....ooo.oddo...\n........ooo.........oooo..."),    # near front and far hind lifted, swinging forward
    paw=G(TOP + "\n..oddo..omo.....omo.oddo...\n..ooo...ooo.....ooo.oooo..."),      # the near front hoof scrapes forward
    out=G("...oddoooddoooooooddooddo..\n..oddo....oddo...oddo..oddo\n..ooo......ooo...ooo....ooo"),   # gallop: flung out
    under=G(".....oddddooooooooddddo....\n......oddddo....oddddo.....\n.......oooo......oooo......"),  # gallop: gathered
)


def side(body, legs, puff="", dust="", dy=0):
    g = pad(stack(body, LEGS[legs], SHADOW), left=3)
    if dy:
        g = shift(g, 0, dy, keep=4)
        g = edit(g, {i - 4: r for i, r in enumerate(pad(stack(LEGS[legs], SHADOW), left=3))})
    marks = {}
    if puff:
        marks |= {8: puff + g[8][len(puff):], 9: ".w" + g[9][2:]}
    if dust:
        marks |= {-2: g[-2][:-len(dust)] + dust}
    return edit(g, marks)


FRONT = G("""
......o.o.o......
.oo..omomomo..oo.
oddoommmmmmmooddo
odpobbbmmmbbbopdo
.oobbbbbbbbbbboo.
.obbbbbbbbbbbbbo.
.obbebbbbbbbebbo.
obbbbbbbbbbbbbbbo
obbtopppppppotbbo
odbtopnpppnpotbdo
oddoopppppppooddo
.odddooooooodddo.
..oddo.....oddo..
..oooo.....oooo..
.sssssssssssssss.
""")
BACK = G("""
......o.o.o......
.oo..omomomo..oo.
oddoobmmmmmbooddo
.oobbbbmmmbbbboo.
.obbbbbmmmbbbbbo.
obbbbbbbmbbbbbbbo
obbbbbbbmbbbbbbbo
obbbbbbbobbbbbbbo
odbbbbbopobbbbbdo
oddbbbbboobbbbddo
.odddddddddddddo.
.odddooooooodddo.
..oddo.....oddo..
..oooo.....oooo..
.sssssssssssssss.
""")
LIFT = {-3: "..oooo.....oddo..", -2: "...........oooo.."}        # one foot off the ground


def facing(g):
    """Idle, walk and charge for the front or the back view: the feet alternate and the body rises a pixel as they pass."""
    g = pad(g, top=1, left=1, right=1)
    step = edit(g, {k: "." + v for k, v in LIFT.items()})          # one foot up...
    step = nudge(step, range(0, len(g) - 3), 1)                    # ...and the weight rolls onto the other: no bouncing, like the cow
    low = shift(g, 0, 1, keep=3)                                   # crouched, for the charge
    blink = [r.replace("e", "b") for r in g]
    dust = {-2: "w" + g[-2][1:-1] + "w"}
    return dict(idle=[g, blink], walk=[step, g, mirror(step), g],
                act=[low, edit(low, dust), low, edit(low, dust), edit(step, dust), low, edit(mirror(step), dust), low])


ENEMY = dict(
    key="tusker", name="Tusker", pal=PAL, role="charger", cell=(32, 32), act="charge", stride=1.6,
    ms=dict(idle=[1400, 160], walk=130, act=[170, 170, 170, 170, 90, 90, 90, 90]),
    where="forest and meadow", when="day",
    behaviour="Grazes and ignores you until you come within four tiles. Then it paws the ground and charges in a straight line. "
              "It cannot turn: step aside and it rams the next tree or wall and is stunned.",
    stats=dict(hp=10, damage=3, speed="slow, then very fast", drops="meat, hide, tusk"),
    dirs={"left": dict(idle=[side(BODY, "stand"), side(TAIL_DOWN, "stand")],
                       walk=[side(BODY, "a"), side(BODY, "pass1"), side(BODY, "b"), side(TAIL_DOWN, "pass2")],
                       act=[side(BODY, "paw", "w"), side(BODY, "stand", "ww"), side(BODY, "paw", "w"), side(BODY, "stand", "ww"),
                            side(BODY, "out", dust=".w", dy=1), side(BODY, "under", dust="ww"),
                            side(BODY, "out", dust="w.", dy=1), side(BODY, "under", dust=".w")]),
          "down": facing(FRONT), "up": facing(BACK)},
)
