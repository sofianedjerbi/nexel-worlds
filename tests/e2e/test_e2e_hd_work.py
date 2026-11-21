"""Work done for nothing in the HD look, counted (no clock): a block of land comes in whole, its tiles not painted for the
classic picture (tiles.js arriveBlock: it was 1024 tiles painted over frames, each making the land again); the far land's
patches are kept by where they are (vox_style_land.js); the paints' sheet gives the places of paints no longer used and
is never wiped (vox_style.js evict); a person's sheet is made between frames (wear.js)."""

import pytest
from test_e2e_hd_sun import hd

DRAWN = """(() => { window.__d = 0; window.__a = 0; const d0 = drawTile, a0 = arriveBlock; drawTile = function (x, y, to) { if (!to) __d++; return d0.apply(this, arguments); };
  arriveBlock = function () { __a++; return a0.apply(this, arguments); }; return 1; })()"""


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
    n = g.js("__a")
    assert g.js("[...blocks.values()].every((b) => !b.drawn || b.px.length === 0)")          # (no block painted for the classic picture)
    assert n >= 5 and g.js("__d") <= 160 * n, (g.js("__d"), n)     # (blocks come in; only the edge tiles beside each are drawn again: before, 1024 a block)
    assert g.js("HdLook.work.wipes") == before["wipes"]            # (the land never made again from none for want of places)


@pytest.mark.realtime
def test_walking_back_the_far_land_is_not_made_again(browser, server):
    g = hd(browser, server)
    x, y = g.pos()
    f0 = g.js("HdLook.work.fars")
    g.page.keyboard.down("ArrowRight")
    g.wait(f"myPos().x >= {x + 8}", timeout=8000)
    g.page.keyboard.up("ArrowRight")
    g.rest()
    f1 = g.js("HdLook.work.fars")
    g.page.keyboard.down("ArrowLeft")
    g.wait(f"myPos().x <= {x}", timeout=8000)
    g.page.keyboard.up("ArrowLeft")
    g.rest()
    f2 = g.js("HdLook.work.fars")
    assert f1 - f0 > 200 and f2 - f1 < (f1 - f0) / 3, (f0, f1, f2)   # (the way back: its patches were made on the way there)


def test_a_persons_sheet_is_made_between_frames(browser, server):
    g = hd(browser, server)
    r = g.js("""(async () => { let idle = 0; const ric = window.requestIdleCallback; window.requestIdleCallback = (f, o) => ric((d) => { idle++; f(d); }, o);
      const ask = () => wornReady('#123457', {head: 'straw_hat'}, 'bear', false), first = ask();
      for (let i = 0; i < 200 && !ask(); i++) await new Promise((done) => setTimeout(done, 20));
      window.requestIdleCallback = ric; const s = ask(); return [first === null, !!s && s.width === IMG.character.width, idle]; })()""")
    assert r[0] and r[1] and r[2] >= 2, r                           # (not made at once; made, in two turns or more)
