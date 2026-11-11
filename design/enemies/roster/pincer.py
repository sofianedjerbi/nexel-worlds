"""Pincer: a small shore crab, about the size of the game's chicken. A flat pointed shell, two raised claws, eyes on stalks.

A crab walks sideways, so it always shows its face (or its back): going left or right it is the same crab, looking that way.
It is drawn as two halves, so each side can do its own thing:
  idle   the eyes look left, then right; one claw clicks, then the other
  walk   8 frames: on each side the upper leg lifts, then the lower, the two sides half a step apart, and the claws rock
  snap   it crouches, rears up with both claws high (held: the warning), slams them shut with a spark as it lunges, holds, settles
"""
from art import G, shift, pad

PAL = {"o": "7a3340", "r": "e0664a", "R": "b94a3f", "h": "f2906a", "c": "f3d8c5", "e": "2b1f2a", "w": "f4f0e6", "y": "fff1a8"}

CLAW = dict(open=["....", "o.o.", "oro.", ".oo."], shut=["....", ".o..", "oro.", ".oo."], up=["o.o.", "oro.", ".o..", ".oo."])
# the four leg pixels' columns for rows 6-9: both legs down, upper leg lifted, both down, lower leg lifted
LEGS = [["o.", "o.o", "..o", ".o."], ["o.", "..o", "..o", ".o."], ["o.", "o.o", "..o", ".o."], ["o.", "o.o", ".oo", "..."]]
UPPER_LIFT = "o"          # a lifted upper leg shows its knee one row higher


def half(claw="open", legs=0, look_out=False, back=False):
    """The crab's left half, 8 pixels wide; the right half is this mirrored (with its own claw, legs and eyes)."""
    c, lg = CLAW[claw], LEGS[legs % 4]
    eye = "oRR" if back else ("oew" if look_out else "owe")
    rows = [
        c[0] + "....",
        c[1] + eye + ".",                 # a gap between the two eyes, so they do not merge
        c[2] + ".o..",
        c[3] + "oooo",
        "..ooo" + ("rhr" if back else "hhh"),
        (UPPER_LIFT if legs % 4 == 1 else ".") + "orrrrrr",
        lg[0] + "oRrrrr" if not back else lg[0] + "oRrhrr",
        lg[1] + ("oRRRR" if back else "oRcco"),
        lg[2] + ".oooo",
        lg[3] + ".....",
    ]
    return [r.ljust(8, ".")[:8] for r in rows]


def crab(left=None, right=None, back=False, dx=0, dy=0, spark=False):
    l, r = half(back=back, **(left or {})), half(back=back, **(right or {}))
    g = pad([a + b[::-1] for a, b in zip(l, r)], left=2, right=2)
    if spark:
        g = ["y" + g[0][1:-1] + "y"] + [g[1][:1] + "y" + g[1][2:-2] + "y" + g[1][-1:]] + g[2:]
    if dx or dy:
        g = shift(g, dx, dy)
    return g + ["...ssssssssssssss..."]


def frames(back=False, lunge=(0, 1), look=None):
    """look: None for facing the camera, "l" when it is heading left (both pupils left; mirrored for right)."""
    eyes = lambda side: dict(look_out=(look == "l" and side == "l"))
    c = lambda l=None, r=None, **kw: crab(dict(eyes("l"), **(l or {})), dict(eyes("r"), **(r or {})), back=back, **kw)
    out, inn = dict(look_out=True), dict(look_out=False)
    idle = [c(), c(l=out), c(l=dict(out, claw="shut")), c(l=out), c(), c(r=out), c(r=dict(out, claw="shut")), c(r=out)]
    walk = [c(l=dict(legs=i, claw="up" if i < 4 else "open"), r=dict(legs=i + 2, claw="open" if i < 4 else "up")) for i in range(8)]
    both = lambda claw: (dict(claw=claw), dict(claw=claw))
    act = [c(*both("shut"), dy=1), c(*both("up"), dy=-1), c(*both("shut"), dx=lunge[0], dy=lunge[1], spark=True),
           c(*both("shut"), dx=lunge[0], dy=lunge[1]), c()]
    return dict(idle=idle, walk=walk, act=act)


ENEMY = dict(
    key="pincer", name="Pincer", pal=PAL, ground="sand", role="guard", cell=(24, 16), act="snap", stride=.8,
    ms=dict(idle=[700, 260, 130, 260, 700, 260, 130, 260], walk=70, act=[140, 420, 80, 220, 220]),
    where="beaches and river banks", when="day and night",
    behaviour="Small and quick. It walks sideways only, so it must turn its flank to chase you. Hits from the front bounce off its "
              "claws; hit it from the side or from behind. It buries itself in sand when hurt and comes back later.",
    stats=dict(hp=4, damage=2, speed="quick sideways, slow forward", drops="shell, claw meat"),
    dirs={"left": frames(lunge=(-2, 0), look="l"), "down": frames(), "up": frames(back=True, lunge=(0, -1))},
)
