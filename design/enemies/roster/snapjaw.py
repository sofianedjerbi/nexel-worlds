"""Snapjaw: a pike. It lives in water: all you see is a fin and a wake, until it jumps."""
from art import G, edit, mirror

PAL = {"o": "2f4858", "g": "7fb5a8", "G": "4f8a8c", "c": "ecebd0", "f": "e0885a", "w": "f2fbfb", "W": "bfe3ea",
       "e": "f6c45a", "k": "2b2236", "t": "f4f0e6", "m": "a03c4a"}

FIN_LEFT = G("""
.....oo.......
....offo......
...offGGo.....
..offGGGGo....
.wofGGGGGGow..
wWwwwwwwwwwWww
.ww..WWW..ww.W
""")
FIN_LEFT2 = edit(FIN_LEFT, {-2: "wwWwwwwwwwwwWw", -1: "..ww.WW.www..W"})
LEAP_LEFT = G("""
.........ooooooo..........
......ooofffGGGGooo.......
....ooGGGGGGGGGGGGGoo.....
..ooGGGGggggggggGGGGGo....
.oGGekgggggggggggggGGGo.oo
otttoggggggggggccggggGoofo
.ommmogccccccccccccggoffo.
.ottttoccccccccccoooo.ofo.
..ooooooooofoooooo.....oo.
..........oo..............
...w..ww..........ww..w...
..wWwwWWWww.....wwWWww.Ww.
""")
LEAP_LEFT2 = edit(LEAP_LEFT, {
    5: "oooooggggggggggccggggGoofo",
    6: "ottttogccccccccccccggoffo.",
    7: ".ooooooccccccccccoooo.ofo.",
    -2: "..w...w..w.......w..w...w.",
    -1: ".wWWwwwWWWWww..wwWWWWwwWWw",
})
FIN_DOWN = G("""
.w..........w.
..w...oo...w..
..w..ofGo..w..
.....ofGo.....
....offGGo....
.w..offGGo..w.
wWwwwwwwwwwwWw
.ww.WW..WW.ww.
""")
FIN_UP = G("""
......oo......
.....ofGo.....
.....ofGo.....
....offGGo....
.w..offGGo..w.
wWwwwwwwwwwwWw
.ww.WW..WW.ww.
..w........w..
.w..........w.
""")
LEAP_DOWN = G("""
....oooooo....
...oGGGGGGo...
..oGggggggGo..
.oekggggggkeo.
.ogottttttogo.
.ogommmmmmogo.
.ogommmmmmogo.
..oottttttoo..
...occcccco...
.w..oooooo..w.
wWww.WWWW.wwWw
.wwWWwwwwWWww.
""")
LEAP_DOWN2 = edit(LEAP_DOWN, {4: ".oggooooooggo.", 5: ".ogottttttogo.", 6: ".ogottttttogo.", 7: "..oooooooooo.."})
LEAP_UP = G("""
..oo......oo..
.offo....offo.
.offfo..offfo.
..offfoofffo..
...offGGffo...
....oGGGGo....
....oGggGo....
...oGggggGo...
...oGggggGo...
.w..oooooo..w.
wWww.WWWW.wwWw
.wwWWwwwwWWww.
""")
LEAP_UP2 = edit(LEAP_UP, {0: "..............", 1: ".oo......oo...", 2: "offo....offo..", 3: ".offfooofffo.."})

ENEMY = dict(
    key="snapjaw", name="Snapjaw", pal=PAL, ground="water", role="lurker", cell=(32, 16), fps=dict(walk=4, act=4), act="leap",
    where="deep water, rivers", when="day and night",
    behaviour="A fin that circles in deep water. It cannot leave the water, but it jumps at anything on the tile beside it: "
              "a swimmer, a boat, someone fishing from the bank. Bridges two tiles wide are safe. Bait pulls it away.",
    stats=dict(hp=7, damage=3, speed="fast, water only", drops="big fish, scales"),
    dirs={"left": dict(walk=[FIN_LEFT, FIN_LEFT2], act=[LEAP_LEFT, LEAP_LEFT2]),
          "down": dict(walk=[FIN_DOWN, mirror(FIN_DOWN)], act=[LEAP_DOWN, LEAP_DOWN2]),
          "up": dict(walk=[FIN_UP, mirror(FIN_UP)], act=[LEAP_UP, LEAP_UP2])},
)
