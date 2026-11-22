"""A running creature is drawn on every frame it is in view and not truly behind land (hd.js bodies). The owner:
"sometimes when mobs run they disappear". The server has a body at its NEXT tile's height (e.z) the moment it starts
the step; the page draws it sliding there from the tile it left. Running off a hill's foot, half a tile still on the
hill, it was put at the meadow's level inside the hill: the rule "a body under solid land is not seen" dropped it for a
frame or three, a step at a time. And bodies were drawn 16 tiles across and 12 south whatever the screen showed."""

import pytest
from conftest import Game, new_name
from test_e2e_hd_sun import hd

# a chicken the page is told of at each tick, as the server tells of one (its tile, the height of that tile, running),
# along a fixed path; and, each frame, where it is drawn, if it is, and the ground under the tile it is drawn on
RUN = """([path, x0, y0]) => { window._run = []; let i = 0; const t0 = window._t0 = onTick;
  onTick = function (d) { const [dx, dy] = path[Math.min(i++, path.length - 1)], x = x0 + dx, y = y0 + dy;
    d.entities = d.entities.concat([{id: 999999, kind: 'chicken', x, y, z: topAt(x, y), hp: 2, run: true, scared: true}]); return t0(d); };
  const f0 = frame; frame = function (now) { f0(now); const q = ents.get('chicken999999'); if (!q || !HdLook.live) return;
    const qx = Math.round(q.x), qy = Math.round(q.y), g = topAt(qx, qy), a = HdLook.screenOf(q.x + .5, q.y + .5, g), b = HdLook.bodies().filter((s) => s[0] === 'chicken');
    window._run.push({x: +(q.x - x0).toFixed(2), y: +(q.y - y0).toFixed(2), g, drawn: b.length ? b[0][1] : null, behind: HdLook.hidden(q.x + .5, q.y + .5, g),
      view: !!a && a[0] > 20 && a[1] > 20 && a[0] < innerWidth - 20 && a[1] < innerHeight - 20}); };
  return 1; }"""


def run(g, path):
    """The chicken along `path` (tiles from you), a tile a tick -> the frames it was in view and not behind land, those
    of them with no chicken drawn, and those drawn at another level than the ground under it."""
    x, y = g.pos()
    g.js(RUN, [path, x, y])
    g.tick(len(path) + 2)
    rec = g.js("window._run")
    g.js("(() => { onTick = window._t0; ents.delete('chicken999999'); return 1; })()")
    seen = [r for r in rec if r["view"] and not r["behind"]]
    return seen, [r for r in seen if r["drawn"] is None], [r for r in seen if r["drawn"] is not None and r["drawn"] != r["g"]]


@pytest.mark.realtime                                                       # (the game's own time: every frame of each step, not a quarter of them)
def test_a_running_creature_is_drawn_on_every_frame_across_meadow_trees_and_a_hill_foot(browser, server):
    g = hd(browser, server)
    g.hour(.3, still=True)
    g.stamp(1, 3, ["..."] * 3, levels=["333"] * 3)                         # a hill three high, its north foot on row y + 3
    g.stamp(-4, 2, ["T.T"])                                                 # trees beside the path
    g.rest()
    seen, lost, wrong = run(g, [(i, 3) for i in range(-6, 7)] + [(i, 3) for i in range(6, -7, -1)] + [(i, 6) for i in range(-6, 7)] + [(6, 6)] * 4)
    assert len(seen) > 60, len(seen)
    assert {r["g"] for r in seen} >= {0, 3}, "it ran over the hill"
    assert not lost, f"{len(lost)} of {len(seen)} frames in view with no chicken drawn: {lost[:6]}"     # (it was 5 of 265: half a step off the hill's foot)
    assert not wrong, f"{len(wrong)} frames drawn at another level than the ground under it: {wrong[:6]}"


def test_a_creature_running_to_the_screens_edge_is_drawn_until_it_leaves_it(browser, server):
    g = Game(browser.new_page(viewport={"width": 1440, "height": 900}), server)
    g.join(new_name(), 2)                                                   # (zoom 2: 22 tiles each way, 18 south on the screen)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    g.rest()
    seen, lost, _ = run(g, [(i, 0) for i in range(0, 24)] + [(-i, 4) for i in range(0, 24)] + [(2, i) for i in range(4, 20)])
    assert max(abs(r["x"]) for r in seen) > 18 and max(r["y"] for r in seen) > 13, (len(seen), seen[-3:])
    assert not lost, f"{len(lost)} of {len(seen)} frames in view with no chicken drawn: {lost[:6]}"     # (it went at 16 tiles across, 12 south)
