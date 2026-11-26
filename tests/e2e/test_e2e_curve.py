"""The curved world (web/js/curve.js; hd.js viewOf): the ground bends away to the horizon the view distance puts, with
a sky over it. A setting, on or off: off, the HD look's land is flat, drawn to the picture's top, no sky."""

from test_e2e_hd_sun import hd


def test_curved_world_is_a_setting_on_the_picture_page_on_unless_chosen_otherwise(game):
    """The settings' "Curved world", On by default, and what it says is what is drawn: on, the land bends (the bend
    viewOf works out for the view distance) to a horizon with the sky over it; off, no bend, no sky, and the land
    reaches the picture's top: no px of it without land. (Its Near and Far moved the sky's line; the land stayed bent.)"""
    assert game.js("OPT_DEFAULT.curve") is True and game.js("opt('curve')") is True
    assert game.js("MENU_PAGES.find((p) => p[0] === 'Picture')[1].find((r) => r.name === 'Curved world').kind") == "toggle"
    game.js("(() => { Curve.force = null; return 1; })()")       # (the setting decides, not the page's address)
    game.wait("Curve.on && HdLook.bend > 0")
    game.js("setOpt('curve', false)")
    game.wait("!Curve.on && HdLook.bend === 0 && HdLook.view.b === 0")
    game.rest()
    assert game.js("HdLook.bare()") == 0                         # the land to the picture's top
    game.js("setOpt('curve', true)")
    game.wait("Curve.on && HdLook.bend > 0")


# where a column of the land, rows r[0] down to r[1] a quarter of a tile apart, is drawn (CSS px, the land's own projection)
COLUMN = """(r) => { const p = myPos(), L = HdLook.level[1], out = [];
  for (let y = r[0]; y >= r[1] - 1e-9; y -= .25) out.push([y, HdLook.screenOf(p.x + 4.5, y + .5, L)]);
  return out; }"""


def creases(pts):
    """The rows where the drawn column turns (a facet's corner): a straight run of land is a straight line on the screen."""
    turn = []
    for (_, a), (y, b), (_, c) in zip(pts, pts[1:], pts[2:]):
        u, v = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
        turn.append((y, abs(u[0] * v[1] - u[1] * v[0]) / max(1e-9, (u[0] ** 2 + u[1] ** 2) ** .5 * (v[0] ** 2 + v[1] ** 2) ** .5)))
    top = max(t for _, t in turn)
    assert top > 1e-3, turn                                      # (the land is bent here: it turns somewhere)
    return {y for y, t in turn if t > top / 4}


def test_the_bends_creases_stay_where_they_are_on_the_land_as_you_walk(browser, server):
    """The bend's flat facets meet at rows of the world, not at rows counted from you (#86): walking north a tile at a
    time, a far straight run of meadow turns at the same rows each time. (Counted from you, a crease slid along a far
    block as you walked.)"""
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.js("(() => { Curve.force = null; setOpt('curve', true); setOpt('view', 65); zoom = ZOOM.to = 2; return 1; })()")   # (zoomed out: this short picture sees farthest)
        g.rest()
        g.wait("HdLook.bend > 0")
        n = g.js("HdLook.view.n")
        assert n >= 25, n                                        # (room for creases between 9 tiles off and the horizon)
        rows = (y - 12, y - n + 3)                               # (9 tiles off at the least, past the curve near you; short of the horizon)
        seen = []
        for k in range(4):
            g.rpc("dev_teleport", x=x, y=y - k)
            g.arrive()
            g.rest()
            seen.append(creases(g.js(COLUMN, list(rows))))
        assert len(seen[0]) >= 2 and all(s == seen[0] for s in seen), (n, rows, seen)
        assert not g.errors, g.errors
    finally:
        g.js("(() => { setOpt('view', OPT_DEFAULT.view); zoom = ZOOM.to = 3; return 1; })()")
        g.page.close()
