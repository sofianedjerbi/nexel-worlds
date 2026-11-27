"""The skeleton (#366: the owner's pick, "Ember eyes", the second of three on the draft page): it comes out at night.

Drawn in the game's own character style, on the player's body plan: every frame is read off the cat's own frame in
character.png (where its body is, where its feet land, how high its head rides: the same bob and walk cycle, frame for
frame), with the cat's 1 px purple outline, flat bone and one shade. On that: a skull per facing (a round cranium,
cheekbones, deep sockets with an ember in each, a nose hole, a row of teeth, a jaw that drops), collarbones, separate
ribs on a spine, a pelvis, bone legs with knees to the cat's feet, bone arms with elbows that swing against the legs.
The skull rides LIFT px higher than the cat's head to make room for the ribs. Its fight: sim/skeleton.py."""

from pathlib import Path

from PIL import Image

from art import outline

CAT = Image.open(Path(__file__).resolve().parents[3] / "src/nexel_worlds/web/assets/character.png").convert("RGBA")
X0, Y0, W, H = 12, 11, 24, 21           # the crop of a 48 px cell the frames keep (the cat's feet on row H-2)

# the cat's colours -> ours: a outline, b bone, d its shade (lilac) -> w warm grey, the collar f -> the neck (outline),
# its pinks (c, e) and the bell (g) -> bone
CATMAP = {(92, 78, 146): "a", (243, 242, 192): "b", (232, 181, 172): "b", (221, 213, 222): "w", (243, 216, 197): "b",
          (118, 109, 170): "a", (234, 225, 120): "a"}
# the cat's colours -> ours: a outline, b bone, d its shade (lilac) -> w warm grey, the collar f -> the neck (outline),
# its pinks (c, e) and the bell (g) -> bone
CATMAP = {(92, 78, 146): "a", (243, 242, 192): "b", (232, 181, 172): "b", (221, 213, 222): "w", (243, 216, 197): "b",
          (118, 109, 170): "a", (234, 225, 120): "a"}
PAL = {"a": "5c4e92", "b": "f4f1e6", "L": "ffffff", "w": "c4bba8", "k": "2a2036", "E": "ffd86a"}
ROWS = {"down": 0, "up": 1, "left": 2}           # the cat's rows (idle; its walk is 4 rows on)


def cat_frame(row, col):
    f = CAT.crop((col * 48 + X0, row * 48 + Y0, col * 48 + X0 + W, row * 48 + Y0 + H))
    g = [["." for _ in range(W)] for _ in range(H)]
    for y in range(H):
        for x in range(W):
            p = f.getpixel((x, y))
            if p[3]:
                g[y][x] = CATMAP.get(p[:3], "b")
    return g


# skulls, by facing (right: mirrored from left). b bone, w its shade, L its light, k the dark (sockets, nose, mouth),
# E an ember in each socket. The last two rows are the jaw (they drop when it opens).
SKULL = {
    "down": ["....aaaaaa....",
             "..aabbbbbbaa..",
             ".abLLbbbbbbba.",
             "abLbbbbbbbbbwa",
             "abbbbbbbbbbbwa",
             "abkkkbbbbkkkwa",
             "abkEkkbbkkEkwa",
             ".abkkbbbbkkwa.",
             ".awbbbkkbbbwa.",
             "..abababababa.",
             "...abbbbbbwa..",
             "....aaaaaaa..."],
    "left": ["...aaaaaa..",
             ".aabbbbbbaa",
             "abLbbbbbbba",
             "abbbbbbbbwa",
             "akkkbbbbbwa",
             "akEkkbbbbwa",
             "abkkbbbbbwa",
             "akbwbbbbwa.",
             ".ababbbbwa.",
             ".abbbbbwa..",
             "..aaaaaa..."],
    "up": ["....aaaaaa....",
           "..aabbbbbbaa..",
           ".abLLbbbbbbba.",
           "abLbbbbbbbbbwa",
           "abbbbbbbbbbbwa",
           "abbbbbwbbbbbwa",
           "abbbbbwbbbbbwa",
           ".abbbbbwbbbwa.",
           ".awbbbbbbbbwa.",
           "..awbbbbbbwa..",
           "...awwwwwwa...",
           "....aaaaaa...."],
}
HEAD_AT = {"down": 5, "up": 5, "left": 7}          # the skull's left column on the crop (right: mirrored)
LIFT = 3                                           # rows the skull rides above the cat's head top: room for the bones
HT = H + LIFT                                      # (the frame is that much taller than the cat's crop)


def blank():
    return [["." for _ in range(W)] for _ in range(HT)]


def cat_rows(row, col, mir):
    g = cat_frame(row, col)
    if mir:
        g = [r[::-1] for r in g]
    return [["."] * W for _ in range(LIFT)] + [list(r) for r in g]


def feet(g):
    """The cat's feet in this frame: [(x, y)], the middle and the lowest px of each, left to right."""
    lo = max(y for y in range(HT) if any(c != "." for c in g[y]))
    cols = [x for x in range(W) if any(g[y][x] != "." for y in range(lo - 1, lo + 1))]
    runs, cur = [], []
    for x in cols:
        if cur and x != cur[-1] + 1:
            runs.append(cur); cur = []
        cur.append(x)
    if cur:
        runs.append(cur)
    out = [((r[0] + r[-1]) / 2, max(y for y in range(lo - 3, HT) for x in r if g[y][x] != ".")) for r in runs[:2]]
    if len(out) == 1:                                    # (the two feet as one, seen from the side)
        x, y = out[0]
        out = [(x - 1, y), (x + 1, y)]
    return out


def body(face, cx, top_, fs, arm=(0, 0), reach=0):
    """The bones under the skull: collarbones at row top_, separate ribs on a spine, a pelvis, legs to the cat's feet
    (fs), arms from the shoulders. cx: the body's middle column."""
    c = blank()
    put = lambda x, y, ch: 0 <= x < W and 0 <= y < HT and c[y].__setitem__(x, ch)
    floor = max(y for _, y in fs)
    pel = floor - 3                                      # the pelvis row
    side = face in ("left", "right")
    fwd = -1 if face == "left" else 1
    half = 3                                             # the ribcage's half width
    if not side:
        for x in range(cx - half - 1, cx + half + 1):    # collarbones, shoulder to shoulder
            put(x, top_, "b")
        for y in range(top_ + 1, pel):                   # the ribcage, narrowing: ribs (bone) and the dark between them
            w_ = half - max(0, (y - top_ - 2) // 2)
            rib = (y - top_) % 2 == 1
            for x in range(cx - w_, cx + w_):
                put(x, y, ("b" if face == "down" else "w") if rib else "k")
            put(cx - 1 if face == "down" else cx, y, "b")   # the breastbone / the spine
        for y in range(pel - 1, pel):
            put(cx - 1, y, "b")
        for x in range(cx - 3, cx + 2):                  # the pelvis: a bowl, dark in its middle
            put(x, pel, "b")
        put(cx - 1, pel, "k" if face == "down" else "w")
    else:
        back = cx + (1 if face == "left" else -2)
        for y in range(top_, pel):
            put(back, y, "b")                            # the spine, at the back
            if top_ < y < pel - 1:
                ln = 3 - max(0, (y - top_ - 3) // 2)
                for i in range(1, ln + 1):               # ribs curving round to the front, dark between
                    put(back + fwd * i, y, "b" if (y - top_) % 2 == 1 else "k")
        for x in range(cx - 2, cx + 1):
            put(x, pel, "b")
    # legs: hip to foot, a knee (a knob) half way, a foot
    hips = [cx - 3, cx + 1] if not side else [cx - 1, cx - 1]
    for n_, ((fx, fy), hx) in enumerate(zip(fs, hips)):
        fx = round(fx)
        for y in range(pel + 1, fy + 1):
            k = (y - pel) / max(1, fy - pel)
            put(round(hx + (fx - hx) * k), y, "b")
        ky = pel + 1 + (fy - pel - 1) // 2
        kx = round(hx + (fx - hx) * (ky - pel) / max(1, fy - pel))
        put(kx + (fwd if side else (-1 if n_ == 0 else 1)), ky, "b")
        put(fx + (fwd if side else (-1 if n_ == 0 else 1)), fy, "b")
    # arms: shoulder, elbow (a knob), hand at the hip; they swing against the legs (arm: the hands' dx); reach: out front
    hand = pel
    if not side:
        for s_, (sx, d) in enumerate(((cx - half - 2, arm[0]), (cx + half + 1, arm[1]))):
            for y in range(top_ + 1, hand + 1):
                put(sx + round(d * (y - top_) / max(1, hand - top_)), y, "b")
            ey = (top_ + hand) // 2
            put(sx + (-1 if s_ == 0 else 1), ey, "b")
    else:
        sx = cx + (-1 if face == "left" else 0)
        if reach:
            for i in range(0, reach + 2):
                put(sx + fwd * i, top_ + 2, "b")
            put(sx + fwd * (reach + 2), top_ + 1, "b"); put(sx + fwd * (reach + 2), top_ + 3, "b")
        else:
            for y in range(top_ + 1, hand + 1):
                put(sx + round(arm[0] * fwd * (y - top_) / max(1, hand - top_)), y, "b")
    return outline(["".join(r) for r in c], "a")


def skeleton(face, row, col, jaw=0, rattle=0, arm=(0, 0), reach=0, dx=0, dy=0):
    mir = face == "right"
    f = "left" if mir else face
    g = cat_rows(row, col, mir)
    tp = next(y for y, r in enumerate(g) if any(ch != "." for ch in r))   # the cat's head top: its bob
    run = [x for x in range(W) if any(g[y][x] != "." for y in range(tp, tp + 9))]
    cx = (run[0] + run[-1] + 1) // 2
    sk = [list(r) for r in SKULL[f]]
    hy = tp - LIFT
    shoulders = hy + len(sk) - 1                         # the collarbones under the skull's last row
    out = [list(r) for r in body(face, cx, shoulders, feet(g), arm, reach)]
    if jaw:                                              # the jaw drops: a dark mouth opens over it
        mouth = ["k" if ch not in ".a" else ch for ch in sk[-3]]
        sk = sk[:-2] + [mouth] * jaw + sk[-2:]
    if mir:
        sk = [r[::-1] for r in sk]
    hx = HEAD_AT[f] if not mir else W - HEAD_AT[f] - len(sk[0])
    for j, r in enumerate(sk):
        for i, ch in enumerate(r):
            if ch != "." and 0 <= hy + j < HT and 0 <= hx + i + rattle < W:
                out[hy + j][hx + i + rattle] = ch
    res = ["".join(r) for r in out]
    if dx or dy:
        res = ["".join(res[y - dy][x - dx] if 0 <= y - dy < HT and 0 <= x - dx < W else "." for x in range(W)) for y in range(HT)]
    return res


def shadow(g, w=9):
    """The ground under it, as the cat's: the frame a row up, and a row of shadow w px wide under its feet."""
    g = [list(r) for r in g[1:]] + [list("." * W)]
    for x in range(W // 2 - w // 2, W // 2 + w // 2 + 1):
        if g[-1][x] == ".":
            g[-1][x] = "s"
    return ["".join(r) for r in g]


def frames(face):
    r0 = ROWS[face]
    S = lambda col, row=r0, **kw: skeleton(face, row, col, **kw)
    swing = lambda i: (1, -1) if i % 4 in (0, 1) else (-1, 1)
    idle = [S(i, jaw=1 if i in (3, 4) else 0, rattle=(1 if i == 6 else -1 if i == 7 else 0)) for i in range(8)]
    walk = [S(i, row=r0 + 4, arm=swing(i) if face != "left" else (swing(i)[0], 0)) for i in range(8)]
    # the act: the tell (the jaw drops, it rises a px, the skull rattles, the arms go out), then the swipe
    act = [S(0, jaw=1, arm=(-1, 1)), S(0, jaw=2, dy=-1, arm=(-2, 2)), S(1, jaw=2, dy=-1, rattle=1, arm=(-2, 2)),
           S(1, jaw=2, dy=-1, rattle=-1, arm=(-2, 2)),
           S(2, jaw=2, dx=-1, reach=2, arm=(-2, 2)), S(2, jaw=2, dx=-2, reach=4, arm=(2, -2)), S(3, jaw=1, dx=-2, reach=4),
           S(3, dx=-1, reach=2), S(0), S(0)]
    return {k: [shadow(g) for g in v] for k, v in dict(idle=idle, walk=walk, act=act).items()}


ENEMY = dict(
    key="skeleton", name="Skeleton", pal=PAL, role="night walker", cell=(W, HT + 2), move="walk", side="night",
    ms=dict(idle=[300, 260, 300, 200, 260, 300, 90, 90], walk=85, act=[160, 200, 120, 120, 80, 90, 140, 160, 160, 160]),
    beats=dict(act="wwwwssssrr"), hit=dict(act="swipe"),
    where="open ground", when="dusk to dawn; gone by day",
    behaviour="A skeleton with an ember in each eye. It walks straight up to you; its tell is the <b>rattle</b>: its jaw "
              "drops, it rises a px and its skull shakes, arms out. Then it swipes. Step back while it rattles, then "
              "hit it: three hits of a spear. By dawn it is gone.",
    stats=dict(hp=12, damage="3", speed="walks", drops="bones"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
