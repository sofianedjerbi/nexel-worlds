"""Holes, overhangs and hills as they are seen, cut open or not (web/js/vox_mesh.js `slot`, `inward`; xray.js `seen`;
vox_engine.js): a hole reads as a hole, the ground goes in under an overhang, and the land is cut only for you.
(An audit of the landed game: "an 8-deep shaft looks 1 deep from outside and like a brown tower from inside, an
overhang is a black box, and hills you stand north of get flattened or boxed".)"""

from test_e2e_digging import DRAWN, LAND, SEEN, earth
from test_e2e_section import fill_px, under

mid = lambda px: sorted(px, key=sum)[len(px) // 2]              # (a face's body, whatever fleck one px of it is)


def test_a_shafts_far_wall_goes_down_into_the_dark_and_from_inside_you_stand_on_its_floor(game):
    """A shaft one tile wide, eight deep, and a pit one deep beside it. From the south, on the meadow: the two levels
    of its north wall the eye sees are darker than the pit's wall, the lower one darker again (it was two bands of
    the same earth, a crate one deep). From inside: the land south of you is cut for you, you and your floor are
    seen, the floor earth as any floor, the wall over you darker than at its top."""
    game.flat()                                                  # (it reads art px of walls up the picture)
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(0, -2, ["."], levels=["h"]); game.stamp(3, -2, ["."], levels=["a"])
    game.wait(DRAWN, 8000); game.sleep(600)
    assert game.js("xray.a") == 0
    wall = lambda tx, lv: mid(game.js(LAND, [[tx, y - 2, lv, ax, 2] for ax in (2, 5, 8, 11, 14)]))
    top, low, pit = wall(x, 0), wall(x, -1), wall(x + 3, 0)
    assert earth(pit) and sum(top) < sum(pit) - 25 and sum(low) < sum(top) - 25, (pit, top, low)
    under(game, x, y - 2, -8)
    assert game.js(f"[xrayShows(ents.get('agent' + myId)) > .95, xray.pic.cut.get('{x},{y - 1}'), xray.pic.cut.get('{x},{y}')]") == [True, -8, -6]
    floor = game.js(LAND, [[x, y - 2, -8, 8, 4]])[0]
    assert earth(floor), floor                                   # your floor, as light as any dug floor
    deep, high = wall(x, -6), wall(x, 0)
    assert sum(deep) < sum(high) - 60, (deep, high)              # the wall behind you: dark down here, earth at the mouth
    assert fill_px(game) == 0 and not game.errors


def test_the_ground_is_seen_going_in_under_an_overhang(game):
    """A slab of land four tiles by three with three levels of air under it, open all round. From the south: under it
    the meadow goes in, in shade, darker further in; not the black of a cave's mouth (it was one black box). A cave
    with one mouth keeps that black from its mouth on (test_e2e_caves.py)."""
    game.flat()
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-2, -5, ["...."] * 3, levels=["0000"] * 3, roofs=["4444"] * 3, heads=["3333"] * 3)
    game.wait(DRAWN, 8000); game.sleep(600)
    assert game.js("xray.a") == 0
    edge, inner, open_ = game.js(LAND, [[x - 2, y - 3, 0, 8, 13], [x - 1, y - 3, 0, 8, 13], [x - 4, y - 3, 0, 8, 13]])   # under its south row: its corner tile, the next one in; the meadow beside it
    for c in (edge, inner):
        assert c[1] > c[0] and sum(c) > 230, (edge, inner)       # the meadow's green, seen
    assert sum(edge) < sum(open_) - 40 and sum(inner) <= sum(edge), (open_, edge, inner)      # in shade; no lighter further in
    assert not game.errors


def test_a_hill_that_does_not_cover_you_is_not_touched_and_one_that_does_is_cut_round_you_alone(game):
    """A plateau three high, seven tiles wide. Standing three rows north of it (it covers nothing of you), every px
    of it is as it is from far away: no cut at all ("standing north of a hill wrecks it"). Right behind it: the cut
    is the tiles that cover you and the ones beside them, none further along the hill."""
    game.flat()
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-3, 3, ["." * 7] * 3, levels=["3" * 7] * 3)
    game.wait(DRAWN, 8000); game.sleep(900)
    spots = [[x + i, y + 3 + j, 3, ax, ay] for i in (-3, -1, 0, 2, 3) for j in (0, 1) for ax, ay in ((3, 3), (12, 9), (8, 15))]      # its top, to its north edge's lip
    near = game.js(LAND, spots)
    assert game.js("[xray.a, Voxels.engine.section.faces >= 0]") == [0, True]
    game.rpc("dev_teleport", x=x, y=y - 1)
    game.wait(f"myAt && myAt.y === {y - 1}", 8000); game.wait(DRAWN, 8000); game.sleep(900)
    assert game.js(LAND, spots) == near                          # the same hill, px for px
    game.rpc("dev_teleport", x=x, y=y + 2)                       # right behind it: it covers you
    game.wait(f"myAt && myAt.y === {y + 2}", 8000); game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    cols = game.js("[...xray.pic.cut.keys()].map((k) => +k.split(',')[0])")
    assert cols and all(abs(c - x) <= 1 for c in cols), (x, cols)
    far = game.js(LAND, [s for s in spots if abs(s[0] - x) >= 2])
    assert far == [c for s, c in zip(spots, near) if abs(s[0] - x) >= 2]      # two tiles along: as it was
    assert fill_px(game) == 0 and not game.errors


def test_a_cut_comes_a_whole_px_of_paint_at_a_time_never_in_stripes(game):
    """Half way in, the cut is a checker of px of paint (art px: zoom px of the screen), on the land's own grid: each
    px of paint is all the cut picture or all the whole one, and none stands alone in its row as a stripe thinner
    than itself ("thin vertical stripes thinner than an art pixel")."""
    game.flat()
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(-3, 1, ["." * 7] * 3, levels=["6" * 7] * 3)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    out = game.js("""(() => { const look = window.xrayLook, keep = {}; window.xrayLook = () => {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; } parts.length = puffs.length = 0; const k = zoom * DPR, n = 16, x0 = Math.floor(W / 2 * DPR / k) * k - 4 * k, y0 = Math.floor(H / 2 * DPR / k) * k - 9 * k;
      const shot = (a) => { xray.a = a; frame(performance.now()); return ctx.getImageData(x0, y0, n * k, n * k).data; };
      const whole = shot(0), half = shot(.5), open = shot(1); xray.a = 1; window.xrayLook = look; Object.assign(window, keep);
      const at = (d, i, j) => { const o = (j * n * k + i) * 4; return d[o] * 65536 + d[o + 1] * 256 + d[o + 2]; };
      let cells = 0, mixed = 0, odd = 0, cutCells = 0;
      for (let cj = 0; cj < n; cj++) for (let ci = 0; ci < n; ci++) {
        let w = 0, c = 0, differs = false;
        for (let j = 0; j < k; j++) for (let i = 0; i < k; i++) { const px = ci * k + i, py = cj * k + j, h = at(half, px, py); if (at(whole, px, py) !== at(open, px, py)) differs = true; if (h === at(whole, px, py)) w++; else if (h === at(open, px, py)) c++; else odd++; }
        if (!differs) continue;
        cells++; if (w && c && w !== k * k && c !== k * k) mixed++; if (c === k * k) cutCells++;
      }
      return [cells, mixed, odd, cutCells]; })()""")
    cells, mixed, odd, cut_cells = out
    assert cells > 60 and mixed == 0 and odd == 0, out           # every px of paint: one picture or the other, whole
    assert .3 < cut_cells / cells < .7, out                      # ...half of them each
    assert not game.errors


green = lambda c: c[1] > c[0] + 12                              # the meadow, a hill's grass


def test_a_plateau_that_covers_you_is_cut_over_your_own_column_and_what_the_knife_made_is_earth_not_grass(game):
    """Right behind a plateau three high ("the cut invents shapes": cut three tiles wide and to the ground, with a
    px of line at its edges, it read as an L-shaped hill). The cut is your own column, the rows of it that cover
    you; the block it slices has a top of earth, the dark of a wall, never the plateau's grass; and the plateau
    beside the cut ends in two px of that earth, then its grass as it was."""
    game.flat()
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-2, 1, ["." * 5] * 3, levels=["3" * 5] * 3)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js("[...xray.pic.cut].map(([k, v]) => k + ':' + v)") == [f"{x},{y + 1}:0", f"{x},{y + 2}:2"]
    cut_top, edge, grass = game.js(LAND, [[x, y + 2, 2, 8, 3], [x + 1, y + 1, 3, 0, 8], [x + 1, y + 1, 3, 8, 8]])
    assert not green(cut_top) and cut_top[0] > cut_top[1] + 25, cut_top      # the sliced block's top: earth
    assert not green(edge) and green(grass), (edge, grass)                # the cut's edge on the plateau beside it; and its grass
    assert sum(cut_top) < sum(grass) - 60, (cut_top, grass)               # ...dark: the ground's inside
    assert fill_px(game) == 0 and not game.errors


def test_no_stump_one_tile_wide_is_left_standing_alone_beside_a_cut(game):
    """A wall one row deep. Two tiles wide: cut over your column, the other tile would stand alone, a pillar that
    is not there: it goes with the cut. Five wide: the two tiles east of you are a piece of the wall, they stay;
    so does the one west, held by the tile beyond it."""
    game.clear_area(12)
    x, y = game.pos()
    game.stamp(0, 1, [".."], levels=["33"])
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert sorted(game.js("[...xray.pic.cut.keys()]")) == sorted([f"{x + 1},{y + 1}", f"{x},{y + 1}"])
    game.stamp(-2, 1, ["....."], levels=["33333"])
    game.wait(DRAWN, 8000); game.sleep(600); game.wait(SEEN, 20000)
    assert game.js("[...xray.pic.cut.keys()]") == [f"{x},{y + 1}"]
    assert fill_px(game) == 0 and not game.errors


def test_on_a_gorges_floor_you_are_in_a_hole_its_walls_go_down_darker_and_its_floor_is_not_the_plateaus(game):
    """A natural gorge, three rows of floor between two plateaus eight high ("the canyon floor has no depth... a rug
    on the plateau"). You are in it as in a hole that was dug: all of the floor round you is shown, not a tile of
    it; the far wall is seen down to its foot, darker there than the plateau's top and darker than at its own top;
    the floor is darker than the same meadow out in the open. An open meadow under one cliff is no gorge."""
    game.flat()
    game.clear_area(14)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(-7, -5, ["." * 15] * 11, levels=["8" * 15] * 4 + ["0" * 15] * 3 + ["8" * 15] * 4)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(400)
    assert game.js(f"[xrayGorge({x}, {y}, 0), xrayGorge({x}, {y + 9}, 0)]") == [True, False]
    cols = set(game.js("[...xray.pic.cut.keys()].map((k) => +k.split(',')[0])"))
    assert cols >= set(range(x - 3, x + 4)), cols                       # the place, not your column
    foot = mid(game.js(LAND, [[x + 1, y - 1, 0, ax, -4] for ax in (2, 5, 8, 11, 14)]))      # the far wall's lowest level, over the floor's far edge
    high = mid(game.js(LAND, [[x + 1, y - 1, 7, ax, -4] for ax in (2, 5, 8, 11, 14)]))      # ...and its highest but one
    top, floor, open_ = game.js(LAND, [[x + 6, y + 3, 8, 8, 8], [x + 2, y, 0, 8, 8], [x - 9, y, 0, 8, 8]])
    assert sum(foot) < sum(top) - 60 and sum(foot) < sum(high) - 25, (foot, high, top)
    assert green(open_) and sum(floor) < sum(open_) - 25, (floor, open_)
    assert fill_px(game) == 0 and not game.errors


def test_the_first_frame_of_a_cut_is_a_checker_of_whole_px_of_paint_in_the_roll_too(game):
    """A cut that opens came a px in four first: a lattice of dots, and, where the curved world squeezes the rows,
    thin stripes for a frame. Its first step is the checker: along every row of the screen, in the rolled picture,
    no run of the cut picture or of the whole one is narrower than a px of paint between two of the other."""
    game.clear_area(12)
    game.stamp(-3, 1, ["." * 7] * 4, levels=["6" * 7] * 4)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    out = game.js("""(() => { const look = window.xrayLook, keep = {}; window.xrayLook = () => {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; } parts.length = puffs.length = 0;
      const k = Math.round(zoom * DPR), w = 40 * k, h = Math.round(H * DPR * .6), x0 = Math.floor(W / 2 * DPR / k) * k - 20 * k;
      const shot = (a) => { xray.a = a; frame(performance.now()); return ctx.getImageData(x0, 0, w, h).data; };
      const whole = shot(0), first = shot(.25), open = shot(1); xray.a = 1; window.xrayLook = look; Object.assign(window, keep);
      const at = (d, i) => d[i * 4] * 65536 + d[i * 4 + 1] * 256 + d[i * 4 + 2];
      let thin = 0, cut = 0, kept = 0, odd = 0;
      for (let j = 0; j < h; j++) { let run = 0, cls = 0, before = 0;
        for (let i = 0; i <= w; i++) { const o = j * w + i, c = i === w || at(whole, o) === at(open, o) ? 0 : at(first, o) === at(open, o) ? 1 : at(first, o) === at(whole, o) ? 2 : 3;
          if (c === 3) odd++; if (c === 1) cut++; if (c === 2) kept++;
          if (c === cls) { run++; continue; }
          if (cls && before && c && run < k) thin++;      // (a run with the other picture on both its sides)
          before = cls; cls = c; run = 1; } }
      return [thin, cut, kept, odd, Curve.on]; })()""")
    thin, cut, kept, odd, rolled = out
    assert rolled and thin == 0 and odd == 0, out
    assert cut > 500 and .25 < cut / (cut + kept) < .75, out      # the checker: half of what changes, at once
    assert not game.errors
