"""What moves by itself is drawn in the HD look (hd_fx.js): a blow's hearts over who was hit, drops hopping out and
landing, a tree falling, flames on what burns, orbs. (They were drawn only on the old flat picture's canvas: none of it
showed in the game.)"""

import pytest

from test_e2e_hd_sun import hd

COW_AT = """(id) => { const q = ents.get('cow' + id); return q ? HdLook.screenOf(q.x + .5, q.y + .5, floorAt(q.tx, q.ty)) : null; }"""
# the px of the picture a tile's flames would be in, CSS px [x0, y0, x1, y1]: over the tile, two tiles high
FLAMES = """([x, y]) => { const a = HdLook.screenOf(x, y + 1, floorAt(x, y)), b = HdLook.screenOf(x + 1, y + 1, floorAt(x, y)); if (!a || !b) return -1;
  const k = cv.width / innerWidth, u = zoom, X0 = Math.round(a[0] * k), X1 = Math.round(b[0] * k), Y0 = Math.round((a[1] - 26 * u) * k), Y1 = Math.round(a[1] * k);
  const d = HdLook.read(X0, Y0, X1 - X0, Y1 - Y0).data; let n = 0;
  for (let i = 0; i < d.length; i += 4) if (d[i] > 200 && d[i + 1] > 70 && d[i + 1] < 215 && d[i + 2] < 110) n++;   // (flame orange and yellow: nothing of a fence or the meadow)
  return n; }"""


def test_a_hit_shows_its_hearts_over_the_cow(game):
    cow = game.spawn("cow", 2, 0, still=10 ** 6)
    game.give(sword=1)
    game.wait(f"ents.has('cow{cow}')", 4000)
    c = game.js(COW_AT, cow)                                     # (where it stands when it is hit: hit, it may run)
    game.js(f"act('attack', {{target: {cow}, with: 'sword'}})")
    game.wait("typeof HdFx !== 'undefined' && HdFx.last.floats.some((f) => f[0].startsWith('-'))", 4000)
    f = game.js("HdFx.last.floats.find((f) => f[0].startsWith('-'))")
    u = game.js("zoom")
    assert c and abs(f[1] + 9 - c[0]) <= 8 * u and 0 < c[1] - f[2] <= 48 * u, (f, c)   # over the cow, not beside it


def test_a_hens_drops_hop_out_and_land(game):
    game.lucky()
    game.give(sword=1)
    hen = game.spawn("chicken", 3, 1, still=10 ** 6)
    game.js(f"act('attack', {{target: {hen}, with: 'sword'}})")
    game.wait("loot.length > 0 && HdFx.last.loot > 0", 4000)      # drawn while they hop
    game.wait("loot.length === 0 && HdFx.last.loot === 0", 4000)  # and they land


def test_a_tree_falls_and_ore_sends_orbs(game):
    game.give(axe=1, pickaxe=1)
    game.hold_item("axe")
    game.stamp(1, 0, ["T"])
    game.face(1, 0)
    game.press("x", 0)
    game.wait("HdFx.last.falls > 0", 8000)                        # the felling, drawn
    game.hold_item("pickaxe")
    game.stamp(0, 1, ["*"])
    game.face(0, 1)
    game.press("x", 0)
    game.wait("HdFx.last.orbs > 0", 6000)


def test_a_burning_fence_has_flames(game):
    game.give(torch=1)
    game.stamp(-1, 0, ["#"])
    x, y = game.pos()
    before = game.js(FLAMES, [x - 1, y])
    game.hold_item("torch")
    game.face(-1, 0)
    game.press("e", 0)
    game.wait("fireAt.length > 0", 4000)
    game.wait(f"({FLAMES})([{x - 1}, {y}]) > 20", 3000)
    assert before <= 5


# every frame: [creatures dying, the px of the box round the tile (x, y) that are near white, the px that are not the meadow's]
DYING = """([x, y, z]) => { window.__dy = []; window.__on = true; const k = devicePixelRatio, f = () => { const a = HdLook.screenOf(x + .5, y + .5, z);
  if (a) { const d = HdLook.read(Math.round((a[0] - 36) * k), Math.round((a[1] - 78) * k), Math.round(72 * k), Math.round(84 * k)).data; let w = 0, n = 0;
    for (let i = 0; i < d.length; i += 4) { if (d[i] > 215 && d[i + 1] > 215 && d[i + 2] > 215) w++; if (!(d[i + 1] > d[i] && d[i + 1] > d[i + 2] + 40)) n++; } __dy.push([dying.length, w, n]); }
  if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_a_creature_killed_flashes_white_and_lifts_before_it_is_gone(browser, server):
    """A cow killed: for half a second its own body is still there, white at first, lifting and fading in its smoke
    (effects.js dying). Only the classic picture drew that: in the HD look the body was gone in one frame."""
    g = hd(browser, server)
    g.hour(.3, still=True)
    g.give(sword=1)
    g.hold_item("sword")
    x, y = g.pos()
    cow = g.spawn("cow", 1, 0, still=10 ** 6)
    g.face(1, 0)
    g.rest()
    g.js(DYING, [x + 1, y, 0])
    g.sleep(300)
    for _ in range(40):
        if not g.js(f"ents.has('cow{cow}')"):
            break
        g.press("x", 250)
    assert not g.js(f"ents.has('cow{cow}')")
    g.sleep(900)
    r = g.js("(() => { __on = false; return __dy; })()")
    alive = [q for q in r if not q[0]][:10]
    dying = [q for q in r if q[0]]
    assert len(dying) >= 5, (len(r), len(dying))
    white0, body0 = max(q[1] for q in alive), min(q[2] for q in alive)
    assert max(q[1] for q in dying[:len(dying) // 2]) > 2 * white0 + 60, (white0, [q[1] for q in dying])       # white, in its first moments
    assert min(q[2] for q in dying[:len(dying) // 2]) > .4 * body0, (body0, [q[2] for q in dying])              # its body still there: not gone in a frame
    assert not g.errors
