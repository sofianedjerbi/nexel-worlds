"""The HD look's paints (vox_style.js: one sheet of the land's paints, each face names its place in it): what a land is
drawn with is always its own. The owner saw, now and then, a meadow of grey and green squares, flat faces of the mean
colour and black blades on the grass, a beige square on a ledge's corner: faces that named places of paints gone.
Each test makes it happen at once, then asks the land to be the land made from none."""

import os

from conftest import Game, new_name


def hd(browser, server):
    g = Game(browser.new_page(viewport={"width": 960, "height": 540}), server)
    g.join(new_name(), 3, look="hd")
    g.js("setOpt('names', false); setOpt('hints', false); setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    g.rest()
    return g


# the land's picture as the screen shows it (hd_view.js read: no page element over it), kept; then the px of it that differ
# from the one kept by more than 30 of 3 x 255: under the sky (its clouds drift), out of a box round you (you breathe,
# and your shadow with you)
KEEP = "(() => { window.__kept = HdLook.read(0, 0, innerWidth * devicePixelRatio, innerHeight * devicePixelRatio); return 1; })()"
DIFF = """(me) => { const A = window.__kept, B = HdLook.read(0, 0, A.width, A.height), k = devicePixelRatio; let n = 0;
  for (let i = 0; i < A.data.length; i += 4) { const p = i / 4, x = p % A.width / k, y = (p / A.width | 0) / k; if (y < innerHeight * .35 || (Math.abs(x - me[0]) < 72 && y - me[1] > -90 && y - me[1] < 50)) continue;
    if (Math.abs(A.data[i] - B.data[i]) + Math.abs(A.data[i + 1] - B.data[i + 1]) + Math.abs(A.data[i + 2] - B.data[i + 2]) > 30) n++; } return n; }"""
ME = "(() => { const p = ents.get('agent' + myId); return HdLook.screenOf(p.x + .5, p.y + .5, HdLook.level[2]); })()"


def made(g):
    """the land made (no making going on, nothing left to make for where you are) and drawn"""
    g.wait("!HdLook.busy", 20000); g.rest(); g.wait("!HdLook.busy", 20000); g.frames(3)


def against_none(g):
    """-> (px of the mean colour on the screen, px that differ from the same land made again with its paints from none)"""
    raw = g.js("HdLook.raw()"); g.js(KEEP); a = g.page.screenshot()
    g.js("HdLook.forget()"); made(g)
    off = g.js(DIFF, g.js(ME))
    if os.environ.get("PAINTS_DUMP"):                        # (the two pictures, to look at: PAINTS_DUMP=/some/dir/prefix)
        n = os.environ["PAINTS_DUMP"] + new_name("p")
        open(n + "_a.png", "wb").write(a); g.page.screenshot(path=n + "_b.png")
    return raw, off


def test_the_land_wiped_while_one_is_made_is_drawn_with_its_own_paints(browser, server):
    """The paints ran out (eng.lost: the land and its paints wiped) while a land was being made: that land's chunks were
    kept, and the next land, made with its paints from none, drew them with the places of paints that were gone (the
    owner's patchwork, in seed 12's caves at (-58, 47) after walking at a sprint)."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(-6, 2, ["............"] * 4, levels=["666666666666"] * 4)        # (a plateau of stone south, steps of earth north: tiles with paints of their own)
        g.stamp(-6, -5, ["......"] * 3, levels=["222222", "333333", "444444"])
        g.hour(.375, still=True)
        made(g); g.js("HdLook.forget()")                          # (the whole land made again, a tile a step...)
        g.page.wait_for_function("() => HdLook.busy && (HdLook.forget(), true)", timeout=20000)   # (...and wiped while it is being made)
        made(g)
        raw, off = against_none(g)
        assert raw == 0 and off < 50, (raw, off)
    finally:
        g.page.close()


def test_the_things_sheet_emptied_in_the_middle_of_a_tile_leaves_none_of_its_pieces_with_another_paint(browser, server):
    """The things' sheet (hd_things.js `room`: a rock's oval of shade, a wall's planks, the hour's shadows) is emptied when
    full, under a new name. Pieces of a tile asked for before that moment kept their place in the old sheet and were
    painted from the new one: another paint, or none (a shadow's black picture where a piece's own was)."""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(-2, -3, ["M"])
        g.hour(.3, still=True); made(g)
        got = g.js("""([x, y]) => { const S = HdThings.sheet, W = S.w, put1 = (put) => put(0, 0, 0xff00ff00);
          const paint = (b) => { let n = 0; for (let j = 0; j < b.d; j++) for (let i = 0; i < b.w; i++) if (S.px[(b.top[1] + (b.win ? b.win[1] : 0) + j) * W + b.top[0] + (b.win ? b.win[0] : 0) + i] >>> 24) n++; return n; };
          const full = () => { for (let j = 0; ; j++) { const id = S.id, p = HdThings.room('full' + j + Math.random(), 16, 16, put1); if (S.id !== id) return false; if (p[0] + 32 > W && p[1] + 32 > W) return true; } };
          for (let t = 0; t < 3; t++) { HdSun.key(); HdThings.at(x, y); if (full()) break; }                 // (the rock's oval and its shadow in the sheet, then the sheet filled to its last place)
          clock.phase = .62; HdSun.key(); const id1 = S.id, out = HdThings.at(x, y) || [];                    // (another hour: a new shadow to put in a full sheet)
          return [S.id !== id1, out.filter((b) => b.top).map((b) => [b.shade ? 'shade' : 'piece', b.w * b.d, paint(b)])]; }""", [x - 2, y - 3])
        emptied, pieces = got
        assert emptied and pieces, got                          # (the sheet was emptied by that very ask)
        assert all(n > 0 for _, _, n in pieces), pieces
    finally:
        g.page.close()
