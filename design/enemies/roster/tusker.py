"""Tusker: a wild boar. Long and low, seen in profile like the game's cow; tusks, a bristly mane, a wedge of a head.

Animation, after the game's cow: an 8-frame walk at 90 ms, the body level, the legs generated (art.leg) and moving in
diagonal pairs (near front with far hind). Idle is a slow breath, a blink and a tail flick.
The charge has a warning (it paws the ground and snorts, twice), then a gallop: legs flung out, legs gathered under.
"""
from art import G, edit, shift, mirror, pad, leg

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
HIPS = dict(nf=(8, 3, "d"), ff=(13, 2, "m"), fh=(20, 2, "m"), nh=(24, 3, "d"))     # each leg: x, width, colour (far legs darker)


def side(body=BODY, step=None, pose=None, puff="", dust="", breathe=False):
    """The boar facing left. step: a frame of the walk (0-7), legs in diagonal pairs. pose: {leg: (dx, up)} for the charge."""
    rows = body[:-1] + [body[-2]] + body[-1:] if breathe else ["." * 27] + body       # breathing in: the barrel is a row deeper
    g = pad(rows, left=3, right=2) + ["." * 7 + "o" * 21 + "." * 4] + ["." * 32] * 3 + ["." * 6 + "s" * 22 + "." * 4]
    for name in ("ff", "fh", "nf", "nh"):                                                # far legs first, near legs over them
        x, w, fill = HIPS[name]
        ph = (0, 0) if step is None else step + (0 if name in ("nf", "fh") else 4)
        g = leg(g, x, 13, 3, (pose or {}).get(name, ph), w=w, fill=fill)
    if puff:
        g = edit(g, {9: puff + g[9][len(puff):], 10: ".w" + g[10][2:]})
    if dust:
        g = edit(g, {-2: g[-2][:-len(dust)] + dust})
    return g


PAW = dict(nf=(-3, 1))
OUT = dict(nf=(-3, 0), ff=(-2, 0), fh=(2, 0), nh=(3, 0))            # gallop: flung out
UNDER = dict(nf=(2, 1), ff=(1, 2), fh=(-1, 2), nh=(-2, 1))          # gallop: gathered under the body

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
obbbbbbbbbbbbbbbo
obbbbbbbbbbbbbbbo
obbbbbbbbbbbbbbbo
odbbbbbbmmbbbbbdo
oddbbbbbbmbbbbddo
.odddddddddddddo.
.odddooooooodddo.
..oddo.....oddo..
..oooo.....oooo..
.sssssssssssssss.
""")
LIFT = {-3: "..oooo.....oddo..", -2: "...........oooo.."}        # one foot off the ground


def facing(g):
    """Front or back view. Like the player: a foot lifts as the body rises a pixel, then both are down and it sinks."""
    g = pad(g, top=1, left=1, right=1)
    step = edit(g, {k: "." + v for k, v in LIFT.items()})          # one foot up, body at full height
    low = shift(g, 0, 1, keep=3)                                   # both feet down, body sunk a pixel
    blink = [r.replace("e", "b") for r in g]
    dust = {-2: "w" + g[-2][1:-1] + "w"}
    return dict(idle=[g, g, low, low, g, blink, low, low],
                walk=[step, step, low, low, mirror(step), mirror(step), low, low],
                act=[low, edit(low, dust), low, edit(low, dust), edit(step, dust), low, edit(mirror(step), dust), low])


ENEMY = dict(
    key="tusker", name="Tusker", pal=PAL, role="charger", cell=(32, 32), act="charge", stride=1.6,
    ms=dict(idle=260, walk=90, act=[170, 170, 170, 170, 90, 90, 90, 90]),
    where="forest and meadow", when="day",
    behaviour="Grazes and ignores you until you come within four tiles. Then it paws the ground and charges in a straight line. "
              "It cannot turn: step aside and it rams the next tree or wall and is stunned.",
    stats=dict(hp=10, damage=3, speed="slow, then very fast", drops="meat, hide, tusk"),
    dirs={"left": dict(idle=[side(), side(), side(breathe=True), side(breathe=True),
                             side(TAIL_DOWN), side(BLINK), side(breathe=True), side(breathe=True)],
                       walk=[side(step=i) for i in range(8)],
                       act=[side(pose=PAW, puff="w"), side(puff="ww"), side(pose=PAW, puff="w"), side(puff="ww"),
                            side(pose=OUT, dust=".w"), side(pose=UNDER, dust="ww"), side(pose=OUT, dust="w."), side(pose=UNDER, dust=".w")]),
          "down": facing(FRONT), "up": facing(BACK)},
)
