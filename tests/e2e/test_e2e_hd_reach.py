"""Who is drawn as far as the HD look shows land (hd.js bodies, HdLook.reach; state.js watch). The owner: "entity view
distance is too small: mobs disappear when visible". Bodies were drawn 12 rows north whatever the screen showed (a hill
26 rows off at zoom 3 on a desk, level ground 17 rows off on a phone held upright), and the server told of who stood in
the top-down screen's rows: land the page had loaded and drew past them was empty."""

import pytest
from game import Game, new_name

# the land's tiles the picture shows (a top over all the nearer ones' and on the screen, `inset` px in from its edges),
# none in water: the one furthest north, south, east and west -> {n: [dx, dy], ...} from you
EDGES = """(inset) => { const p = myPos(), tx = Math.round(p.x), ty = Math.round(p.y), W = innerWidth, H = innerHeight, best = {};
  const col = (x, y) => { const c = Voxels.host.column(x, y); return c && c.length ? c[c.length - 1] : null; };
  const z0 = topAt(tx, ty); let d0 = 0; for (let ya = -1e9; d0 < 40; d0++) { const a = HdLook.screenOf(tx + .5, ty + d0 + .5, z0); if (!a || a[1] <= ya || ya > H) break; ya = a[1]; }   // (south as far as the rows go down the picture: past the eye they come back up)
  for (let dx = -60; dx <= 60; dx++) { let sky = 1e9; for (let dy = d0; dy >= -60; dy--) { const x = tx + dx, y = ty + dy, t = col(x, y); if (t === null) continue;
    const a = HdLook.screenOf(x + .5, y + .5, t); if (!a || a[1] > H * 2 || a[1] >= sky) continue; sky = a[1];
    if (Voxels.host.water(x, y) || a[0] < inset || a[0] > W - inset || a[1] < inset + 30 || a[1] > H - inset) continue;
    for (const [k, v] of [['n', -a[1]], ['s', a[1]], ['e', a[0]], ['w', -a[0]]]) if (!best[k] || v > best[k][2]) best[k] = [dx, dy, v]; } }
  return Object.fromEntries(Object.entries(best).map(([k, v]) => [k, v.slice(0, 2)])); }"""


def look(g):
    g.rpc("dev_creatures", clear=90)
    g.tick(2)
    g.rest()
    edges = g.js(EDGES, 24)
    assert set(edges) == {"n", "s", "e", "w"}, (edges, g.pos(), g.js("[HdLook.live, !!HdLook.screenOf(0, 0, 0), zoom]"))
    ids = {k: g.rpc("dev_creatures", kind="chicken", dx=dx, dy=dy, still=100000)["spawned"] for k, (dx, dy) in edges.items()}
    g.wait(f"[{','.join(str(i) for i in ids.values())}].every((i) => ents.has('chicken' + i))", 8000)   # (the server told of them)
    g.tick(2)
    g.frames(3)
    drawn = g.js("HdLook.bodies().filter((b) => b[0] === 'chicken').length")
    return edges, ids, drawn


def check(g, what):
    for z in (2, 4, 6):
        g.js(f"zoomBy({z} - zoom)")
        g.wait(f"zoom === {z} && !ZOOM.busy")
        edges, ids, drawn = look(g)
        assert drawn == 4, f"{what} zoom {z}: chickens at the screen's edges {edges}: {drawn} of 4 drawn"


def test_creatures_at_each_edge_of_a_desks_screen_are_told_of_and_drawn(browser, server):
    g = Game(browser.new_page(viewport={"width": 1440, "height": 900}), server)
    g.join(new_name("rd"), 2)
    g.js("setOpt('names', false); setOpt('hints', false)")
    check(g, "desk")


@pytest.mark.parametrize("w,h", [(390, 844), (844, 390)])
def test_creatures_at_each_edge_of_a_phones_screen_are_told_of_and_drawn(browser, server, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True, device_scale_factor=3)
    try:
        g = Game(ctx.new_page(), server)
        g.join(new_name("rp"), 2)
        g.js("setOpt('names', false); setOpt('hints', false)")
        check(g, f"phone {w}x{h}")
    finally:
        ctx.close()


# a chicken the page is told of at each tick, walking west a tile a tick from off the screen's east edge; each frame:
# its feet on the screen or not, drawn or not
WALK = """([x0, y0, n]) => { window._walk = []; let i = 0; const t0 = window._t0 = onTick;
  onTick = function (d) { const x = x0 - Math.min(i++, n), y = y0; d.entities = d.entities.concat([{id: 999998, kind: 'chicken', x, y, z: topAt(x, y), hp: 2}]); return t0(d); };
  const f0 = window._f0 = frame; frame = function (now) { f0(now); const q = ents.get('chicken999998'); if (!q || !HdLook.live) return;
    const a = HdLook.screenOf(q.x + .5, q.y + .5, topAt(Math.round(q.x), Math.round(q.y)));
    window._walk.push({x: q.x, on: !!a && a[0] >= 0 && a[0] <= innerWidth && a[1] >= 0 && a[1] <= innerHeight, drawn: HdLook.bodies().some((b) => b[0] === 'chicken')}); };
  return 1; }"""


@pytest.mark.realtime                                       # (every frame of each step)
def test_a_creature_walking_in_from_off_the_screen_is_drawn_before_its_feet_are_on_it(browser, server):
    g = Game(browser.new_page(viewport={"width": 1440, "height": 900}), server)
    g.join(new_name("rw"), 4)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=90)
    g.clear_area(12)
    g.rest()
    x, y = g.pos()
    reach = g.js("HdLook.reach")
    assert reach and reach[2] - x >= 9, reach                    # (zoom 4 on a desk: 11 tiles east show)
    # the server tells of one off the screen's east edge, a tile past what shows
    cid = g.rpc("dev_creatures", kind="cow", dx=reach[2] - x + 2, dy=0, still=100000)["spawned"]
    g.wait(f"ents.has('cow{cid}')", 8000)
    g.js(WALK, [reach[2] + 3, y, 16])
    g.tick(20)
    rec = g.js("(() => { onTick = window._t0; frame = window._f0; ents.delete('chicken999998'); return window._walk; })()")
    first = next((i for i, r in enumerate(rec) if r["on"]), None)
    assert first is not None, (len(rec), rec[:3], rec[-3:], reach, (x, y))
    assert first > 0 and rec[first - 1]["drawn"] and all(r["drawn"] for r in rec[first:]), rec[max(0, first - 3):first + 3]
