"""Adder: a grass snake. No legs, no face to speak of: one long wave on the ground.

Animation: the body is not drawn by hand, it is a wave computed from a phase, so the bends travel smoothly from head to
tail while the head stays level. The strike: the coils tighten and the head pulls back (hold), then the body goes straight
and the head shoots forward with the mouth open, holds, and the wave returns.
"""
import math

from art import G, outline, over

PAL = {"o": "3a4a3a", "g": "9ccf62", "G": "6ba04e", "k": "3f7040", "e": "2b1f2a", "t": "e0504a", "w": "f4f0e6"}
W, H = 26, 10            # the side view; the head points left
HEAD = G("""
.oooo.
oggggo
oeggGg
oggGGg
.oooo.
""")
HEAD_OPEN = G("""
ooooo..
oegggo.
owttGgg
.otGGgg
..ooooo
""")
TOP_HEAD = G("""
..ooo..
.ogggo.
oegggeo
ogggggo
.ogggo.
""")


def wave(phase, amp=2.0, length=11.0, head_x=3, straight=0):
    """The body from behind the head to the tail tip: three pixels thick, thinning to two, its bends moving with `phase`."""
    fill = [["."] * W for _ in range(H)]
    for x in range(head_x + 4, W - 1):
        t = (x - head_x - 4) / (W - head_x - 6)                         # 0 at the neck, 1 at the tail
        a = amp * min(1, t * 4) * (1 - straight)                        # the neck barely moves: the head stays level
        y = round(3 + a * math.sin(2 * math.pi * (x / length) - phase))
        fill[y][x] = "k" if x % 5 == 0 and t < .8 else "g"
        fill[y + 1][x] = "g" if t < .8 else "G"
        if t < .8:
            fill[y + 2][x] = "G"
    return ["".join(r) for r in fill]


def side(phase, tongue=False, head_x=3, **kw):
    g = outline(wave(phase, head_x=head_x, **kw))
    g = over(g, HEAD_OPEN if kw.get("straight") else HEAD, head_x - 1 if kw.get("straight") else head_x, 2)
    if tongue:
        g = over(g, ["tt"], head_x - 2, 4)
    return g + ["." * 4 + "s" * 20 + ".."]


def vertical(phase, down, **kw):
    """The same wave seen heading up or down the screen: x becomes y, with a head seen from above."""
    g = outline(wave(phase, **kw))
    body = ["".join(row[x] for row in g) for x in range(W)]            # the head end is at the top
    body = over(body, TOP_HEAD if down else [r.replace("e", "g") for r in TOP_HEAD], 1, kw.get("head_x", 3))
    if kw.get("straight"):
        body = over(body, [".ooooo.", ".ottto."] if down else [".ooooo."], 1, kw.get("head_x", 3) - 1)
    if down:                                                           # head at the bottom, touching its shadow
        body = body[::-1]
        while not body[-1].strip("."):
            body = [body[-1]] + body[:-1]
    return body + ["." + "s" * (H - 2) + "."]


PH = [i * math.pi / 4 for i in range(8)]               # 8 frames, like the game's own walks
COIL = dict(amp=2.3, length=9.0, head_x=6)
LUNGE = dict(straight=.75, head_x=1)


def frames(make):
    return dict(idle=[make(0), make(0, tongue=True)] if make is side else [make(0), make(.5)],
                walk=[make(p) for p in PH],
                act=[make(0, **COIL), make(0, **LUNGE), make(0, **LUNGE), make(0)])


ENEMY = dict(
    key="adder", name="Adder", pal=PAL, role="ambusher", cell=(32, 32), act="strike", stride=1.4,
    ms=dict(idle=[1500, 140], walk=80, act=[450, 80, 200, 250]),
    where="tall grass, crop fields", when="day",
    behaviour="Lies in tall grass where you cannot see it, and only the grass moves. Step next to it and it strikes once, "
              "then slides away. The bite does little, but it poisons: you lose health slowly until you eat. Mown grass has no adders.",
    stats=dict(hp=3, damage="1 + poison", speed="fast", drops="snakeskin"),
    dirs={"left": frames(side),
          "down": frames(lambda p, **kw: vertical(p, True, **kw)),
          "up": frames(lambda p, **kw: vertical(p, False, **kw))},
)
