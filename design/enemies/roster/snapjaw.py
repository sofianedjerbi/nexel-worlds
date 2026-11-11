"""Snapjaw: a pike. It lives in water: all you see is a fin and a wake, until it jumps.

Animation: the fin rides level and dips a pixel while the wake flickers behind it. The leap: the fin goes under and
bubbles rise (hold: that is the warning), then the fish comes half out, hangs at the top with its jaws open, falls
back with them shut, and leaves a splash.
"""
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
WAKE_LEFT = {-2: "wwWwwwwwwwwwWw", -1: "..ww.WW.www..W"}
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
""")
SHUT_LEFT = edit(LEAP_LEFT, {5: "oooooggggggggggccggggGoofo", 6: "ottttogccccccccccccggoffo.", 7: ".ooooooccccccccccoooo.ofo."})
SPLASH_WIDE = G("""
...w..ww..........ww..w...
..wWwwWWWww.....wwWWww.Ww.
""")
SPLASH_BIG = G("""
..w...w..w.......w..w...w.
.wWWwwwWWWWww..wwWWWWwwWWw
""")
BUBBLES_WIDE = G("""
.........w......w.........
............w.............
......wwWWwwwwwwWWww......
.......ww.WWWWWW.ww.......
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
""")
SHUT_DOWN = edit(LEAP_DOWN, {4: ".oggooooooggo.", 5: ".ogottttttogo.", 6: ".ogottttttogo.", 7: "..oooooooooo.."})
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
""")
SHUT_UP = edit(LEAP_UP, {0: "..............", 1: ".oo......oo...", 2: "offo....offo..", 3: ".offfooofffo.."})
SPLASH = G("""
.w..oooooo..w.
wWww.WWWW.wwWw
.wwWWwwwwWWww.
""")
SPLASH_FLAT = G("""
.w..........w.
wWww.WWWW.wwWw
.wwWWwwwwWWww.
""")
BUBBLES = G("""
....w....w....
.......w......
..wwWWwwWWww..
...ww.WW.ww...
""")


def swim(fin, above, wake):
    """Four frames: the fin level, then dipped a pixel (its top row goes under), each with the wake in two states."""
    dipped = ["." * len(fin[0])] + fin[:above - 1] + fin[above:]
    return [fin, wake(fin), dipped, wake(dipped)]


def leap(fish, shut, splash, big, bubbles, rows):
    w = len(fish[0])
    air = ["." * w] * 2
    return [bubbles, fish[:rows] + splash, fish + air + splash, shut[:rows] + big, big]


ENEMY = dict(
    key="snapjaw", name="Snapjaw", pal=PAL, ground="water", role="lurker", cell=(32, 16), act="leap", stride=1.6,
    ms=dict(idle=260, walk=160, act=[480, 80, 240, 90, 320]),
    where="deep water, rivers", when="day and night",
    behaviour="A fin that circles in deep water. It cannot leave the water, but it jumps at anything on the tile beside it: "
              "a swimmer, a boat, someone fishing from the bank. Bridges two tiles wide are safe. Bait pulls it away.",
    stats=dict(hp=7, damage=3, speed="fast, water only", drops="big fish, scales"),
    dirs={"left": (lambda s: dict(idle=s, walk=s, act=leap(LEAP_LEFT, SHUT_LEFT, SPLASH_WIDE, SPLASH_BIG, BUBBLES_WIDE, 5)))(
              swim(FIN_LEFT, 4, lambda g: edit(g, WAKE_LEFT))),
          "down": (lambda s: dict(idle=s, walk=s, act=leap(LEAP_DOWN, SHUT_DOWN, SPLASH, SPLASH_FLAT, BUBBLES, 5)))(
              swim(FIN_DOWN, 5, mirror)),
          "up": (lambda s: dict(idle=s, walk=s, act=leap(LEAP_UP, SHUT_UP, SPLASH, SPLASH_FLAT, BUBBLES, 5)))(
              swim(FIN_UP, 4, mirror))},
)
