"""Stag: the lord of the meadow. Tall, antlered, long-legged. Peaceful until you come too close.

Animation, as smooth as the player's: an 8-frame walk with generated legs (art.leg) in diagonal pairs, and the head and
antlers nodding once per step, as deer do. At rest it breathes, blinks and flicks an ear. When it has had enough of
you it lowers its antlers and stamps (held: the warning), then runs at you head down.
"""
from art import G, edit, leg, mirror, pad, shift

PAL = {"o": "6b3f3a", "b": "c98a5a", "d": "a86a48", "c": "f3e6c8", "k": "3a2a30", "e": "2b1f2a", "a": "e3c79a",
       "m": "8a5540", "w": "fbf6e6"}

TOP = G("""
...a..a.a..................
...a.a..a..................
....aa.a...................
.....aaa...................
......a..oo................
....ooooobo................
...obbbbboo................
..obbebbbbo................
.obbbbbbbbbo...............
.okbbooobbbo...............
..ooo..obbbbo..............
.......occbbbo.............
.......occbbbboooooooooo...
........ocbbbbbbbbbbbbbbo.w
........ocbbbbbbbbbbbbbbbwo
........occbbbbbbbbbbbbbbo.
.........occbbbbbbbbbbbddo.
.........ooccddddddddddddo.
..........oooooooooooooo...
""")
EAR_BACK = edit(TOP, {4: "......a....................", 5: "....oooooooo...............", 6: "...obbbbbobo..............."})
BLINK = [r.replace("e", "b") for r in TOP]
STRIDE = [(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (-1, 1)]     # a long, high-stepping stride
HIPS = dict(ff=(15, "m", None), fh=(21, "m", None), nf=(13, "b", "o"), nh=(23, "b", "o"))   # x, fill, edge; far legs first: thin, no outline
NOD = [0, 0, 1, 1, 0, 0, 1, 1]


def nod(g, n):
    """The head, neck and antlers (the left 12 columns, above the shoulders) sink n pixels."""
    out = [list(r) for r in g]
    for x in range(12):
        col = [g[r][x] for r in range(11)]
        for r in range(11 + n):
            out[r][x] = col[r - n] if r >= n else "."
    return ["".join(r) for r in out]


def side(step=None, top=TOP, head=0, pose=None, dust=""):
    g = pad(nod(top, head) if head else top, top=1, left=2, right=2) + ["." * 31] * 7 + ["." * 10 + "s" * 18 + "." * 3]
    for name, (x, fill, ink) in HIPS.items():
        ph = (0, 0) if step is None else STRIDE[(step + (0 if name in ("nf", "fh") else 4)) % 8]
        g = leg(g, x, 20, 6, (pose or {}).get(name, ph), w=1, fill=fill, ink=ink)
    if dust:
        g = edit(g, {-2: g[-2][:-len(dust)] + dust})
    return g


FRONT = G("""
a..a........a..a
a.a..........a.a
.aa..a....a..aa.
..a.a......a.a..
..aaa......aaa..
...a.oooooo.a...
..ooobbbbbbooo..
.obbobbbbbbobbo.
..ooobebbebooo..
....obbbbbbo....
....obbccbbo....
.....occcco.....
.....ockkco.....
....oooccooo....
...obbbccbbbo...
...obbbccbbbo...
...obbbbbbbbo...
...odbbbbbbdo...
...oddoooodbo...
...obo....obo...
...obo....obo...
...obo....obo...
...obo....obo...
...ooo....ooo...
..ssssssssssss..
""")
BACK = edit(FRONT, {8: "..ooobbbbbbooo..", 10: "....obbbbbbo....", 11: ".....obbbbo.....", 12: ".....obbbbo.....",
                    13: "....oobbbboo....", 14: "...obbbbbbbbo...", 15: "...obbbwwbbbo...", 16: "...obbwwwwbbo...",
                    17: "...odbbwwbbdo..."})
LIFT = {-3: "...ooo....obo...", -2: "..........ooo..."}        # the left foot off the ground


def facing(g):
    """Front or back. Like the player: a foot lifts as the body rises a pixel, then both are down and it sinks."""
    g = pad(g, top=2)
    step = edit(g, LIFT)
    low = shift(g, 0, 1, keep=5)                                  # the body sinks onto its legs
    lower = shift(g, 0, 2, keep=5)                                # antlers down
    blink = [r.replace("e", "b") for r in g]
    dust = {-2: "w" + g[-2][1:-1] + "w"}
    run = [step, step, low, low, mirror(step), mirror(step), low, low]
    return dict(idle=[g, g, low, low, g, blink, low, low], walk=run,
                act=[lower, edit(lower, dust), lower, edit(lower, dust)] + [edit(f, dust) if i % 2 == 0 else f for i, f in enumerate(run)])


PAW = dict(nf=(-2, 2))
ENEMY = dict(
    key="stag", name="Stag", pal=PAL, role="guardian", cell=(32, 32), act="charge", move="walk",
    ms=dict(idle=260, walk=90, act=[180, 180, 180, 180] + [55] * 8),
    where="deep forest clearings", when="dawn and dusk",
    behaviour="Rare, and not an enemy unless you make it one. It lets you watch from a distance and walks away if you follow. "
              "Come within two tiles, or hurt a deer nearby, and it lowers its antlers, stamps twice, and runs you down. "
              "Its antler is the best tool handle there is; it sheds one in winter if left alone.",
    stats=dict(hp=45, damage=12, speed="faster than you", drops="venison, hide, antler"),
    dirs={"left": dict(idle=[side(), side(), side(head=1), side(head=1), side(top=EAR_BACK), side(top=BLINK), side(head=1), side(head=1)],
                       walk=[side(i, head=NOD[i]) for i in range(8)],
                       act=[side(head=3, pose=PAW), side(head=3), side(head=3, pose=PAW), side(head=3)]
                           + [side(i, head=3, dust=[".w", "ww", "w.", ".."][i % 4]) for i in range(8)]),
          "down": facing(FRONT), "up": facing(BACK)},
)
