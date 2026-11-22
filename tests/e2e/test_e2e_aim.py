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
