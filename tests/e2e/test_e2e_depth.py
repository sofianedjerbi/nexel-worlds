"""The land's depth (the settings' Picture page: Depth, on by default; vox_light.js `deep`, sunland.js): with no
shader, the sun's shadows on the land, shade at the foot of higher land, higher land a little lighter. Each on top of
the land's own paint: off, the picture is the one painted, to the px; open ground at level 0 is never changed."""
from test_e2e_digging import DRAWN, LAND, earth
from test_e2e_sunland import RESET, look, twice

# one frame drawn three times: with the depth off, with all of the sun's code out of the frame, with the depth on -> a hash of every px of each
HASHES = """() => new Promise((ok) => requestAnimationFrame((T) => {
  const raf = window.requestAnimationFrame, was = opt('depth'), keep = {cast: Sun.cast, shade: Sun.shade, draw: Sun.draw}; window.requestAnimationFrame = () => 0;
  const px = () => { const d = ctx.getImageData(0, 0, cv.width, cv.height).data; let h = 0; for (let i = 0; i < d.length; i++) h = (Math.imul(h, 31) + d[i]) | 0; return h; };
  const out = {};
  try { setOpt('depth', false); frame(T); out.off = px(); Sun.cast = () => null; Sun.shade = () => {}; Sun.draw = () => {}; frame(T); out.none = px(); Object.assign(Sun, keep); setOpt('depth', true); frame(T); out.on = px(); }
  finally { Object.assign(Sun, keep); setOpt('depth', was); window.requestAnimationFrame = raf; raf(frame); }
  ok(out); }))"""
# the mean colour [r, g, b] of a part of the flat ground [x0, y0, x1, y1] (tiles), the same frame drawn with the depth on and off
RGB = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame((T) => {
  const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
  const S = TS(), [ox, oy] = screenOrigin(S), out = [];
  const rgb = () => { const d = ctx.getImageData(Math.round((ox + x0 * S) * DPR), Math.round((oy + y0 * S) * DPR), Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)).data, s = [0, 0, 0];
    for (let i = 0; i < d.length; i += 4) for (let j = 0; j < 3; j++) s[j] += d[i + j]; return s.map((v) => v / d.length * 4); };
  try { setOpt('depth', true); frame(T); out.push(rgb()); setOpt('depth', false); frame(T); out.push(rgb()); } finally { setOpt('depth', true); window.requestAnimationFrame = raf; raf(frame); }
  ok(out); }))"""


def test_with_the_depth_off_the_picture_is_the_one_painted_to_the_px(game):
    game.clear_area(8)
    game.stamp(-5, -4, ["...", "..."], levels=["333", "333"]); game.stamp(2, -3, ["T"]); game.stamp(-4, 2, [".."], levels=["11"])
    x, y = game.pos()
    game.rpc("dev_time", phase=.1); game.sleep(1200)
    for spot in ((x, y), (x + 9, y + 4)):
        game.rpc("dev_teleport", x=spot[0], y=spot[1], z=0); game.wait(f"myAt && myAt.x === {spot[0]} && myAt.y === {spot[1]}", 8000)
        game.wait("dirtyTiles.length === 0", 20000); game.sleep(900)
        h = game.js(HASHES)
        assert h["off"] == h["none"], h                         # off: as with no sun at all in the frame
        assert h["on"] != h["off"], h                           # (and on, it is there)
    game.js(RESET)


def test_a_blocks_foot_is_darker_than_open_ground_which_is_as_it_is_painted(game):
    game.clear_area(8)
    game.stamp(-1, 2, ["..."], levels=["111"])                  # a block one level high, south of you (where the picture is flat)
    x, y = game.pos()
    game.rpc("dev_time", phase=.3); game.sleep(1200)
    assert game.js("[opt('shader'), opt('depth'), Sun.shades()]") == ["off", True, True]
    foot, open_, mine = twice(game, [[x - .6, y + 3 - 2 / 16, x + .6, y + 3 + 1 / 16], [x + 4, y + 2, x + 6, y + 4], [x + 1.2, y - .4, x + 2.2, y + .6]], "depth", False)
    assert foot[0] < foot[1] - 8, foot                          # the ground at its foot: shaded
    assert open_[0] == open_[1] and mine[0] == mine[1], (open_, mine)      # open ground, at your own level: the colours it is painted in
    game.js(RESET)


# the middle tone (the median px's light) of each part [x0, y0, x1, y1] (tiles of the flat picture) of one frame
MID = """(boxes) => new Promise((ok) => requestAnimationFrame((T) => {
  const S = TS(), [ox, oy] = screenOrigin(S);
  ok(boxes.map(([x0, y0, x1, y1]) => { const d = ctx.getImageData(Math.round((ox + x0 * S) * DPR), Math.round((oy + y0 * S) * DPR), Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)).data, l = [];
    for (let i = 0; i < d.length; i += 4) l.push(.299 * d[i] + .587 * d[i + 1] + .114 * d[i + 2]); l.sort((a, b) => a - b); return l[l.length >> 1]; })); }))"""


def test_stone_stays_stone_and_each_terrace_of_it_is_a_clear_step_lighter(game):
    """Seen from where no wall of it faces you a stone mountain was beige sheets: its tops tell the height. Each level's
    top is a clear step lighter than the one under it (in its paint: tiles.js hillSheet; the depth adds none to stone)."""
    game.clear_area(12)
    game.stamp(-6, 6, ["............"] * 4, levels=["666677778888"] * 4)      # three stone terraces side by side, south of you
    x, y = game.pos()
    game.rpc("dev_time", phase=.375); game.sleep(1200)
    on, off = game.js(RGB, [x - 5, y + 7 - 3, x - 3, y + 9 - 3])      # the middle of the lowest one's top (six levels: drawn three tiles up)
    assert max(off) - min(off) < 30, off                        # (stone: grey)
    assert all(abs(a - b) < .01 for a, b in zip(on, off)), (on, off)      # the depth: no light of its own on stone (it went to white)
    low, mid, high = game.js(MID, [[x - 5, y + 7 - 3, x - 3, y + 9 - 3], [x - 1, y + 7 - 3.5, x + 1, y + 9 - 3.5], [x + 3, y + 7 - 4, x + 5, y + 9 - 4]])
    assert mid >= low * 1.025 and high >= mid * 1.025, (low, mid, high)      # a step a level (2.5 %: with 4 % the lowest stone top was the wall's grey, tiles.js ROCK_TONE; the edge is told by the rim line and the foot band too)
    assert high < 200, high                                      # (and never lighter than the stone sheet's own top)
    game.js(RESET)


# the mean colour [r, g, b] of a part [x0, y0, x1, y1] (tiles of the flat picture) of the land's own picture (the engine's: no light of the hour on it)
LAND_RGB = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame((T) => {
  const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
  try { frame(T); const S = TS(), [ox, oy] = screenOrigin(S), c = document.createElement("canvas"); c.width = cv.width; c.height = cv.height; const g = c.getContext("2d"); g.drawImage(VoxGL.el, 0, 0);
    const d = g.getImageData(Math.round((ox + x0 * S) * DPR), Math.round((oy + y0 * S) * DPR), Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)).data, s = [0, 0, 0];
    for (let i = 0; i < d.length; i += 4) for (let j = 0; j < 3; j++) s[j] += d[i + j]; ok(s.map((v) => v / d.length * 4)); }
  finally { window.requestAnimationFrame = raf; raf(frame); } }))"""


def test_a_front_has_one_tone_at_every_hour_whatever_stands_beside_it(game):
    """The sun is never south: a south face is never in the sun, and takes no shadow, the land's or a cloud's. (Laid on
    a front four ways, a shadow drew triangles, split columns, wedges and lighter rectangles on a cliff.)"""
    game.clear_area(10)
    game.stamp(-1, 2, ["..", ".."], levels=["33", "33"])        # a block three high south of you (where the picture is flat),
    game.stamp(-3, 2, ["."] * 3, levels=["6"] * 3); game.stamp(2, 2, ["."] * 3, levels=["6"] * 3)      # a pillar twice as high a tile west and east of it
    x, y = game.pos()
    front, gap = [x - .8, y + 4 - 1.2, x + .8, y + 4 - .3], [x - 2 + .3, y + 3 + .3, x - 2 + .7, y + 3 + .8]
    look(game, "natural"); game.js("setOpt('clouds', 100)")
    tones = []
    for phase in (.1, .3, .5, .65):
        game.rpc("dev_time", phase=phase); game.sleep(900)
        tones.append(game.js(LAND_RGB, front))
    assert all(max(t[j] for t in tones) - min(t[j] for t in tones) <= 1 for j in range(3)), tones
    game.js("setOpt('clouds', 0)"); game.rpc("dev_time", phase=.1); game.sleep(900)
    ground, = twice(game, [gap], "shadows", 0)
    assert ground[0] < ground[1] - 4, ground                     # (and the pillars do throw a shadow: on the ground between)
    game.js(RESET)


def test_the_ground_behind_a_step_is_darker_along_it(game):
    """A terrace seen from behind (its wall faces away) had nothing to tell it by: the lower ground north of it is
    shaded for a few px along the step's far edge."""
    game.clear_area(8)
    game.stamp(-2, 3, ["....."] * 2, levels=["11111"] * 2)      # a step one level high, south of you: you look at its back
    x, y = game.pos()
    game.rpc("dev_time", phase=.375); game.sleep(1200)
    band, north = twice(game, [[x - 1, y + 2 + 7 / 16, x + 1, y + 2 + 11 / 16], [x - 1, y + 2, x + 1, y + 2 + 5 / 16]], "depth", False)
    assert band[0] < band[1] - 8, band                          # the last px of the ground before the step's top hides it
    assert north[0] == north[1], north                          # and no further
    game.js(RESET)


def test_the_depth_costs_little_of_a_frame(game):
    game.clear_area(8)
    game.stamp(-6, -5, ["......", "......", "~~~~~~"], levels=["332211", "332211", "000000"]); game.stamp(2, -3, ["T.T", "...", "T.T"])
    game.rpc("dev_time", phase=.08); game.sleep(1000)
    assert game.js("opt('depth') && opt('shader') === 'off'")
    ms = game.js("new Promise((ok) => { const out = [], of = window.frame; window.frame = (now) => { const a = performance.now(); of(now); out.push(performance.now() - a); if (out.length >= 90) { window.frame = of; ok(out); } }; })")
    ms.sort()
    assert ms[len(ms) // 2] < 7 and ms[int(len(ms) * .95)] < 14, ms[-5:]      # (the bar of the shader's sun: test_e2e_sunland.py)
    game.js(RESET)


# each device row of a part of the flat ground [x0, y0, x1, y1] (tiles): its px as the sum of red, green and blue, read in the frame it was drawn in
ROWS = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
  const S = TS(), [ox, oy] = screenOrigin(S), w = Math.round((x1 - x0) * S * DPR), h = Math.round((y1 - y0) * S * DPR);
  const d = cv.getContext("2d").getImageData(Math.round((ox + x0 * S) * DPR), Math.round((oy + y0 * S) * DPR), w, h).data, out = [];
  for (let r = 0; r < h; r++) { const row = []; for (let i = 0; i < w; i++) { const k = (r * w + i) * 4; row.push(d[k] + d[k + 1] + d[k + 2]); } out.push(row); }
  ok(out); })))"""


def test_a_step_of_one_level_throws_a_shadow_all_along_it_away_from_the_sun(game):
    """A terrace is a step: the ground under a riser one level high is in its shadow on the side away from the sun, in
    every row of the riser's length (no gaps: it was dashes, then nothing), and not on the sun's side."""
    game.flat(); game.clear_area(9)
    game.stamp(-1, -5, ["..."] * 4, levels=["111"] * 4)         # a terrace one level up, north of you: its risers run north-south
    x, y = game.pos()
    east, west = [x + 2 + 3 / 16, y - 4.5, x + 2 + 8 / 16, y - 2.5], [x - 1 - 8 / 16, y - 4.5, x - 1 - 3 / 16, y - 2.5]
    for phase, far, near in ((.68, east, west), (.06, west, east)):      # evening: the sun in the west; morning: in the east
        game.rpc("dev_time", phase=phase); game.sleep(1200)
        on = [game.js(ROWS, r) for r in (far, near)]
        game.js("setOpt('landshade', false)"); game.sleep(600)
        off = [game.js(ROWS, r) for r in (far, near)]
        game.js("setOpt('landshade', true)")
        gaps = [i for i, (a, b) in enumerate(zip(on[0], off[0])) if min(p - q for p, q in zip(a, b)) > -30]
        assert not gaps, (phase, gaps[:8], len(on[0]))           # away from the sun: shadow px in every row along the riser
        lit = max(abs(p - q) for a, b in zip(on[1], off[1]) for p, q in zip(a, b))
        assert lit < 3, (phase, lit)                             # the sun's side: none
    game.js(RESET)


def test_an_inner_corner_is_no_darker_than_one_walls_shadow(game):
    """Two walls' shadows that meet in a corner are one shadow: no px there is darker than a px in the shadow of one wall
    alone (dark squares sat in the inner corners of terraces)."""
    game.flat(); game.clear_area(9)
    game.stamp(-2, -5, ["...."] * 4, levels=["1111", "0001", "0001", "0001"])      # a step along the north and the east: the corner is inside, north-east
    x, y = game.pos()
    game.rpc("dev_time", phase=.06); game.sleep(1200)           # morning: both throw their shadow into it
    corner, one = [x + .4, y - 4 + 2 / 16, x + 1 - 3 / 16, y - 4 + 8 / 16], [x + .4, y - 2.6, x + 1 - 3 / 16, y - 2.1]
    on = [game.js(ROWS, r) for r in (corner, one)]
    game.js("setOpt('depth', false)"); game.sleep(600)
    plain = [game.js(ROWS, r) for r in (corner, one)]
    by = [[p / max(q, 1) for a, b in zip(o, pl) for p, q in zip(a, b)] for o, pl in zip(on, plain)]
    assert min(by[1]) < .9, min(by[1])                           # (one wall's shadow is there)
    assert min(by[0]) > min(by[1]) - .03, (min(by[0]), min(by[1]))
    game.js(RESET)


def test_a_body_in_a_trees_shadow_is_darker_than_beside_it(game):
    """What stands in the shadow of what stands is in it (only the land's shadow darkened a body)."""
    from test_e2e_sunland import LIT
    game.flat(); game.clear_area(8)
    x, y = game.pos()
    game.rpc("dev_time", phase=.1); game.sleep(1200)           # morning: a tree's shadow lies long to the west, a little south
    me = [x + .3, y - .2, x + .7, y + .3]
    beside = game.js(LIT, me)
    game.stamp(2, -1, ["T"]); game.sleep(700)                   # a tree north-east of you: you stand in its shadow
    under = game.js(LIT, me)
    assert under < beside - 10, (beside, under)
    game.js(RESET)


def test_a_straight_walls_shadow_has_a_straight_edge(game):
    """Along a straight wall the shadow's outer edge is as far from the wall in every row: no notch at each tile's joint
    ("shadow has weird dents")."""
    game.flat(); game.clear_area(9)
    game.stamp(3, -5, ["."] * 6, levels=["3"] * 6)              # a wall six tiles long, north-south, east of you
    x, y = game.pos()
    part = [x + 1, y - 3.5, x + 3, y - 0.5]                      # the ground west of it, clear of its two ends
    for phase in (.1, .2, .3):
        game.rpc("dev_time", phase=phase); game.sleep(1200)    # morning: its shadow lies west
        on = game.js(ROWS, part)
        game.js("setOpt('landshade', false)"); game.sleep(600)
        off = game.js(ROWS, part)
        game.js("setOpt('landshade', true)")
        edge = [next((i for i, (p, q) in enumerate(zip(a, b)) if p - q < -30), None) for a, b in zip(on, off)]
        assert None not in edge and max(edge) - min(edge) <= 1, (phase, sorted(set(edge)))
    game.js(RESET)


def test_a_cliff_that_runs_on_a_slant_is_one_rock_face(game):
    """A stone cliff eight levels high whose edge goes a tile south for every tile east ("this wall look so weird": a
    grid of grey squares, stone over orange earth in a staircase). Each of its columns is drawn a tile, two levels,
    lower than the one west of it: side by side on one row of the screen are a level of one and the level two higher
    of the next. They are one colour (a wall has its rock's one tone: no step of light a level, not in the paint, not
    in the depth), and a block whose top is stone is stone at its foot. An earth block beside it is earth."""
    game.flat()                                                  # (it reads art px of fronts by where the flat picture has them)
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.375)                             # (noon: no shadow of one column on the next)
    game.stamp(2, 2, ["." * 6] * 6, levels=["".join("8" if j <= i else "0" for i in range(6)) for j in range(6)])
    game.stamp(-6, 3, ["..."] * 2, levels=["333"] * 2)
    game.wait(DRAWN, 8000); game.sleep(900)
    mid = lambda px: sorted(px, key=sum)[len(px) // 2]           # (a face's body, whatever fleck one px of it is)
    wall = lambda i, lv: mid(game.js(LAND, [[x + 2 + i, y + 3 + i, lv, ax, 3] for ax in (4, 6, 8, 10, 12)]))      # column i's front, its level lv
    for i in (1, 2, 3):
        for lv in (1, 2, 4, 6):
            a, b = wall(i, lv), wall(i + 1, lv + 2)              # the same row of the screen, two columns
            assert a == b, (i, lv, a, b)
    foot, high = wall(2, 1), wall(2, 8)
    assert foot == high and max(foot) - min(foot) < 30 and not earth(foot), (foot, high)      # stone down to the ground, one tone
    low = mid(game.js(LAND, [[x - 5, y + 5, 1, ax, 3] for ax in (4, 6, 8, 10, 12)]))
    assert earth(low), low                                       # (a block whose top is grass: earth)
    game.js(RESET)


def test_a_stone_top_is_far_lighter_than_its_wall_at_every_level_and_its_foot_band_is_between(game):
    """ "Low stone tops are nearly the wall's grey: the terraces read as one murky mass": terraces of stone from level 5 to
    12 rising north. At every level the top is 12 % lighter or more than the front under it (a wall is the shaded face,
    one tone: tiles.js ROCK_TONE), a step lighter than the terrace under it, never lighter than the sheet's own; and the
    band of shade at a wall's foot is darker than the top it lies on and lighter than the wall."""
    game.flat()                                                  # (it reads rows of art px by where the flat picture has them)
    game.clear_area(14)
    x, y = game.pos()
    game.rpc("dev_time", phase=.375)
    assert game.js("[opt('shader'), opt('depth')]") == ["off", True]
    tops, fronts, bands = [], [], []
    for L0 in (5, 9):                                            # (four at a time: the view is eleven tiles high)
        game.stamp(-9, 2, ["." * 7] * 4, levels=[str("0123456789ABC"[L0 + 3 - j]) * 7 for j in range(4)])      # (west of you: land that hides you is cut open)
        game.wait(DRAWN, 8000); game.sleep(1200)
        rows = []
        for i in range(4):
            r0 = y + 5 - i - (L0 + i) / 2                          # (its row on the flat picture: a level is half a tile up)
            rows += [[x - 8, r0 + .3, x - 4, r0 + .6], [x - 8, r0 + 1.12, x - 4, r0 + 1.3], [x - 8, r0 + .01, x - 4, r0 + .17]]      # its top's middle, its front's body, the band at the foot of the wall north of it
        got = game.js(MID, rows); tops += got[0::3]; fronts += got[1::3]; bands += got[2::3]
    for i in range(8):
        assert tops[i] * .88 >= fronts[i], (5 + i, tops[i], fronts[i])
        if i: assert tops[i] >= tops[i - 1] * 1.02, (5 + i, tops)
        if i % 4 < 3: assert fronts[i] + 3 < bands[i] < tops[i] - 6, (5 + i, fronts[i], bands[i], tops[i])
    assert tops[-1] < 200 and max(fronts) - min(fronts) < 1.5, (tops, fronts)      # (the sheet's own tone at the top; a wall: one tone at every level)
    print("stone luminance, levels 5..12: tops", [round(v, 1) for v in tops], "fronts", [round(v, 1) for v in fronts], "bands", [round(v, 1) for v in bands])
    game.js(RESET)
