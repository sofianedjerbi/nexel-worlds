"""Lampwing: a big night moth, seen from above with its wings spread. It flies: the shadow sits apart on the ground.

Animation: the wings go open, half, shut, half; the body drops a pixel as the wings close and lifts as they open, and the
shadow shrinks with the wings. It never stands still. The dust: it beats faster in place and dust falls, row by row.
"""
from art import G, edit, shift, turn_left

PAL = {"o": "5a4a6e", "w": "efe6d0", "v": "c9b6d8", "V": "9a86b8", "k": "3d3350", "y": "f6c45a", "f": "d9c9a8", "e": "2b2236"}

OPEN = G("""
.....................
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
""")
HALF = edit(OPEN, {
    3: "..ooo...ooooo...ooo..",
    4: ".owwwo..offfo..owwwo.",
    5: ".owvkwwoofffoowwkvwo.",
    6: ".owkykwwofffowwkykwo.",
    7: ".owvkvwwofffowwvkvwo.",
    8: "..owvvwwofffowwvvwo..",
    9: "...ooVVwofffowVVoo...",
    10: "....oVVVofffoVVVo....",
    11: "....oVvVofffoVvVo....",
    12: ".....oVoofffooVo.....",
    13: "......o..ofo..o......",
})
SHUT = edit(OPEN, {
    3: "....oo..ooooo..oo....",
    4: "...owwo.offfo.owwo...",
    5: "...owkwoofffoowkwo...",
    6: "...owykwofffowkywo...",
    7: "...owkvwofffowvkwo...",
    8: "...owvvwofffowvvwo...",
    9: "....ooVwofffowVoo....",
    10: ".....oVVofffoVVo.....",
    11: ".....oVVofffoVVo.....",
    12: "......ooofffooo......",
    13: ".........ofo.........",
})
WINGS = [(OPEN, 0, 11), (HALF, 0, 9), (SHUT, 1, 7), (HALF, 1, 9)]       # sprite, how far the body has dropped, shadow width
DUST = ["....y......y....y....", ".......y......y......", "...y.......y......y..", "......y...y...y......"]


def frame(i, facing, dust=None):
    g, drop, sh = WINGS[i]
    if facing == "down":
        g = g[:1] + g[1:][::-1]
        g = edit(g, {3: g[3].replace("offfo", "oefeo")})
    elif facing == "left":
        g = turn_left(g[1:])                                            # seen from above, so the side view is a quarter turn
        g = ["." * len(g[0])] + g
    w = len(g[0])
    gap = ["." * w] * 3
    if dust is not None:
        gap = [DUST[(dust + j) % 4][:w].ljust(w, ".") if j <= dust % 3 else "." * w for j in range(3)]
    body = shift(g, 0, drop) if drop else g
    pad = (w - min(sh, w - 2)) // 2
    return body + gap + ["." * pad + "s" * (w - 2 * pad) + "." * pad]


def frames(facing):
    return dict(idle=[frame(i, facing) for i in range(4)], walk=[frame(i, facing) for i in range(4)],
                act=[frame(i % 4, facing, dust=i) for i in range(8)])


ENEMY = dict(
    key="lampwing", name="Lampwing", pal=PAL, role="light thief", cell=(32, 32), act="dust", stride=1.2,
    ms=dict(idle=[130, 80, 130, 80], walk=[90, 60, 90, 60], act=60),
    where="anywhere there is a light", when="night",
    behaviour="Harmless to you, bad for your camp. It flies to the nearest torch or campfire and beats it out with its wings, "
              "and in the dark the glooms come. Its wing dust makes you slow for a moment. One hit kills it; it flies over fences.",
    stats=dict(hp=1, damage=0, speed="fast, flies", drops="wing dust"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
