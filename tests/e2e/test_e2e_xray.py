"""Seen through what hides you, in Chrome (js/xray.js, voxels.js): behind a wall or a mountain the rock in front of
you is cut away, a tile at a time, down to the ground it hides (the land is blocks: the engine leaves them out);
what stands on that rock goes with it, and nothing else changes."""

import pytest

pytestmark = pytest.mark.usefixtures("circle_view")      # (the view that had a circle when the land was painted flat: built roofs still go by it, conftest.py)


def frames(game, body):
    """Frozen frames, one moment (water moves: two moments can't be compared). `body` is JS that returns something; it
    has shot(mode): the screen's px with the land cut open ('on') or not ('off'); box(d, x0, y0, x1, y1): the px of a box of tiles;
    differ(a, b): how many px of two such boxes are not the same. The land alone: nobody is drawn, nor the tile you
    aim at."""
    return game.js("""() => { const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
      const T = performance.now(), keep = {...XRAY}, S = TS(), [ox, oy] = screenOrigin(S), real = {};
      for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { real[f] = window[f]; window[f] = () => null; }
      parts.length = puffs.length = 0; frame(T);
      const shot = (mode) => { Object.assign(XRAY, keep, {wait: 0}, mode === 'off' ? {from: 9, full: 10} : {});
        xray.t = 1; frame(T); xray.a = mode === 'off' || !xray.t ? 0 : 1; frame(T); frame(T); return ctx.getImageData(0, 0, cv.width, cv.height).data; };   // (hidden or not, the frame itself says: t)
      const box = (d, x0, y0, x1, y1) => { const out = [], k = DPR;
        for (let y = Math.round((oy + y0 * S) * k); y < Math.round((oy + y1 * S) * k); y++) for (let x = Math.round((ox + x0 * S) * k); x < Math.round((ox + x1 * S) * k); x++) { const i = (y * cv.width + x) * 4; out.push(d[i], d[i + 1], d[i + 2]); }
        return out; };
      const differ = (a, b) => { let n = 0; for (let i = 0; i < a.length; i += 3) if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2]) n++; return n; };
      const out = (() => { %s })(); Object.assign(XRAY, keep); Object.assign(window, real); window.requestAnimationFrame = raf; raf(frame); return out; }""" % body)


# the land on the screen is made, as blocks (waited for, however busy the machine)
BUILT = """(() => { const [qx, qy, qw, qh] = viewRect(0); for (const b of blocks.values()) if (b.bx * B < qx + qw && (b.bx + 1) * B > qx
  && b.by * B < qy + qh && (b.by + 1) * B > qy && !Voxels.made(b)) return false; return !dirtyTiles.length; })()"""


def differ(a, b):
    """How many px of two boxes of the screen are not the same (the share of them)."""
    return sum(1 for i in range(0, len(a), 3) if a[i:i + 3] != b[i:i + 3]) / max(1, len(a) // 3)


def test_behind_a_mountain_you_are_seen_through_it(game):
    """Behind a wall or a mountain you were cut at its edge: gone. The rock in front of you is cut away (xray.js): you
    show, on the ground you stand on; out from behind it, the rock is back."""
    game.clear_area(10)
    game.stamp(-5, 1, ["." * 11] * 4, levels=["66666666666"] * 4)   # a wall 6 layers high, right in front (south) of you
    game.sleep(900)
    look = """(() => { const k = DPR, w = Math.round(48 * k), d = ctx.getImageData(Math.round(W / 2 * k) - w / 2, Math.round(H / 2 * k) - w / 2, w, w).data;
      return Array.from(d); })()"""
    assert game.js("xray.a") > .95
    seen = game.js(look)
    game.js("(() => { XRAY.from = 1e9; XRAY.full = 2e9; return 1; })()")          # without it: the wall, and nothing of you
    game.sleep(700)
    assert game.js("xray.a") == 0
    hidden = game.js(look)
    assert sum(1 for a, b in zip(seen[::4], hidden[::4]) if abs(a - b) > 24) > len(seen) / 4 * .3
    game.js("(() => { XRAY.from = .7; XRAY.full = .8; return 1; })()")
    game.hold(["w"], 900)                                              # out from behind it
    game.sleep(600)
    assert game.js("xray.a") == 0
    assert not game.errors


def test_what_is_there_shows_without_the_rock_in_front(game):
    """In a canyon, the plateau in front is drawn up over you, over the canyon, and over the cliff behind you. The
    circle showed the canyon's floor alone: above you the front plateau's top layer was still there, over the cliff
    behind. What shows is the land without that plateau: the cliff behind you, down to its foot. Checked
    against the real thing: the same px with the plateau in front taken away."""
    game.clear_area(12)
    game.stamp(-6, -4, ["." * 13] * 9, levels=["8" * 13] * 4 + ["0" * 13] + ["8" * 13] * 4)
    game.sleep(700); game.wait(BUILT, 20000); game.wait("xray.a > .95", 20000)
    x, y = game.pos()
    area = f"{x} - 1 + 5 / 16, {y} - 2, {x} + 2 - 5 / 16, {y} + 1"            # the cliff behind you and your row (not the 4 px at each side: the plateau is cut where it covers you and a tile each side, no more, and the wall of that cut stands there, leaning as walls do: xray.js `seen`)
    on, off = frames(game, f"return [box(shot('on'), {area}), box(shot('off'), {area})];")
    assert on != off
    game.stamp(-6, 1, ["." * 13] * 4, levels=["0" * 13] * 4)         # the plateau in front, gone
    game.sleep(700); game.wait(BUILT, 20000); game.wait("xray.a === 0", 20000)
    gone = frames(game, f"return box(shot('off'), {area});")
    assert differ(on, gone) < .02, differ(on, gone)
    assert not game.errors


def test_the_hidden_ground_shows_and_nothing_changes_away_from_it(game):
    """In a nook open to the north, walls west, east and south of you: the ground the rock in front hides shows,
    the channel behind you, the meadow it is down its middle; and away from you the land is the same, cut or not.
    (It had painted the rock too: first the walls beside you with a tall face down to the cut, walls that are not
    there; then all of it as a brown footprint, wherever the circle reached.)"""
    game.clear_area(10)
    game.stamp(-4, -3, ["." * 9] * 7, levels=["666606666"] * 4 + ["666666666"] * 3)   # a nook, open to the north: walls west, east and south
    game.sleep(700); game.wait(BUILT, 20000); game.wait("xray.a > .95", 20000)
    x, y = game.pos()
    ground, away = f"{x} + 6 / 16, {y} - 2, {x} + 10 / 16, {y} - 1", f"{x} - 9, {y} - 6, {x} - 5, {y} + 5"   # the channel behind you, its middle (the walls beside it have their ledges over its sides); the land five tiles west
    seen, green, same = frames(game, f"""const A = shot('on'), Z = shot('off'), g = box(A, {ground}); let n = 0;
      for (let i = 0; i < g.length; i += 3) if (g[i + 1] > g[i] + 12) n++;
      return [differ(g, box(Z, {ground})) / (g.length / 3), n / (g.length / 3), differ(box(A, {away}), box(Z, {away}))];""")
    assert seen > .9 and green > .9 and same == 0, (seen, green, same)
    assert not game.errors


def test_the_cut_never_touches_ground_that_already_shows(game):
    """Behind a wall three layers high: its top covers you and half of the row behind you. Cut away, it shows what it
    covers; a pixel further back, where the ground shows anyway, is the same cut or not (it was cut
    out in whole tile columns with a margin: seams and dark lines in open ground and open water)."""
    game.clear_area(10)
    game.stamp(-3, 1, ["." * 7] * 2, levels=["3333333"] * 2)
    game.sleep(1200)
    x, y = game.pos()
    assert game.js("xray.a") > .95
    shows, covered = f"{x} - 3, {y} - 4, {x} + 4, {y} - 1 + 8 / 16", f"{x} - 1, {y} - 3 / 16, {x} + 2, {y} + 1"   # behind the wall's top edge (a block's top goes to its tile's edge: three layers, a tile and a half up); under it
    same, seen = frames(game, f"const A = shot('on'), B_ = shot('off'); return [box(A, {shows}).join() === box(B_, {shows}).join(), box(A, {covered}).join() !== box(B_, {covered}).join()];")
    assert same and seen
    assert not game.errors


def test_the_side_of_a_cliff_beside_open_water_is_not_seen_through(game):
    """Only rock in front of you is seen through, and only where it is drawn over something. A cliff's side sticks
    out a few px over the tile beside it: with the circle on, the water showed through that edge and its corners,
    though nothing hides that water."""
    game.clear_area(12)
    rows, lv = [], []
    for j in range(-4, 5):
        r, l = "", ""
        for i in range(-6, 7):
            front, side = 1 <= j <= 3 and -3 <= i <= 1, -3 <= j <= 0 and 3 <= i <= 4       # the plateau in front of you; a wall to the east
            r += "." if front or side else "~"; l += "6" if front or side else "0"
        rows.append(r); lv.append(l)
    game.stamp(-6, -4, rows, levels=lv)
    game.sleep(1500)
    x, y = game.pos()
    assert game.js("xray.a") > .95
    # the open water beside the wall, under its side, and the water under the plateau in front
    edge, under = f"{x} + 2 + 9 / 16, {y} - 2, {x} + 3, {y} + 1", f"{x} - 1, {y} + 1 / 16, {x}, {y} + 1"
    same, seen = frames(game, f"const A = shot('on'), B_ = shot('off'); return [box(A, {edge}).join() === box(B_, {edge}).join(), box(A, {under}).join() !== box(B_, {under}).join()];")
    assert same and seen
    assert not game.errors


def stamp_levels(game, f):
    """A 15x15 scene round you: f(i, j) -> the level of each tile, made and the rock that hides you cut away. (Land, not water: a
    scene of water left behind is in the next test's blocks.)"""
    game.clear_area(12)
    lv = [[f(i, j) for i in range(-7, 8)] for j in range(-7, 8)]
    game.stamp(-7, -7, ["." * 15] * 15, levels=["".join("0123456789"[v] for v in r) for r in lv])
    game.sleep(700); game.wait(BUILT, 20000); game.wait("xray.a > .95", 20000)
    return game.pos()


def test_the_place_you_are_in_shows_not_only_what_is_behind_you(game):
    """Along a bank that goes off in steps (a river's: the screenshot), the ground ahead is hidden by bank tiles on
    your own row and north of it. The circle saw through the rock south of your row only: it stopped dead at your feet
    and at your side, and showed nothing of where you were heading. The rock seen through is what stands on the line
    of sight to the place you are in (the ground you could walk to from where you stand): the bank beside you and in
    front of you are of it, the ground ahead shows, the meadow it is, and all of your own tile shows. (The bank is cut
    where it covers you and the tiles round you, not all of it: the rest of it stands a tile on, and its side leans
    over the ground ahead, a band a level: more than half of that tile is meadow, it was nine tenths.)"""
    for side in (1, -1):
        x, y = stamp_levels(game, lambda i, j: 6 if side * i + j >= 1 else 0)
        ahead = f"{x + side}, {y - 1}, {x + side + 1}, {y}"                       # the ground a step on, round the bank's corner
        mine = f"{x}, {y}, {x + 1}, {y + 1}"
        out = frames(game, f"""const A = shot('on'), Z = shot('off'), a = box(A, {ahead}); let n = 0;
          for (let i = 0; i < a.length; i += 3) if (a[i + 1] > a[i] + 12) n++;
          return [differ(a, box(Z, {ahead})) > 0, n / (a.length / 3) > .5, differ(box(A, {mine}), box(Z, {mine})) > 0, xrayRock({x + side}, {y}), xrayRock({x}, {y + 1})];""")
        assert out == [True, True, True, True, True], (side, out)
    game.clear_area(12)
    assert not game.errors


def test_a_rock_that_stands_apart_stays_whole(game):
    """Behind a wall, with a pillar standing in the meadow behind you: the pillar hides ground you could walk to, but
    it is not the rock that hides you. It stays, whole: it shows as the land has it with the wall in front
    taken away (cut out like the wall, its foot was a square of the wall's own top in the middle of the grass)."""
    game.js("setOpt('depth', false)")                         # (the land as it is painted: with its depth on, the sun's shadows are part of what is compared and counted here)
    game.clear_area(12)
    game.stamp(-5, 1, ["." * 11] * 3, levels=["6" * 11] * 3)
    game.stamp(1, -2, ["."], levels=["6"])
    game.sleep(700); game.wait(BUILT, 20000); game.wait("xray.a > .95", 20000)
    x, y = game.pos()
    area = f"{x} + 1, {y} - 3, {x} + 2 - 5 / 16, {y}"        # the pillar's column, under the wall's top (not its last px east: the wall is cut a tile each side of you, and the side of that cut stands there)
    on, off, rock = frames(game, f"return [box(shot('on'), {area}), box(shot('off'), {area}), [xrayRock({x + 1}, {y - 2}), xrayRock({x}, {y + 1})]];")
    assert on != off and rock == [False, True]
    game.stamp(-5, 1, ["." * 11] * 3, levels=["0" * 11] * 3)  # the wall in front, gone
    game.sleep(700); game.wait(BUILT, 20000)
    game.wait("xray.a === 0", 20000)
    gone = frames(game, f"return box(shot('off'), {area});")
    assert differ(on, gone) < .02, differ(on, gone)
    game.clear_area(12)
    assert not game.errors


def test_things_on_the_rock_in_front_of_you_fade_with_it(game):
    """What stands or lies on the rock the circle looks through would cover you again: a tree, a creature, and
    things lying there (a pile was still drawn, right over you)."""
    game.clear_area(10)
    game.give(wood=1)
    game.act("drop", item="wood")
    game.sleep(300)
    px, py = game.pos()
    game.rpc("dev_teleport", x=px, y=py - 1)                  # a tile north of the pile...
    game.sleep(700)
    x, y = game.pos()
    assert (x, y) == (px, py - 1)
    game.stamp(-3, 1, ["." * 7] * 3, levels=["6666666"] * 3)  # ...and the ground under it, and beside it, goes up six layers
    game.sleep(1300)
    assert game.js("xray.a") > .95 and game.js(f"groundItems.some(([ix, iy]) => ix === {px} && iy === {py})")
    assert game.js(f"xrayOver({px}, {py})") > .98             # on rock that is cut away: not drawn at all
    drawn = game.js(f"""(() => {{ const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0; let n = 0;
      const icon = ghostIcon('wood'), d = ctx.drawImage; ctx.drawImage = function (img, ...a) {{ if (img === icon) n++; return d.call(ctx, img, ...a); }};
      const T = performance.now(); frame(T); const on = n; n = 0;
      XRAY.from = 9; XRAY.full = 10; xray.a = 0; frame(T); const off = n;
      XRAY.from = .5; XRAY.full = .6; ctx.drawImage = d; window.requestAnimationFrame = raf; return [on, off]; }})()""")
    assert drawn == [0, 1], drawn                             # the rock cut away: gone; whole: there
    assert not game.errors


def test_creatures_behind_the_rock_are_seen_and_those_on_it_go_with_it(game):
    """A creature behind the rock with you showed whole in the middle of the circle and not at all a step further
    out; one on the rock was there, then gone. The rock in front is cut away a tile at a time: a creature behind it
    with you, on the ground of the place you are in, is drawn whole, once; one on the rock that is cut away is not
    drawn (it would stand in the air, over you)."""
    game.js("setOpt('depth', false)")                         # (the land as it is painted: with its depth on, the sun's shadows are part of what is compared and counted here)
    game.clear_area(10)
    game.stamp(-6, 1, ["." * 13] * 3, levels=["6" * 13] * 3)  # a wall in front of you, six layers
    behind, on_rock = game.spawn("cow", 1, 0, still=600), game.spawn("chicken", -1, 1, still=600)   # beside you; on the wall, where it is cut away (a tile each side of you: it was all of the wall)
    game.sleep(1500)
    assert game.js("xray.a") > .95
    assert game.js(f"[xrayShows(ents.get('cow{behind}')) > .95, xrayOverBody(ents.get('chicken{on_rock}')) > .95]") == [True, True]
    drawn = game.js("""(() => { const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
      const real = window.drawEntity, seen = {}; window.drawEntity = function (p, ...a) { (seen[p.e.id] = seen[p.e.id] || []).push(+ctx.globalAlpha.toFixed(2)); return real(p, ...a); };
      frame(performance.now()); window.drawEntity = real; window.requestAnimationFrame = raf; raf(frame); return seen; })()""")
    assert drawn[str(behind)] == [1] and str(on_rock) not in drawn, drawn
    assert drawn[str(game.js("myId"))] == [1], drawn          # you: whole, once
    assert not game.errors


def test_what_is_cut_away_is_found_again_only_when_you_change_tile(game):
    """The place you are in, the rock in the way and how low each tile is cut are kept (xray.js xrayFind): standing still nothing is worked out
    again; walking along behind a wall, once a tile."""
    game.clear_area(10)
    game.stamp(-7, 1, ["." * 15] * 3, levels=["6" * 15] * 3)
    game.sleep(1200)
    assert game.js("xray.a") > .95
    game.js("(() => { window.__found = []; let last = xray.pic; (function f() { if (xray.pic !== last) { last = xray.pic; window.__found.push(last && last.key); } requestAnimationFrame(f); })(); return 1; })()")
    game.sleep(800)
    assert game.js("__found") == []
    x, y = game.pos()
    game.hold(["d"], 700)                                     # east along the wall
    game.sleep(500)
    moved = game.pos()[0] - x
    assert moved >= 2 and game.js("xray.a") > .95
    found = game.js("__found")                                # what each was found for: your tile, your height, the land
    # (No more than tiles walked, and one; on a busy machine the server falls behind, your screen takes you a tile
    # back and on again, and that tile is found twice, rightly; and land that comes in beside you as you walk makes
    # the tile you are on be found again, rightly too. Three more than the tiles are let; every frame would be forty.)
    assert found and len(found) <= moved + 3, (found, moved)
    assert not game.errors
