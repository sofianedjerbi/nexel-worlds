"""Lampwing: a big night moth, seen from above with its wings spread. It flies: the shadow sits apart on the ground."""
from art import G, edit, turn_left

PAL = {"o": "5a4a6e", "w": "efe6d0", "v": "c9b6d8", "V": "9a86b8", "k": "3d3350", "y": "f6c45a", "f": "d9c9a8", "e": "2b2236"}

UP = G("""
......o.......o......
.......o.....o.......
.oooo...ooooo...oooo.
owwwwoo.offfo.oowwwwo
owvkvwwoofffoowwvkvwo
owkykvwwofffowwvkykwo
owvkvvwwofffowwvvkvwo
.owvvvwwofffowwvvvwo.
..oooVVwofffowVVooo..
...oVVVVofffoVVVVo...
...oVvvVofffoVvvVo...
....oVVoofffooVVo....
.....oo..ofo..oo.....
..........o..........
.....................
.....................
.....................
.....sssssssssss.....
""")
UP_SHUT = edit(UP, {
    2: "....oo..ooooo..oo....",
    3: "...owwo.offfo.owwo...",
    4: "...owkwoofffoowkwo...",
    5: "...owykwofffowkywo...",
    6: "...owkvwofffowvkwo...",
    7: "...owvvwofffowvvwo...",
    8: "....ooVwofffowVoo....",
    9: ".....oVVofffoVVo.....",
    10: ".....oVVofffoVVo.....",
    11: "......ooofffooo......",
    12: ".........ofo.........",
    -1: ".......sssssss.......",
})


def facing_down(g):
    body = g[:14][::-1]
    body[11] = body[11].replace("offfo", "oefeo")
    return body + g[14:]


DUST = {14: "....y......y....y....", 15: ".......y......y......", 16: "...y.......y......y.."}
DUST2 = {14: ".......y......y......", 15: "....y......y....y....", 16: "......y...y...y......"}



def facing_left(g, dust=None):
    """Seen from above, so the side view is the same moth turned a quarter: head to the left, wings up and down."""
    body = turn_left(g[:14])
    w = len(body[0])
    gap = [r.ljust(w, ".")[:w] for r in (dust or ["", "", ""])]
    return body + gap + [("..ssssssssss..")[:w]]


LD, LD2 = ["..y....y..y", ".....y....y..", "...y....y...y"], [".....y....y", "..y....y...y", "....y.....y"]
LEFT, LEFT_SHUT = facing_left(UP), facing_left(UP_SHUT)
DOWN, DOWN_SHUT = facing_down(UP), facing_down(UP_SHUT)

ENEMY = dict(
    key="lampwing", name="Lampwing", pal=PAL, role="light thief", cell=(32, 32), fps=dict(walk=8, act=8), act="dust",
    where="anywhere there is a light", when="night",
    behaviour="Harmless to you, bad for your camp. It flies to the nearest torch or campfire and beats it out with its wings, "
              "and in the dark the glooms come. Its wing dust makes you slow for a moment. One hit kills it; it flies over fences.",
    stats=dict(hp=1, damage=0, speed="fast, flies", drops="wing dust"),
    dirs={"left": dict(walk=[LEFT, LEFT_SHUT], act=[facing_left(UP, LD), facing_left(UP_SHUT, LD2)]),
          "down": dict(walk=[DOWN, DOWN_SHUT], act=[edit(DOWN, DUST), edit(DOWN_SHUT, DUST2)]),
          "up": dict(walk=[UP, UP_SHUT], act=[edit(UP, DUST), edit(UP_SHUT, DUST2)])},
)
