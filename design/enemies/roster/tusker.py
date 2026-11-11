"""Tusker: a wild boar. Long and low, seen in profile like the game's cow; tusks, a bristly mane, a wedge of a head."""
from art import G, edit, shift

PAL = {"o": "4a3240", "b": "947567", "d": "765a55", "m": "5e4450", "h": "ab8d7b", "p": "e8b5ac", "n": "c98a8a",
       "t": "f3f2c0", "e": "2b1f2a", "w": "ece6cc"}

LEFT = G("""
..........o.o.o.o.........
.......oo.omomomoo........
......odpoommmmmmmooooo...
....ooodpobbmmmmbbbbbbbo..
...obbboobbbbbbbbbbbbbbbo.o
..obbbbbbbbbbbbbbbbbbbbbboo
.obbebbbbbbbbbbbbbbbbbbbbo.
obbbbbbbbbbbdbbbbbbbbbbbbo.
opbbtbbbbbbddbbbbbbbbbbbdo.
oppotbbbddddbbbbbbbbbbbddo.
.oooobdddddbbbbbbbbbbbddo..
....odddddddddddddddddddo..
.....oddoddooooooddoddoo...
.....oddoddo.....oddoddo...
.....oooooo......ooooooo...
....ssssssssssssssssssssss.
""")
LEFT2 = edit(LEFT, {
    -4: "....oddooddoooooddooddo....",
    -3: "....oddo.oddo...oddo.oddo..",
    -2: "....oooo.oooo...oooo.oooo..",
})
RUN = edit(shift(LEFT, 0, 1, keep=4), {
    -4: "...oddoooddoooooooddooddow.",
    -3: "..oddo....oddo...oddo..oddo",
    -2: "..ooo......ooo...ooo....ooo",
    -1: "....ssssssssssssssssssss.ww",
})
RUN2 = edit(LEFT, {
    -4: ".....oddddooooooooddddo..w.",
    -3: "......oddddo....oddddo..www",
    -2: ".......oooo......oooo....w.",
})

DOWN = G("""
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
DOWN2 = edit(shift(DOWN, 0, 1, keep=3), {-3: "..oddo.....oooo..", -2: "..oooo..........."})
UP = G("""
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
..oddoooooooddo..
..oddo.....oddo..
..oooo.....oooo..
.sssssssssssssss.
""")
UP2 = edit(shift(UP, 0, 1, keep=3), {-3: "..oooo.....oddo..", -2: "...........oooo.."})

ENEMY = dict(
    key="tusker", name="Tusker", pal=PAL, role="charger", cell=(32, 32), fps=dict(walk=5, act=9), act="charge",
    where="forest and meadow", when="day",
    behaviour="Grazes and ignores you until you come within four tiles. Then it paws the ground and charges in a straight line. "
              "It cannot turn: step aside and it rams the next tree or wall and is stunned.",
    stats=dict(hp=10, damage=3, speed="slow, then very fast", drops="meat, hide, tusk"),
    dirs={"left": dict(walk=[LEFT, LEFT2], act=[RUN, RUN2]),
          "down": dict(walk=[DOWN, DOWN2], act=[edit(DOWN, {-2: "w.oooo.....oooo.w"}), edit(DOWN2, {-4: "wodddooooooodddow"})]),
          "up": dict(walk=[UP, UP2], act=[edit(UP, {-2: "w.oooo.....oooo.w"}), edit(UP2, {-4: "w.oddoooooooddo.w"})])},
)
