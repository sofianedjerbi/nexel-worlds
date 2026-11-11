"""Stilt: a marsh heron. Tall and thin on two long legs, a long beak; the tallest thing that is not a tree.

Animation: an 8-frame walk at 80 ms with generated legs (hip to foot when planted, bent and lifted when swinging); the head
thrusts forward ahead of the body, as wading birds do. Idle: the head eases forward and back, and it blinks. The peck: the neck pulls back and holds, then stabs, holds, returns.
"""
from art import G, edit, mirror, pad, nudge, stack, shift

PAL = {"o": "4b4f6b", "b": "aeb9c9", "d": "8793ab", "w": "eef0ea", "k": "3d4260", "y": "e9b04e", "Y": "c98a3a",
       "l": "c98a3a", "e": "2b2236"}

BODY = G("""
....................
...........ooo......
..........owwwokk...
...ooooooowewwwokko.
..oyyyyyyywwwwoooo..
...oooooooowwo......
...........owwo.....
...........owwo.....
..........owwo......
..........owwo......
..........owwooooo..
.........owbbbbbbbo.
.........obbbbbbbbbo
.........obbbbbbdddo
.........owbbbddddko
..........owwdddkko.
...........oooooo...
""")
SHADOW = G(".......sssssssssss..")
HEAD = range(0, 6)
BODY, SHADOW = pad(BODY, right=2), pad(SHADOW, right=2)          # room for the head to pull back
REACH = [-3, -2, -1, 1, 3, 2, 0, -2]          # where the foot is, frame by frame: lands ahead, slides back, lifts, swings forward
RAISE = [0, 0, 0, 0, 0, 1, 2, 1]


def thin_leg(g, hip, phase):
    """One leg, a pixel wide: hip to foot when it carries weight; bent at the joint, foot off the ground, when it swings."""
    out = [list(r) for r in g]
    dx, up = (0, 0) if phase is None else (REACH[phase % 8], RAISE[phase % 8])
    foot_y = 5 - 2 * up
    knee = (hip + (1 if up else 0) + dx // 2, foot_y // 2) if up else None
    pts = [(hip, 0)] + ([knee] if knee else []) + [(hip + dx, foot_y)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            out[y0 + round((y1 - y0) * i / n)][x0 + round((x1 - x0) * i / n)] = "l"
    out[foot_y][hip + dx - 1] = "l"                                # the toes point forward
    return ["".join(r) for r in out]


def side(step=None, head=0, body=BODY):
    b = nudge(body, HEAD, head) if head else body
    legs = ["." * len(body[0])] * 6
    legs = thin_leg(thin_leg(legs, 15, None if step is None else step + 4), 12, step)
    return stack(b, legs, SHADOW)


WINDUP = nudge(nudge(BODY, HEAD, 2), range(6, 8), 1)          # the head drawn back over the body
STAB = G("""
....................
....................
....................
....................
....................
....................
....................
....................
....................
....................
............oooooo..
.........ooobbbbbbo.
.......oowwbbbbbbbbo
.....oowwoobbbbbdddo
...oowwoo.obbbddddko
.oowwwokk.owwdddkko.
oyywewoo...oooooo...
""")
STAB = pad(STAB, right=2)
STAB_LEGS = edit(side()[-7:-1], {0: ".ooyoo......l..l...."})

FRONT = G("""
...........
....kkk....
...okkko...
..owwwwwo..
..oewwweo..
..owwywwo..
...owyoo...
....oYo....
....owo....
....owo....
...oowoo...
..obwwwbo..
.obbwwwbbo.
.obbbwbbbo.
.odbbbbbdo.
.oddbbbddo.
..odddddo..
...ooooo...
""")
BACK = G("""
...........
....kkk....
...okkko...
..owwkwwo..
..owwkwwo..
..owwwwwo..
...ooooo...
....owo....
....owo....
....owo....
...oowoo...
..obbbbbo..
.obbbbbbbo.
.obdbbbdbo.
.obdbbbdbo.
.oddbdbddo.
..odkdkdo..
...ooooo...
""")
F_SHADOW = G(".sssssssss.")
F_LEGS = dict(
    stand=G("...l...l...\n...l...l...\n...l...l...\n...l...l...\n...l...l...\n..ll...ll.."),
    lift=G("...l...l...\n...l...l...\n...l...l...\n..ll...l...\n.......l...\n.......ll.."),     # one leg drawn up, straight
)


def facing(body):
    def f(b, legs="stand", low=False):
        g = stack(b, legs if isinstance(legs, list) else F_LEGS[legs], F_SHADOW)
        return stack(["." * 11], g[:-7], g[-6:]) if low else g      # low: the legs lose a row, the body sinks
    lift, lift2 = f(body, "lift"), f(body, mirror(F_LEGS["lift"]))
    up = edit(stack(body[1:7], ["." * 11], body[7:]), {6: body[8]})  # the head rises as the neck stretches
    down = stack(["." * 11] * 3, body[1:7], body[10:], ["." * 11])[:len(body)]   # the neck is gone: the head is on the body
    blink = [r.replace("e", "w") for r in body]
    return dict(idle=[f(body), f(body), f(body, low=True), f(body, low=True), f(body), f(blink), f(body, low=True), f(body, low=True)],
                walk=[lift, lift, f(body, low=True), f(body, low=True), lift2, lift2, f(body, low=True), f(body, low=True)],
                act=[f(up), f(down), f(down), f(body)])


ENEMY = dict(
    key="stilt", name="Stilt", pal=PAL, role="spear", cell=(32, 32), act="peck", stride=1.0,
    ms=dict(idle=300, walk=80, act=[480, 90, 220, 260]),
    where="shallow water, reeds, shores", when="day",
    behaviour="Stands dead still in the shallows and watches. Its beak reaches two tiles: it pulls its neck back, then stabs. "
              "The stab is slow to come and easy to read; walk in after it lands. It steals the fish you catch nearby.",
    stats=dict(hp=6, damage=2, speed="slow walker", drops="feathers, fish"),
    dirs={"left": dict(idle=[side(), side(), side(head=-1), side(head=-1), side(), side(body=[r.replace("e", "w") for r in BODY]),
                             side(head=-1), side(head=-1)],
                       walk=[side(i, head=-1 if i % 4 >= 2 else 0) for i in range(8)],
                       act=[side(body=WINDUP), stack(STAB, STAB_LEGS, SHADOW), stack(STAB, STAB_LEGS, SHADOW), side()]),
          "down": facing(FRONT), "up": facing(BACK)},
)
