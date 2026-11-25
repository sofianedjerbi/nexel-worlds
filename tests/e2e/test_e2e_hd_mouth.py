"""A way into the land seen from any side (vox_style_land.js `mouths`, `mouthShade`): the eye looks north, so a cave's or
a tunnel's mouth that opens north, east or west has its face hidden. The ground in front of it and the land's top over
it are shaded dark toward it (painted with the land, whole art px), so "there is a way in here" is seen; a wall, or a
one-tile alcove with no way on, is not."""

import json

from test_e2e_hd_behind import calm, go
from test_e2e_hd_sun import hd

# the mean light of a piece of a top at level z, (x0, y0) to (x1, y1) in tiles, as it is on the screen (the px inside its corners' box, a px in)
PIECE = """([x0, y0, x1, y1, z]) => { const c = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(([a, b]) => HdLook.screenOf(a, b, z)), k = devicePixelRatio;
  const X0 = Math.ceil(Math.max(c[0][0], c[3][0]) * k) + 1, X1 = Math.floor(Math.min(c[1][0], c[2][0]) * k) - 1, Y0 = Math.ceil(c[0][1] * k) + 1, Y1 = Math.floor(c[2][1] * k) - 1;
  if (X1 <= X0 || Y1 <= Y0) return -1; const d = HdLook.read(X0, Y0, X1 - X0, Y1 - Y0).data; let s = 0; for (let i = 0; i < d.length; i += 4) s += .3 * d[i] + .59 * d[i + 1] + .11 * d[i + 2]; return s / (d.length / 4); }"""


def rect(x0, y0, x1, y1):
    return [[i, j] for j in range(y0, y1 + 1) for i in range(x0, x1 + 1)]


def test_a_tunnel_mouth_facing_north_east_or_west_is_shaded_on_the_ground_before_it_and_the_top_over_it(browser, server):
    """Three small hills three high round you, each with a tunnel two deep whose mouth faces you: the one south of you
    opens north, the one west of you opens east, the one east of you opens west (their faces are hidden from the eye
    that looks north); a one-tile alcove beside the north one (no way on). The same px read with the tunnels open and
    then filled (a plain wall); the ground before the north one from a pit north of it (from the meadow its own hill hides it): open, the ground in front of each mouth (the half of its tile toward it) and the hill's
    top over it are darker (faintly, a few px deep: the ground before a north one is hidden by its hill, its top tells it, with a little arch on its north edge, 4 px deep); the alcove's are not. It was the same (the ground a little lighter: no wall's corner shade)."""
    g = hd(browser, server)
    calm(g)
    g.js("setOpt('shadows', 0)")
    x, y = g.pos()
    hills = rect(x - 5, y + 2, x - 1, y + 4) + rect(x - 9, y - 4, x - 6, y - 2) + rect(x + 6, y - 4, x + 9, y - 2)
    holes = [[x - 4, y + 2], [x - 4, y + 3], [x - 6, y - 3], [x - 7, y - 3], [x + 6, y - 3], [x + 7, y - 3], [x - 2, y + 2]]
    # (piece of a top: the part of its tile toward the mouth, away from its corners; a top's north piece from its 4th art px: the rim's dark rows along that edge are 2 or 3 as the eye's sub-px place falls, and the open alcove read 7 % darker than the filled one, one dark row more, in most runs, before any change of the mouth's shade)
    look = {"north front": [x - 4 + .2, y + 1 + .55, x - 4 + .8, y + 1 + .95, 0], "north top": [x - 4 + .3, y + 2 + .02, x - 4 + .7, y + 2 + .22, 3],
            "east front": [x - 5 + .05, y - 3 + .2, x - 5 + .45, y - 3 + .8, 0], "east top": [x - 6 + .55, y - 3 + .2, x - 6 + .95, y - 3 + .8, 3],
            "west front": [x + 5 + .55, y - 3 + .2, x + 5 + .95, y - 3 + .8, 0], "west top": [x + 6 + .05, y - 3 + .2, x + 6 + .45, y - 3 + .8, 3],
            "alcove front": [x - 2 + .2, y + 1 + .55, x - 2 + .8, y + 1 + .95, 0], "alcove top": [x - 2 + .2, y + 2 + .25, x - 2 + .8, y + 2 + .45, 3]}
    north = {"north front": [x - 4 + .2, y + 1 + .1, x - 4 + .8, y + 1 + .5, 0]}       # (behind its own hill from the eye on the meadow: read from a pit, the eye over it)
    read = "(() => { const P = " + PIECE + "; return Object.fromEntries(Object.entries(%s).map(([k, v]) => [k, Math.round(P(v))])); })()"

    def both():
        go(g, x, y, 0)
        g.frames(2)
        r = g.js(read % json.dumps({k: v for k, v in look.items() if k != "north front"}))
        go(g, x - 4, y - 3, -3)
        g.frames(2)
        return {**r, **g.js(read % json.dumps(north))}
    try:
        g.rpc("dev_col", tiles=hills, col=[3])
        g.rpc("dev_col", tiles=[[x - 4, y - 3]], col=[-3])
        g.rpc("dev_col", tiles=holes, col=[0, 2, 3])
        opened = both()
        g.rpc("dev_col", tiles=holes, col=[3])
        shut = both()
        assert min(opened.values()) > 0 and min(shut.values()) > 0, (opened, shut)     # (every piece on the screen)
        for k in look:
            if k == "north front":                                               # (the shade is 9 px deep now: the part of that tile the eye sees, from the pit, past its hill, has none. The north mouth is told by its top)
                continue
            if k.startswith("alcove") or k in ("east top", "west top"):
                assert opened[k] > .97 * shut[k], (k, opened, shut)                  # no way in: as a wall; the top over an east or west mouth: no mark ("except for north facing entries, don't show the shadow above")
            else:
                assert opened[k] < .95 * shut[k], (k, opened, shut)                  # a way in: its shade, faint (it was the same, or lighter; then a black smudge: "those black spots ... ugly")
    finally:
        go(g, x, y, 0)
        g.rpc("dev_col", tiles=hills + [[x - 4, y - 3]], col=[0])
        g.js("setOpt('shadows', 100)")
