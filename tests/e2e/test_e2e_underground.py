"""Being under ground as it is seen (web/js/xray.js, voxels.js, daylight.js): one view for a stair under a hill, a
tunnel, a room: the land cut open over the place you are in; the light in it, by day
and by night. (The dug look itself, and build mode's digging: test_e2e_digging.py; caves under hills:
test_e2e_caves.py.)"""

import pytest
from test_e2e_digging import DRAWN, GREEN_ON_SCREEN, LAND, SEEN, cut, earth, sliced


def test_a_stair_dug_under_a_hill_is_a_burrow_in_the_bank_not_floors_lying_on_the_hill(game):
    game.js("Underground.force = 0")   # (the cut as the game paints it: the underground view, underground.js, is laid over it)
    """doben4's stair, dug west from a pit, under a hill that rises as it goes down ("this is very weird and ugly !"):
    under a hill a view of its own drew each floor alone where it is drawn, tiles south of the stair, squares of earth
    on the hill. "everything should have the same view ! ... an unique 'player is hided, xray on' view": under a hill
    as under the meadow you are seen through what hides you, and the stair's floors are of the place you are in, each
    at its own depth: earth on the screen, there, under you and over you."""
    game.js("setOpt('depth', false)")                         # (the land as it is painted: these colours and shades were measured with no sun; the land's depth has its own tests)
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-9, -3, ["." * 10] * 7, levels=["3322110000"] * 7)
    game.stamp(-9, 0, ["." * 10], levels=["ffedcbba00"], roofs=["9976400000"], heads=["2222200000"])
    X = x - 6                                                  # four down, under a hill two high
    game.rpc("dev_teleport", x=X, y=y + 1, z=2)               # on the hill beside it: the hill, whole
    game.wait(f"myAt && myAt.x === {X} && myAt.z === 2", 8000)
    game.wait(DRAWN, 8000); game.sleep(600)
    assert game.js(f"[xray.a, standAt({X}, {y}), hiddenAt({X}, {y})]") == [0, 2, True]
    game.rpc("dev_teleport", x=X, y=y, z=-4)                 # on the stair
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(SEEN, 20000); game.sleep(300)
    assert game.js(f"[-9, -8, -7, -6, -5, -4].map((d) => seenUnder({x} + d, {y}))") == [-6, -6, -5, -4, -3, None]
    assert game.js(f"[standAt({X}, {y}), hiddenAt({X}, {y}), xray.pic.floor.size]") == [-4, False, 5]
    steps = game.js(LAND, [[x + d, y, f, 8, 8] for d, f in ((-9, -6), (-8, -6), (-7, -5), (-6, -4), (-5, -3))])
    assert all(earth(c) for c in steps), steps                # every floor of it, where it is drawn: under you, yours, the one you came down
    south = game.js(LAND, [[X, y + 1, -4, 8, 8]])[0]
    assert sliced(south), south                                # ...and no floor a tile south of the stair: the ground in front, cut open
    assert not game.errors


def test_earth_left_between_two_tunnels_is_the_nearer_ones_back_wall_not_a_strip_of_meadow(game):
    game.js("Underground.force = 0")   # (the cut as the game paints it: the underground view, underground.js, is laid over it)
    """Two tunnels side by side, four down, joined at one end: the earth between them hides the far one and is left
    out; where it stood the land as drawn showed, a strip of meadow between two floors, and the nearer tunnel was a
    floor lying on the grass. Then it was cut level with the floors: a row nobody dug, shown as gone. The earth
    between them is no floor of the place, and on the screen it is earth cut through: no meadow, no floor."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, 0, ["...."], levels=["abcd"])
    game.rpc("dev_stamp", x=x + 5, y=y, rows=["......", ".", "......"], levels=["dddddd", "d", "dddddd"], roofs=["444444", "4", "444444"], heads=["222222", "2", "222222"])
    X = x + 8
    game.rpc("dev_teleport", x=X, y=y, z=-4)                 # in the far one
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js(f"[seenUnder({X}, {y}), seenUnder({X}, {y + 1}), seenUnder({X}, {y + 2})]") == [-4, None, -4]
    far, between, near = game.js(LAND, [[X, y, -4, 8, 8], [X, y + 1, -4, 8, 8], [X, y + 2, -4, 8, 8]])
    assert earth(far) and earth(near) and sliced(between), (far, between, near)
    assert game.js(GREEN_ON_SCREEN, [[X, y, 4], [X, y + 1, 4], [X, y + 2, 4]]) == [0, 0, 0]
    assert not game.errors


# the screen without anybody on it: the mean brightness (r + g + b) of each tile [x, y] where the land at sea level is drawn
BRIGHT = """(tiles) => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
  frame(performance.now()); const S = TS(), [ox, oy] = screenOrigin(S), out = [];
  for (const [x, y] of tiles) { const px = ctx.getImageData(Math.round((ox + x * S) * DPR), Math.round((oy + y * S) * DPR), S * DPR, S * DPR).data; let n = 0;
    for (let i = 0; i < px.length; i += 4) n += px[i] + px[i + 1] + px[i + 2]; out.push(Math.round(n / (px.length / 4))); }
  Object.assign(window, keep); return out; }"""


def test_at_night_a_fire_under_a_roof_lights_nothing_of_the_meadow_over_it(game):
    """Night's lights were drawn where they are on the screen, roof or no roof: a fire in a tunnel lit a ring of the
    meadow over it (and who hid under the ground glowed through it). A light under a roof lights what is under that
    roof: seen through, the picture of the place; hidden, nothing (daylight.js)."""
    game.clear_area(16)
    x, y = game.pos()
    game.stamp(-8, 0, ["........^......."], levels=["abcddddddddddddd"], roofs=["0000444444444444"], heads=["0000222222222222"])
    game.rpc("dev_time", phase=.85)
    game.rpc("dev_teleport", x=x + 7, y=y - 4, z=0)           # on the meadow, away from the fire (it is under (x, y), four down)
    game.wait(f"myAt && myAt.x === {x + 7} && myAt.y === {y - 4}", 8000)
    game.wait(DRAWN, 8000); game.sleep(900)
    assert game.js(f"[combAt({x}, {y}), hiddenAt({x}, {y}), xray.a]") == ["^", True, 0]
    over, beside, far = game.js(BRIGHT, [[x, y], [x, y + 1], [x + 15, y + 1]])
    assert far > 100 and abs(over - far) < 25 and abs(beside - far) < 25, (over, beside, far)   # the meadow over the fire: as dark as the meadow anywhere
    assert not game.errors


@pytest.mark.realtime
def test_light_is_one_shade_under_a_roof_no_edge_along_the_tunnel(game):
    game.js("Underground.force = 0")   # (the cut as the game paints it: the underground view, underground.js, is laid over it)
    """"See how lightning is cut ? Uniformise it with a real lightning model": the earth cut through over a tunnel was
    a flat shade darker from the roof's edge on, a line down the wall where the roof starts, and a stair of light and
    dark along the floor. Under a roof the land has one shade, a cave's own dark (vox_engine.js): the tunnel's floor
    is the same all along, and darker than the same floor under the sky at the stair's foot."""
    game.js("setOpt('depth', false)")                         # (the land as it is painted: these colours and shades were measured with no sun; the land's depth has its own tests)
    game.clear_area(14)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, 0, ["........"], levels=["abcddddd"], roofs=["00004444"], heads=["00002222"])
    X = x + 6
    game.rpc("dev_teleport", x=X, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    sky, first, mine, on = game.js(LAND, [[x + 4, y, -4, 8, 8], [x + 5, y, -4, 8, 8], [X, y, -4, 8, 8], [X + 1, y, -4, 8, 8]])
    assert all(earth(c) for c in (sky, first, mine, on)), (sky, first, mine, on)
    assert max(abs(a - b) for c in (mine, on) for a, b in zip(c, first)) <= 12, (first, mine, on)
    assert sum(first) < .8 * sum(sky), (sky, first)
    assert not game.errors


def test_walking_down_a_stair_under_a_roof_the_underground_view_comes_on_and_stays_on(game):
    """The owner's cave: a stair going west down from the meadow under a roof ("the view still does not work... the
    game should have the same consistent hd-2d view everywhere"). Walked the real way (keys, no force): on the meadow
    the game's view; at the stair's open head, under the roof, at its foot: the slice through the earth (underground.js),
    drawn over the whole screen: strata, no meadow green round you."""
    game.clear_area(14)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-8, 0, ["........"], levels=["ddddcba0"], roofs=["44440000"], heads=["22220000"])
    game.wait(DRAWN, 8000); game.sleep(600)
    assert game.js("[Underground.on, xray.a]") == [False, 0]
    seen = []
    for _ in range(8):
        game.hold(["ArrowLeft"], 330); game.sleep(500)
        seen.append(game.js("[Math.round(ents.get('agent' + myId).x), xray.L, xray.a > .5, Underground.a]"))
    down = [s for s in seen if s[2]]
    assert down and all(s[3] > 0 for s in down), seen       # wherever the cut is on: the new view, never the old flat cut
    assert seen[-1][1] <= -3 and seen[-1][3] == 1, seen
    green = game.js("""(() => { const d = ctx.getImageData(0, 0, cv.width, cv.height).data; let g = 0, n = 0;
      for (let i = 0; i < d.length; i += 4 * 97) { n++; if (d[i + 1] > 150 && d[i + 1] > d[i] + 30 && d[i + 1] > d[i + 2] + 40) g++; } return g / n; })()""")
    assert green < .02, green                                  # the strata over the screen, not the meadow
    assert not game.errors
