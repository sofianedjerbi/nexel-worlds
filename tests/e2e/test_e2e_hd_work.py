"""Work done for nothing in the HD look, counted (no clock): a block of land comes in whole, its tiles not painted for the
classic picture (tiles.js arriveBlock: it was 1024 tiles painted over frames, each making the land again); the far land's
patches are kept by where they are (vox_style_land.js); the paints' sheet gives the places of paints no longer used and
is never wiped (vox_style.js evict); a person's sheet is made between frames (wear.js)."""

import pytest
from test_e2e_hd_sun import hd

# (__n: blocks come in, of the screen's and of the far land the HD look draws to its horizon (state.js HdLook.far, since
#  9c681e2): each puts its neighbours' edge tiles to be drawn again, and the far ones never arrive (arriveBlock is the
#  screen's): counted by arrivals, 243 a block, two runs in three)
DRAWN = """(() => { window.__d = 0; window.__a = 0; window.__n = 0; const d0 = drawTile, a0 = arriveBlock, r0 = onRegion; drawTile = function (x, y, to) { if (!to) __d++; return d0.apply(this, arguments); };
  arriveBlock = function () { __a++; return a0.apply(this, arguments); };
  onRegion = function (d) { if (d.w === B && !blocks.has(bkey(d.x / B, d.y / B))) __n++; return r0.apply(this, arguments); }; return 1; })()"""


@pytest.mark.realtime
def test_land_comes_in_whole_and_its_paints_are_never_wiped(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    g.js(DRAWN)
    before = g.js("HdLook.work")
    for k in range(1, 6):                                          # (five places, each a land of its own: some 2000 paints each, 4096 places)
        g.rpc("dev_teleport", x=x + 70 * k, y=y)
        g.arrive()
        g.rest()
    n, came = g.js("[__a, __n]")
    assert g.js("[...blocks.values()].every((b) => !b.drawn || b.px.length === 0)")          # (no block painted for the classic picture)
    assert n >= 5 and g.js("__d") <= 160 * came, (g.js("__d"), n, came)     # (blocks come in; only the edge tiles beside each are drawn again: before, 1024 a block)
    assert g.js("HdLook.work.wipes") == before["wipes"]            # (the land never made again from none for want of places)


# every block of the far land the HD look draws (HdLook.far, state.js) has come
FAR = "(() => { const f = HdLook.far; if (!f) return true; for (let by = Math.floor(f[1] / B); by <= Math.floor(f[3] / B); by++) for (let bx = Math.floor(f[0] / B); bx <= Math.floor(f[2] / B); bx++) if (!blocks.has(bkey(bx, by))) return false; return true; })()"


@pytest.mark.realtime
def test_walking_back_the_far_land_is_not_made_again(browser, server):
    """(Counted once the far land asked for has come (FAR): its blocks come four a tenth of a second (state.js, since
    9c681e2), and one that came while you walked back made its patches again, rightly, they were drawn from nothing:
    653 against 1131, one run in three.)"""
    g = hd(browser, server)
    x, y = g.pos()
    g.wait(FAR, 15000)
    g.rest()
    f0 = g.js("HdLook.work.fars")
    g.page.keyboard.down("ArrowRight")
    g.wait(f"myPos().x >= {x + 8}", timeout=8000)
    g.page.keyboard.up("ArrowRight")
    g.wait(FAR, 15000)
    g.rest()
    f1, k1, b1 = g.js("HdLook.work.fars"), g.js("HdLook.work.forgot"), g.js("[...blocks.keys()]")
    g.page.keyboard.down("ArrowLeft")
    g.wait(f"myPos().x <= {x}", timeout=8000)
    g.page.keyboard.up("ArrowLeft")
    g.rest()
    f2, k2 = g.js("HdLook.work.fars"), g.js("HdLook.work.forgot")
    # (the way back makes again what the world changed meanwhile, rightly: a tile changed lets go of the far patches that
    # read it (vox_land_far.js forget). Those are not counted; the blocks that came on the way back are said. 367 made
    # against 342, one run in seven: which of the two it was, the message says now, #240)
    came = sorted(set(g.js("[...blocks.keys()]")) - set(b1))
    assert f1 - f0 > 200 and f2 - f1 - min(k2 - k1, f2 - f1) < (f1 - f0) / 3, \
        {"made": (f0, f1, f2), "forgot on the way back": k2 - k1, "blocks come on the way back": came, "work": g.js("HdLook.work"), "far": g.js("HdLook.far")}   # (the way back: its patches were made on the way there)


def test_a_persons_sheet_is_made_between_frames(browser, server):
    g = hd(browser, server)
    r = g.js("""(async () => { let idle = 0; const ric = window.requestIdleCallback; window.requestIdleCallback = (f, o) => ric((d) => { idle++; f(d); }, o);
      const ask = () => wornReady('#123457', {head: 'straw_hat'}, 'bear', false), first = ask();
      for (let i = 0; i < 3000 && !ask(); i++) await new Promise((done) => setTimeout(done, 20));
      window.requestIdleCallback = ric; const s = ask(); return [first === null, !!s && s.width === IMG.character.width, idle]; })()""")
    assert r[0] and r[1] and r[2] >= 2, r                           # (not made at once; made, in two turns or more)
    # (the loop is a wait, not a budget: 200 turns of 20 ms were a second of the machine's on the tests' clock, and a bear's dressed sheet takes 300 to 500 turns, before the cubes as after)
