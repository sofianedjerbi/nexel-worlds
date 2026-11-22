"""Where you aim, seen (target.js, aim_art.js): the selected cell's box is always whole, drawn OVER your sprite at your
body's cell or over your head (your sprite seen through it), as a box under your feet when it is under you; and your
body aims at it with its face and paw: up, ahead or down, in every facing, back to standing when nothing is aimed at."""
import pytest

pytestmark = pytest.mark.e2e

# your sprite's box on the picture (device px): its px, and how many of them are the box's line colour
BODY = """([c, on]) => { const P = HdLook.art(), B = P && P.body, k = devicePixelRatio; if (!B) return null;
  const top = Target.top; if (!on) Target.top = () => { Target.late = null; };
  return new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(() => { Target.top = top;
    const d = HdLook.read(Math.round(B.x * k), Math.round(B.y * k), Math.round(B.w * k), Math.round(B.h * k)).data, px = [];
    for (let i = 0; i < d.length; i += 4) px.push(d[i], d[i + 1], d[i + 2]); res(px); }))); }"""
LINE = {"break": (255, 157, 60), "place": (255, 248, 232), "bad": (232, 85, 74)}


def shaft(game):
    game.clear_area(6)
    game.stamp(-1, -1, ["...", "..."], levels=["444", "401"])
    game.give(dirt=8)
    game.hold_item("dirt")
    game.face(1, 0)
    game.press("z")
    game.wait("Build.on", 3000)
    return game.js("myZ(myPos().x, myPos().y)")


def at(game, dx, lv, h):
    """the build cursor in your column (dx 0) or before you, lv levels over your body's cell (-1: the block under you)"""
    game.js(f"(() => {{ const s = myPos(); Build.S.at = {{x: s.x + {dx}, y: s.y}}; Build.S.plane = {h + lv + 1}; Build.S.deep = null; return 1; }})()")
    game.frames(4)


def test_the_selected_box_in_your_own_column_is_drawn_whole_over_you_or_under_your_feet(game):
    """The owner in a 1-wide shaft, build mode: the box of the cell at his body or over his head was cut out of his sprite
    (or not drawn at all: 40 % of it on the sprite). Now drawn over it, the sprite showing through; the block under
    him: a box under his feet, drawn whole round them, the sprite in front of it."""
    h = shaft(game)
    for lv in (-1, 0, 1, 2):
        at(game, 0, lv, h)
        s = game.js("(() => { const p = myPos(), c = Target.sel; return c && {x: c.x - p.x, y: c.y - p.y, lv: c.z - myZ(p.x, p.y) - 1, kind: c.kind, ok: c.ok !== false}; })()")
        assert s and s["x"] == 0 and s["y"] == 0 and s["lv"] == lv, (lv, s)
        drew = game.js("Target.drew.filter((d) => d.over || d.sel).map((d) => ({over: !!d.over, sel: !!d.sel, line: d.line || 0, dots: d.dots || 0}))")
        assert len(drew) == 1 and drew[0]["line"] + drew[0]["dots"] > 0, (lv, drew)
        assert drew[0]["over"] == (lv >= 0), (lv, drew)              # over you at your body and above; under you: under your feet
        if lv < 0:
            continue
        on, off = game.js(BODY, ["", True]), game.js(BODY, ["", False])
        n = len(on) // 3
        changed = sum(1 for i in range(n) if sum(abs(on[3 * i + j] - off[3 * i + j]) for j in range(3)) > 24)
        col = LINE["bad"] if not s["ok"] else LINE[s["kind"]] if s["kind"] in LINE else LINE["place"]
        line = sum(1 for i in range(n) if sum(abs(on[3 * i + j] - col[j]) for j in range(3)) < 30)
        assert changed > n * .05, (lv, changed, n)                   # the box is on your sprite's box
        assert line < n * .5, (lv, line, n)                          # ...and you show through it, not covered by its line
    game.press("z")


POSES = """(() => { const c = document.createElement('canvas'); c.width = 48; c.height = 48; const g = c.getContext('2d', {willReadFrequently: true});
  const top = (col, row) => { g.clearRect(0, 0, 48, 48); g.drawImage(IMG.character, col * 48, row * 48, 48, 48, 0, 0, 48, 48); const d = g.getImageData(0, 0, 48, 48).data;
    let t = -1, b = -1, sig = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) { const y = Math.floor(i / 4 / 48); if (t < 0) t = y; b = y; sig = (sig * 31 + i + d[i - 3] * 7 + d[i - 1]) % 1000000007; } return [t, b, sig]; };
  const out = []; for (let f = 0; f < 4; f++) out.push({idle: top(0, f), up: top(AimArt.COL.up, ANIM.aim + f), ahead: top(AimArt.COL.ahead, ANIM.aim + f), down: top(AimArt.COL.down, ANIM.aim + f),
    paw: ['up', 'ahead', 'down'].map((a) => AimArt.PAW[a][f])}); return [IMG.character.height, out]; })()"""


def test_the_aim_has_a_pose_for_up_ahead_and_down_in_every_facing(game):
    """Made from the standing frame by whole rows (aim_art.js): up a row taller (the head raised), down a row lower
    (the head bowed), ahead the paw held out; the feet on the cat's own row; each pose its own picture, its paw known."""
    h, rows = game.js(POSES)
    assert h == 44 * 48 and game.js("ANIM.aim") == 40
    for f, r in enumerate(rows):
        stand = r["idle"]
        assert r["up"][0] < stand[0] and r["down"][0] > stand[0], (f, r)          # the head up / down
        assert r["up"][1] >= stand[1] and r["down"][1] >= stand[1] - 1, (f, r)   # standing where it stood
        assert len({stand[2], r["up"][2], r["ahead"][2], r["down"][2]}) == 4, (f, r)
        assert all(p and 0 <= p[0] < 48 and 0 <= p[1] < 48 for p in r["paw"]), (f, r)
        if f >= 2:                                                                 # side on: the paw before the body, up over the down one
            up, ahead, down = r["paw"]
            assert up[1] < ahead[1] < down[1], (f, r["paw"])


FRAME = "(() => { const p = ents.get('agent' + myId); return p && [p.fi, DIR_ROW(p), Target.aim]; })()"


def test_standing_you_aim_at_the_selected_cell_and_stand_again_without_one(game):
    """Build mode, the cursor at your head, your body, the block under you, then before you: the aim's pose of your
    facing (up, ahead, down); out of build mode, an empty paw on open grass: nothing aimed at, the standing frames."""
    h = shaft(game)
    for lv, want in ((1, "up"), (0, "ahead"), (-1, "down")):
        for dx in (0, 1):
            at(game, dx, lv, h)
            game.wait(f"(() => {{ const p = ents.get('agent' + myId); return p && Target.aim === '{want}' && p.fi === (ANIM.aim + DIR_ROW(p)) * 8 + AimArt.COL['{want}']; }})()", 3000)
    game.press("z")
    game.wait("!Build.on", 3000)
    game.clear_area(6)
    game.js("selectItem(null)")
    game.wait("(() => { const p = ents.get('agent' + myId); return p && Target.aim === null && p.fi < 4 * 8; })()", 3000)


def well(game):
    """the owner's case: a 1-wide shaft four deep, open to the south (seen from above: its walls' faces edge-on)"""
    game.clear_area(6)
    game.stamp(-2, -2, ["....."] * 4, levels=["44444", "44044", "44044", "00000"])
    game.give(dirt=8)
    game.hold_item("dirt")
    game.face(0, 1)
    game.press("z")
    game.wait("Build.on", 3000)
    return game.js("myZ(myPos().x, myPos().y)")


def at2(game, dx, dy, lv, h):
    game.js(f"(() => {{ const s = myPos(); Build.S.at = {{x: s.x + {dx}, y: s.y + {dy}}}; Build.S.plane = {h + lv + 1}; Build.S.deep = null; return 1; }})()")


LOOK = "(() => { const p = ents.get('agent' + myId); return p && [DIR_ROW(p), p.fx, p.fy]; })()"


def test_you_turn_to_the_selected_cell_and_the_keys_keep_their_facing(game):
    """The owner: "player should face block direction". The cursor east of you: you face east, west: west, north: away,
    south: us; your own column keeps the facing. Only the drawn facing: the tile the keys act on (p.fx, p.fy) is not turned."""
    h = well(game)
    for dx, dy, row in ((1, 0, 2), (-1, 0, 3), (0, -1, 1), (0, 1, 0), (1, 0, 2), (0, 0, 2)):
        game.frames(10)                                              # (a turn holds 150 ms: no flicker)
        at2(game, dx, dy, 0, h)
        ok = f"(() => {{ const p = ents.get('agent' + myId); return p && DIR_ROW(p) === {row} && p.fi === (ANIM.aim + {row}) * 8 + AimArt.COL[Target.aim]; }})()"
        game.wait(ok, 3000)
        assert game.js(LOOK)[1:] == [0, 1], (dx, dy)                 # the keys' facing: south, as it was
    game.press("z")
    game.wait("!Build.on", 3000)
    game.wait("(() => { const p = ents.get('agent' + myId); return p && DIR_ROW(p) === 0; })()", 3000)   # (out of build mode: the keys' tile, south, and you face it)


FRONT = """([dx, dy, z]) => { const s = myPos(), A = HdLook.art(), x = s.x + dx, y = s.y + dy, u = A.u;
  const a = A.at(x, y + 1, z), b = A.at(x + 1, y + 1, z), c = A.at(x, y + 1, z - 1);   // (its south face's corners: its front on the screen, in art px)
  return {sel: Target.drew.filter((d) => d.sel).map((d) => ({area: d.area || 0, line: d.line || 0})),
    rows: Math.round((c[1] - a[1]) / u), cols: Math.round((b[0] - a[0]) / u)}; }"""


def test_the_cell_beside_you_in_the_wall_has_its_whole_box(game):
    """Seen from above in a 1-wide shaft, the cell east of your feet shows only its south face, 3 px tall: its box was a flat
    orange bar beside you. Never a sliver: under a quarter of its block it is the whole block, seen through (target.js pxOf).
    Since the eye looks down at most 58 degrees (hd.js STEEP, 5064cee) that south face is a block's whole front, 8 art px tall,
    as tall as the front of the cell south of you: the box is that face, whole (its top is under the wall's next block, not
    seen). So it is measured against its own face on the screen, not against the cell south of you (top and front: 368 px to
    146; it asked for 70 % of that, right only while the face was a sliver and the box became the whole block)."""
    h = well(game)
    sizes = {}
    for dx, dy in ((1, 0), (-1, 0), (0, 1)):
        at2(game, dx, dy, 0, h)
        game.frames(3)
        d = game.js(FRONT, [dx, dy, h + 1])
        assert len(d["sel"]) == 1, (dx, dy, d)
        sizes[(dx, dy)] = (d["sel"][0]["area"], d["sel"][0]["line"], d["rows"], d["cols"])
    _, _, rows, cols = sizes[(0, 1)]
    assert rows >= 6, sizes                                          # (a front, not a 3 px bar)
    for side in ((1, 0), (-1, 0)):
        a, line, r, c = sizes[side]
        assert abs(r - rows) <= 1 and a >= .9 * min(r, rows) * c and line >= 2 * (min(r, rows) + c) - 4, sizes   # its whole front, outlined all round (a face's rows, read off the picture's px, may round a px apart)
    game.press("z")


RED = """([c]) => { const P = HdLook.art(), B = P && P.body, k = devicePixelRatio; if (!B) return null;
  const d = HdLook.read(Math.round(B.x * k) - 8, Math.round(B.y * k) - 8, Math.round(B.w * k) + 16, Math.round(B.h * k) + 16).data; let n = 0;
  for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 232) + Math.abs(d[i + 1] - 85) + Math.abs(d[i + 2] - 74) < 40) n++; return n; }"""


def test_no_red_box_over_you_where_you_merely_stand(game):
    """A block can't go into your body's cell or your head's: you are in it. Not an error: its box is cream dotted (can't),
    never red, at your feet and at your head."""
    h = well(game)
    for lv in (0, 1):
        at2(game, 0, 0, lv, h)
        game.frames(3)
        d = game.js("Target.drew.filter((d) => d.over).map((d) => ({far: d.far, dots: d.dots || 0, line: d.line || 0}))")
        assert len(d) == 1 and d[0]["far"] and d[0]["dots"] > 0 and d[0]["line"] == 0, (lv, d)
        assert game.js(RED, [""]) < 4, lv
    game.press("z")


LEGS = """(() => { const c = document.createElement('canvas'); c.width = 48; c.height = 48; const g = c.getContext('2d', {willReadFrequently: true});
  const low = (col, row) => { g.clearRect(0, 0, 48, 48); g.drawImage(IMG.character, col * 48, row * 48, 48, 48, 0, 0, 48, 48); const d = g.getImageData(0, 0, 48, 48).data;
    let b = -1; for (let i = 3; i < d.length; i += 4) if (d[i]) b = Math.floor(i / 4 / 48); let n = 0, x0 = 48, x1 = -1;
    for (let y = b - 1; y <= b; y++) for (let x = 0; x < 48; x++) if (d[(y * 48 + x) * 4 + 3]) { n++; x0 = Math.min(x0, x); x1 = Math.max(x1, x); } return [n, x1 - x0]; };
  const out = []; for (let f = 0; f < 4; f++) out.push([low(0, f), low(AimArt.COL.down, ANIM.aim + f)]); return out; })()"""


def test_looking_down_has_no_third_leg(game):
    """The down pose's paw is before the chest (bent down), not at the feet: its feet's rows are no wider than the
    standing frame's (an arm to the feet read as a third leg facing us, a crumpled body side on)."""
    for f, (stand, down) in enumerate(game.js(LEGS)):
        assert down[1] <= stand[1] and down[0] <= stand[0] + 2, (f, stand, down)
