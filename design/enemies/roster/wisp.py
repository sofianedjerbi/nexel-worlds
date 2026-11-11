"""Wisp: a floating lantern-jelly of the night. Nothing here is drawn by hand: every frame is computed, so it moves as
smoothly as the player does.

  the bell   a dome that squashes wide and stretches tall over 8 frames, bobbing up and down as it does
  tentacles  four strands, each a travelling wave, trailing behind when it moves sideways
  the glow   a soft halo (see-through pixels) that breathes with the bell
  the call   it dims and shrinks (the warning), then flares with sparks, and settles
"""
import math

from art import outline, over

PAL = {"o": "4f8fa6", "b": "c9f3ee", "w": "fafffb", "d": "8fd6d6", "e": "2b3a55", "y": "fff1a8",
       "g": "9fe8e060", "h": "9fe8e030"}
W, H = 26, 28
CX = W // 2
WIDE = [10, 12, 12, 12, 10, 8, 8, 10]            # the bell's width, frame by frame: squash, then stretch
TALL = [8, 7, 7, 7, 8, 9, 9, 8]
BOB = [0, 1, 1, 0, -1, -2, -2, -1]


def frame(i, facing, glow=1.0, sparks=False, scale=0):
    i %= 8
    fx = {"left": -1, "right": 1}.get(facing, 0)
    w, h = WIDE[i] + scale, TALL[i]
    top = 9 + BOB[i] - (h - 8)
    fill = [["."] * W for _ in range(H)]
    for r in range(h):                                              # the dome: full width at the rim
        half = max(1, round(w / 2 * math.sqrt(1 - ((h - 1 - r) / h) ** 2)))
        for x in range(CX - half, CX + half):
            fill[top + r][x] = "d" if r == h - 1 and (x + i) % 3 == 0 else "b"      # a scalloped rim that ripples
    for x, y in ((CX - 3, top + 2), (CX - 2, top + 1), (CX - 2, top + 2)):        # the light inside, upper left
        if fill[y][x] == "b":
            fill[y][x] = "w"
    g = outline(["".join(r) for r in fill])
    g = [list(r) for r in g]
    if facing != "up":                                              # two eyes, looking where it goes
        ey = top + h - 3
        for x in (CX - 2 + fx, CX + 1 + fx):
            g[ey][x] = "e"
    rim = top + h
    for k, x0 in enumerate((CX - 4, CX - 2, CX + 1, CX + 3)):       # tentacles: a wave running down each strand
        for r in range(7 - (k % 2)):
            x = x0 + round(1.3 * math.sin(2 * math.pi * i / 8 - r * 0.8 + k * 1.7)) - round(fx * r * 0.45)
            if 0 <= x < W and rim + r < H - 1 and g[rim + r][x] == ".":
                g[rim + r][x] = "d" if r < 5 else "b"
    cy, rad = top + h / 2, (7.5 + (WIDE[i] - 10) * 0.4) * glow       # the halo
    for y in range(H - 1):
        for x in range(W):
            d = math.hypot(x - CX + 0.5, (y - cy) * 1.1)
            if g[y][x] == "." and d <= rad:
                g[y][x] = "g" if d <= rad - 2 else "h"
    if sparks:
        for k in range(8):
            a = k * math.pi / 4 + i * 0.4
            x, y = round(CX + 11 * math.cos(a)), round(cy + 9 * math.sin(a))
            if 0 <= x < W and 0 <= y < H - 1:
                g[y][x] = "y"
    sh = 8 + (WIDE[i] - 10) // 2
    g[H - 1] = list("." * ((W - sh) // 2) + "s" * sh + "." * (W - sh - (W - sh) // 2))
    return ["".join(r) for r in g]


def frames(facing):
    return dict(idle=[frame(i, facing) for i in range(8)], walk=[frame(i, facing) for i in range(8)],
                act=[frame(4, facing, glow=0.7, scale=-2), frame(5, facing, glow=0.55, scale=-2),
                     frame(1, facing, glow=1.45, sparks=True, scale=2), frame(2, facing, glow=1.3, sparks=True, scale=2),
                     frame(3, facing, glow=1.15), frame(4, facing)])


ENEMY = dict(
    key="wisp", name="Wisp", pal=PAL, role="lure", cell=(32, 32), act="call", move="float",
    ms=dict(idle=140, walk=90, act=[220, 300, 90, 160, 160, 160]),
    where="meadows and marsh, far from any fire", when="night",
    behaviour="A light in the dark that looks like a far campfire. It drifts ahead of you and calls; follow it and it leads "
              "you somewhere: often to ore or a lost chest, sometimes into a ring of glooms. It cannot be hit and never hurts "
              "you itself. Light a torch and it fades.",
    stats=dict(hp="none", damage=0, speed="as fast as you walk", drops="nothing"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
