"""Redknee (#366, the owner's pick of three tarantulas, "improved a little"): a hairy, heavy night spider.

It is posed in 3D (x forward, y to its left, z up) and projected for each facing, the way the game looks at the world
(a little from above: what is nearer is lower on the screen). Each leg is a hip, a knee and a foot: the foot is placed,
the knee is solved (two bones, bent up), so the legs really bend. It walks as a spider does: two sets of four legs
(L1 R2 L3 R4 / R1 L2 R3 L4) take turns, one set planted and pushing back while the other lifts and swings forward.
Parts are drawn far to near, each with its outline; hair is a fringe of single pixels outside the outline. Its fight
(sim/redknee.py): it waits by cover, rears up with its fangs bared (the warning), then pounces on where you stood;
still there, you are bitten and pinned in silk for a moment."""
import math

from art import canvas, dot, ell, ground, outline, over, rows


def cap(c, x0, y0, x1, y1, r0, ch, r1=None, on=None):
    """A thick limb: discs along the segment, r0 at the start tapering to r1."""
    r1 = r0 if r1 is None else r1
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) * 2))
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t
        ell(c, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, max(.6, r), max(.6, r), ch, on)


def bevel(c, ch, lite=None, dark=None, d=1, keep=""):
    """Light from the top left: the pixels of ch on the shape's top edge go lite, those within d of its lower right edge
    go dark (the shape = every filled px of this canvas)."""
    h, w = len(c), len(c[0])
    full = lambda x, y: 0 <= x < w and 0 <= y < h and c[y][x] != "."
    src = [r[:] for r in c]
    for y in range(h):
        for x in range(w):
            if src[y][x] != ch:
                continue
            if dark and any(not full(x + k, y + k) or not full(x, y + k) for k in range(1, d + 1)):
                c[y][x] = dark
            elif lite and (not full(x, y - 1) or not full(x - 1, y - 1)):
                c[y][x] = lite

W, H = 62, 42
FACES = ("left", "down", "up")

# its palette (body b/B/L, leg l/k, bands r, hair h, eyes E, fangs f, mouth m, silk/dust d) and build
REDKNEE = dict(
    pal={"o": "1a1210", "b": "3a2a24", "B": "1e1410", "L": "5e463a", "l": "4a362e", "n": "6e544a", "k": "30241d", "r": "e0662e", "R": "ffa45c",
         "h": "6a4436", "E": "ff7a4a", "e": "fff0d8", "f": "e8dccb", "m": "6a2a20", "d": "e8e2d4", "D": "a8977c", "a": "b8542c"},
    ab=(7.8, 6.7, 5.7), ce=(5.1, 4.7, 3.3), leg=(1.55, 1.25), hair=.45, bands=("r", "r"), reach=1.0)

# leg sockets on the carapace (front to back) and where each foot rests (x forward, y out); pedipalps apart
HIPS = [(3.0, 2.4), (1.6, 3.2), (0.2, 3.2), (-1.2, 2.6)]
FEET = [(14.0, 12.0), (6.0, 16.5), (-4.0, 16.5), (-12.5, 13.0)]
BONES = [(9.5, 10.5), (8.5, 9.5), (8.5, 9.5), (9.5, 11.0)]
SETS = {("L", 0): 0, ("R", 1): 0, ("L", 2): 0, ("R", 3): 0, ("R", 0): .5, ("L", 1): .5, ("R", 2): .5, ("L", 3): .5}


def proj(face, x, y, z, gy, cx):
    """(x forward, y to its left, z up) -> screen px and depth (bigger = nearer the camera)."""
    if face == "left":
        return cx - x, gy - z + y * .32, y
    if face == "down":
        return cx - y, gy - z + x * .45, x
    return cx + y, gy - z - x * .45, -x


def knee(hip, foot, a, b):
    """Two bones a, b from hip to foot, the joint bent up (a spider's knee stands above its body)."""
    d = [foot[i] - hip[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in d)) or 1
    if n >= a + b:
        a, b = a * n / (a + b) * 1.001, b * n / (a + b) * 1.001
    u = [v / n for v in d]
    p = (a * a - b * b + n * n) / (2 * n)
    h = math.sqrt(max(0, a * a - p * p))
    up = [0, 0, 1]
    dot_ = sum(up[i] * u[i] for i in range(3))
    w = [up[i] - dot_ * u[i] for i in range(3)]
    wn = math.sqrt(sum(v * v for v in w)) or 1
    return [hip[i] + p * u[i] + h * w[i] / wn for i in range(3)]


def hair(c, pts, ch, every, seed, gap):
    """Single hairs standing off an outline: a px beyond the outline on some edge px, picked by a fixed hash."""
    hgt, wid = len(c), len(c[0])
    for (x, y) in pts:
        hsh = (x * 73856093 ^ y * 19349663 ^ seed) & 1023
        if hsh / 1024 > every:
            continue
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1), (-1, -1), (1, -1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < wid and 0 <= yy < hgt - 1 and c[yy][xx] == ".":
                ok = all(not (0 <= xx + ex < wid and 0 <= yy + ey < hgt) or c[yy + ey][xx + ex] in ".o" + ch for ex, ey in ((0, 0),))
                if ok and (hsh >> 3) % gap == 0:
                    c[yy][xx] = ch
                    break


def finish(c, ink="o", fur=None, seed=0):
    """Outline a part, then put its fur on: hairs out of the outline."""
    g = [list(r) for r in outline(rows(c), ink)]
    if fur:
        ch, every = fur
        edge = [(x, y) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == ink]
        hair(g, edge, ch, every, seed, 2)
    return rows(g)


def tara(key, face, gait=None, lift=0.0, tilt=0.0, raise_=0.0, fang=0, crouch=0.0, air=0.0, reach=0.0, squash=0.0, curl=0.0,
         palp=0.0, tap=0.0, breath=0.0, eye=1, dust=0, silk=0, hold=None):
    """One pose. gait: walk phase 0..1 (None: standing). lift: body px up. tilt: front up (rad). raise_: front two pairs
    up in threat. fang: 0 shut, 1 out, 2 striking. crouch: body pressed down (0..1). air: px in the air. reach: legs thrown
    forward (the leap). squash: landing (0..1). curl: legs drawn in (death). tap: the front leg lifts and taps (idle)."""
    T = REDKNEE
    abr, cer, (lr0, lr1) = T["ab"], T["ce"], T["leg"]
    k = T["reach"]
    side = face == "left"
    gy = H - (5 if side else 10 if face == "down" else 4)
    cx = W // 2 + (3 if side else 0)
    z0 = 7.0 - crouch * 3.2 + lift + air - squash * 2.2
    prims = []                                                          # (depth, painter)

    def body_pt(x, z):                                                  # a point of the body, tilted about the hips
        return x * math.cos(tilt) - (z - z0) * math.sin(tilt), z0 + (z - z0) * math.cos(tilt) + x * math.sin(tilt)

    # legs
    for s, sg in (("L", 1), ("R", -1)):
        for i in range(4):
            hx, hy = HIPS[i]
            hx, hz = body_pt(hx, z0)
            hip = [hx, hy * sg, hz]
            fx, fy = FEET[i]
            fx, fy = fx * k, fy * k
            fz = 0.0
            if gait is not None:                                        # the stride: planted and pushed back, lifted and swung
                ph = (gait + SETS[(s, i)]) % 1
                stride = 4.5
                if ph < .5:
                    fx += stride / 2 - stride * ph / .5
                else:
                    u = (ph - .5) / .5
                    fx += -stride / 2 + stride * u
                    fz = 3.2 * math.sin(math.pi * u)
            if crouch:
                fy *= 1 + crouch * .12
            if squash:
                fy *= 1 + squash * .18
                fx *= 1 + squash * .1
            if raise_ and i < 2:                                        # threat: the front pairs up, the fangs bared under them
                r = raise_ * (1 if i == 0 else .7)
                fx, fy, fz = fx * (1 - .35 * r), fy * (1 - .3 * r), fz + r * (16 if i == 0 else 11)
            if air:                                                     # the leap: front legs thrown ahead, back legs trailing
                fz = max(fz, air - (2 if i < 2 else 3))
                fx += reach * (5 if i < 2 else -4)
                fy *= .85
            if tap and s == "L" and i == 0:
                fz += tap * 5
                fx += tap * 1.5
            if curl:                                                    # dying: the legs fold in under it
                fx, fy, fz = fx * (1 - .7 * curl), fy * (1 - .75 * curl), fz + curl * (z0 + 1)
            foot = [fx, fy * sg, fz]
            kn = knee(hip, foot, *[v * k for v in BONES[i]])
            if curl:
                kn[2] += curl * 2
            seg = [(hip, kn, lr0, lr0 * .9, "femur"), (kn, foot, lr0 * .9, lr1 * .8, "tibia")]
            for a, b, r0, r1, nm in seg:
                d = (proj(face, *a, gy, cx)[2] + proj(face, *b, gy, cx)[2]) / 2
                prims.append((d + (.01 * i), ("leg", a, b, r0, r1, nm, i)))
    # pedipalps: two short feelers at the front
    for sg in (1, -1):
        hx, hz = body_pt(cer[0] * .8 + 1.5, z0 - .5)
        hip = [hx, 1.6 * sg, hz]
        foot = [hx + 4 + palp * 1.5 - curl * 3, (2.6 + palp * .6) * sg, max(0, hz - 5 + palp * 2 + raise_ * 3 + curl * 3)]
        kn = knee(hip, foot, 3.2, 3.6)
        d = (proj(face, *hip, gy, cx)[2] + proj(face, *foot, gy, cx)[2]) / 2
        prims.append((d + .2, ("leg", hip, kn, lr1 * .95, lr1 * .9, "palp", 0)))
        prims.append((d + .2, ("leg", kn, foot, lr1 * .9, lr1 * .8, "palp", 0)))
    # body: abdomen behind, carapace in front
    ax, az = body_pt(-abr[0] - 1.0, z0 + .8)
    cx3, cz = body_pt(cer[0] * .45, z0 + .2)
    for (px, pz, r, nm) in ((ax, az, abr, "ab"), (cx3, cz, cer, "ce")):
        d = proj(face, px, 0, pz, gy, cx)[2]
        prims.append((d - (2.5 if nm == "ab" and face != "up" else 0) + (3 if nm == "ab" and face == "up" else 0), ("body", px, pz, r, nm)))
    prims.sort(key=lambda p: p[0])

    g = rows(canvas(W, H))
    pal_leg, band, band2 = "l", T["bands"][0], T["bands"][1]
    fur = ("h", T["hair"])
    for depth, p in prims:
        c = canvas(W, H)
        if p[0] == "leg":
            _, a, b, r0, r1, nm, i = p
            ax_, ay_, _ = proj(face, *a, gy, cx)
            bx_, by_, _ = proj(face, *b, gy, cx)
            far = depth < (0 if face == "left" else -99)
            base = "k" if far else pal_leg
            cap(c, ax_, ay_, bx_, by_, r0, base, r1)
            if not far:
                bevel(c, base, "n", None, 1)
            if nm == "femur" and not far:                               # a band at the knee
                tx, ty = ax_ + (bx_ - ax_) * .68, ay_ + (by_ - ay_) * .68
                cap(c, tx, ty, bx_, by_, r0, band, r1, on=base + "n")
                bevel(c, band, "R", None, 1)
            elif nm == "tibia" and band2 and not far:                   # and a thin one down the shin
                tx, ty = ax_ + (bx_ - ax_) * .55, ay_ + (by_ - ay_) * .55
                cap(c, tx, ty, tx + (bx_ - ax_) * .14, ty + (by_ - ay_) * .14, r1 * 1.1, band2, r1 * 1.1, on=base + "n")
            part = finish(c, fur=fur if not far else None, seed=i * 7 + int(depth * 10))
            if not far and nm == "femur":                       # a few orange hairs where the band is
                pg = [list(r_) for r_ in part]
                near = [(x, y) for y in range(H) for x in range(W) if pg[y][x] == "o"
                        and any(0 <= x + a_ < W and 0 <= y + b_ < H and c[y + b_][x + a_] in ("r", "R") for a_, b_ in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
                hair(pg, near, "R", .4, i * 13 + 3, 2)
                part = rows(pg)
            g = over(g, part)
        else:
            _, px, pz, r, nm = p
            sx, sy, _ = proj(face, px, 0, pz, gy, cx)
            if side:
                rx, ry = r[0], r[2]
            else:
                rx, ry = r[1], math.sqrt(r[2] ** 2 * .75 + (r[0] * .45) ** 2)
            ry *= 1 - squash * .15
            rx *= 1 + squash * .08 + breath * (.04 if nm == "ab" else 0)
            ry *= 1 + breath * (.04 if nm == "ab" else 0)
            ell(c, sx, sy, rx, ry, "b")
            bevel(c, "b", "L", "B", 1 if nm == "ce" else 2)
            if nm == "ab":
                if face != "down":                # a rust patch of hair on its back
                    ell(c, sx + (1 if side else 0), sy - ry * .25, rx * .5, ry * .45, "a", on="bL")
                g = over(g, finish(c, fur=("h", T["hair"] + .25), seed=11))
            else:
                face_at = (sx, sy, rx, ry)
                for j in range(-2, 3):                                  # the fovea: a star of grooves on its back
                    dot(c, sx + j, sy, "B", on="bL"); dot(c, sx, sy + j * .6, "B", on="bL")
                g = over(g, finish(c, fur=("h", T["hair"]), seed=5))
    if face != "up":                                                    # the face last, over any leg: chelicerae and fangs, the eyes
        sx, sy, rx, ry = face_at
        c2 = canvas(W, H)
        fx3, fz3 = body_pt(cer[0] * .45 + cer[0] - .6, z0 - .6)
        for sg in ((0,) if side else (1, -1)):
            bx_, by_, _ = proj(face, fx3, 1.3 * sg, fz3, gy, cx)
            ell(c2, bx_, by_ + (0 if side else 1), 1.9, 1.8, "b")
        bevel(c2, "b", "L", "B", 1)
        g = over(g, finish(c2, fur=("a", .5), seed=9))
        c3 = [list(r_) for r_ in g]
        for sg in ((0,) if side else (1, -1)):
            bx_, by_, _ = proj(face, fx3, 1.3 * sg, fz3, gy, cx)
            by_ += 0 if side else 1
            if side:                                                    # long curved fangs, a shadow under them
                tips = [[(bx_ - 1, by_ + 1), (bx_ - 1, by_ + 2), (bx_ - 2, by_ + 3)],
                        [(bx_ - 1, by_ + 1), (bx_ - 2, by_ + 2), (bx_ - 3, by_ + 3), (bx_ - 4, by_ + 3)],
                        [(bx_ - 1, by_ + 1), (bx_ - 2, by_ + 1), (bx_ - 3, by_ + 2), (bx_ - 4, by_ + 2), (bx_ - 5, by_ + 1)]][fang]
                shade = [(x_, y_ + 1) for x_, y_ in tips]
            else:
                dx_ = -sg * (0 if fang == 0 else 1)
                tips = [(bx_, by_ + 2), (bx_, by_ + 3), (bx_ + dx_, by_ + 4)] + ([(bx_ + dx_ * 2, by_ + 5)] if fang > 1 else [])
                shade = [(x_ + sg, y_) for x_, y_ in tips]
            for x_, y_ in shade:
                dot(c3, x_, y_, "o", on=".")
            for q, (x_, y_) in enumerate(tips):
                dot(c3, x_, y_, "e" if q == len(tips) - 1 else "f")
            if side and fang:
                dot(c3, bx_ - 2, by_ + 2, "m"); dot(c3, bx_ - 3, by_ + 3, "m", on="o.")
        ex, ey = (sx - rx * .55, sy - ry * .7) if side else (sx, sy - ry * .55)
        ex, ey = round(ex), round(ey)                                   # a dark turret, two big glossy eyes, small ones round them
        sock = [(dx, dy) for dx in range(-1, 4) for dy in (-2, -1, 0, 1)] if side else [(dx, dy) for dx in range(-4, 5) for dy in (-2, -1, 0, 1)]
        for dx, dy in sock:
            dot(c3, ex + dx, ey + dy, "B", on="bLB")
        eyes_ = (((0, -1, "e"), (1, -1, "E"), (0, 0, "E"), (1, 0, "E"), (3, -1, "E"), (3, 1, "E")) if side else
                 ((-2, -1, "e"), (-1, -1, "E"), (-2, 0, "E"), (-1, 0, "E"), (1, -1, "e"), (2, -1, "E"), (1, 0, "E"), (2, 0, "E"),
                  (-4, 1, "E"), (4, 1, "E"), (-3, -2, "E"), (3, -2, "E")))
        for dx, dy, chh in eyes_:
            dot(c3, ex + dx, ey + dy, chh if eye else "B")
        g = rows(c3)
    if dust or silk:
        c = [list(r_) for r_ in g]
        if dust:                                                 # a heavier landing: a ring of dust, clods thrown up and falling
            ox = cx - (3 if side else 0)
            for j in range(18):
                a = math.pi + j * math.pi / 17
                r = 8 + dust * 4
                x_, y_ = ox + r * 1.6 * math.cos(a), H - 3 + r * .4 * math.sin(a) - (2 - dust) * .5
                dot(c, x_, y_, "d" if j % 3 else "D", on=".")
                if dust < 3 and j % 2 == 0:
                    dot(c, x_ + (1 if math.cos(a) > 0 else -1), y_, "D" if j % 4 else "d", on=".")
            for j, (fx_, h_) in enumerate(((-1.0, 1), (-.6, 1.6), (.6, 1.5), (1.0, .9), (-.25, 2.0), (.3, 1.8))):
                t_ = dust / 3
                x_ = ox + fx_ * (10 + 10 * t_)
                y_ = H - 4 - h_ * (7 * math.sin(math.pi * min(1, t_ + .15)))
                dot(c, x_, y_, "D", on="."); dot(c, x_ + 1, y_, "D", on=".") if j % 2 else None
        g = rows(c)
    shadow = max(10, round((26 if side else 30) * (1 - min(air, 12) / 24)))
    return ground(g, cx - (3 if side else 0), shadow)



def frames(face):
    P = lambda **kw: tara("redknee", face, **kw)
    idle = [P(breath=b, palp=p, tap=t, eye=e) for b, p, t, e in
            ((0, 0, 0, 1), (.5, .2, 0, 1), (1, .4, 0, 1), (.5, .4, .5, 1), (0, .2, 1, 1), (.5, 0, .5, 1), (1, 0, 0, 0), (.5, .2, 0, 1))]
    walk = [P(gait=i / 8, lift=.5 * (i % 4 in (1, 2)), palp=.3 * (i % 2)) for i in range(8)]
    # the act: the warning (it rears up, fangs bared) and then the pounce (leap, land heavy in a ring of dust, settle)
    act = [P(crouch=.4, fang=1), P(raise_=.6, tilt=.18, crouch=.2, fang=1), P(raise_=1, tilt=.3, fang=2, palp=1),
           P(raise_=1, tilt=.32, fang=2, palp=1, eye=0),
           P(crouch=1, fang=1), P(air=7, reach=1, tilt=.12, fang=2), P(air=10, reach=1.3, tilt=.05, fang=2),
           P(air=4, reach=.6, fang=2), P(squash=1, fang=2, dust=1), P(squash=.5, fang=1, dust=2), P(crouch=.2, dust=3), P()]
    return dict(idle=idle, walk=walk, act=act)


ENEMY = dict(
    key="redknee", name="Redknee", pal=REDKNEE["pal"], role="night ambusher", cell=(W, H + 2), move="skitter", side="night",
    ms=dict(idle=[300, 260, 300, 160, 200, 160, 220, 260], walk=95, act=[160, 200, 240, 200, 140, 90, 110, 80, 70, 140, 180, 220]),
    beats=dict(act="wwwwssssrrrr"), hit=dict(act="pin"),
    where="by woods, out of the trees' shade", when="dusk to dawn; gone (dug in) by day",
    behaviour="A tarantula as big as a dog, black-brown and hairy, orange bands at every knee. It waits by the trees "
              "and comes for you at night. Its warning is the <b>rear-up</b>: front legs high, fangs bared. Then it "
              "<b>pounces</b> on where you stood: still there, you are bitten and pinned in silk for a moment. Sidestep "
              "the leap and hit it while it settles. By dawn it has dug itself in.",
    stats=dict(hp=12, damage="3, pinned 1.5 s", speed="quick", drops="fibre (its silk)"),
    dirs={d: frames(d) for d in ("left", "down", "up")},
)
