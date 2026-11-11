"""Adder: a grass snake. No legs, no face to speak of: one long wave on the ground."""
from art import G, edit, mirror

PAL = {"o": "3a4a3a", "g": "9ccf62", "G": "6ba04e", "k": "3f7040", "e": "2b1f2a", "t": "e0504a", "w": "f4f0e6"}

LEFT = G("""
...oooo...................
..oggggo.....ooooo........
..oeggggo..ooggkggoo......
..oggGgggoogggGGGgkgo...oo
...ooooGgggkgGooooGggo.ogo
.......oGGGGGo....oGgkogGo
........ooooo......oGgggo.
....................oooo..
....ssssssssssssssssssss..
""")
LEFT2 = G("""
...oooo............oooo...
..oggggo.........ooggkgo..
..oeggggo.......ogggGGggo.
ttoggGgggoo....oggGoooGgo.
...ooooGggkgooogkGo..oGgo.
.......oGGgggkgggo...ogGo.
........ooGGGGGoo....ooo..
..........ooooo...........
....ssssssssssssssssssss..
""")
STRIKE = edit(LEFT, {
    0: "oooooo....................",
    1: "oegggggoo....ooooo........",
    2: "owttoggggo.ooggkggoo......",
    3: ".oooogggggogggGGGgkgo...oo",
})
DOWN = G("""
....oo......
...ogGo.....
...ogGo.....
....ogGooo..
....ogggGGo.
.....ooogGGo
...ooooogGGo
..ogggggGGo.
.oggGGooooo.
.ogGoo......
.ogggggoo...
..oGGgggGo..
...ooooggGo.
....ooogggo.
...oggggggo.
...oeggggeo.
...oggggggo.
....oggggo..
.....oooo...
..ssssssss..
""")
DOWN_BITE = edit(DOWN, {-4: "...owttttwo.", -3: "....ottto...", -2: ".....ooo...."})
_up = [r.replace("e", "g") for r in DOWN[:-1][::-1]]
UP = _up + DOWN[-1:]

ENEMY = dict(
    key="adder", name="Adder", pal=PAL, role="ambusher", cell=(32, 24), fps=dict(walk=5, act=4), act="strike",
    where="tall grass, crop fields", when="day",
    behaviour="Lies in tall grass where you cannot see it, and only the grass moves. Step next to it and it strikes once, "
              "then slides away. The bite does little, but it poisons: you lose health slowly until you eat. Mown grass has no adders.",
    stats=dict(hp=3, damage="1 + poison", speed="fast", drops="snakeskin"),
    dirs={"left": dict(walk=[LEFT, LEFT2], act=[LEFT, STRIKE]),
          "down": dict(walk=[DOWN, mirror(DOWN)], act=[DOWN, DOWN_BITE]),
          "up": dict(walk=[UP, mirror(UP)], act=[UP, mirror(UP)])},
)
