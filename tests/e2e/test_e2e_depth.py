"""The land's depth (the settings' Picture page: Depth, on by default; vox_light.js `deep`, sunland.js): with no
shader, the sun's shadows on the land, shade at the foot of higher land, higher land a little lighter. Each on top of
the land's own paint: off, the picture is the one painted, to the px; open ground at level 0 is never changed."""
from test_e2e_sunland import RESET, twice

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


def test_stone_stays_stone_and_higher_land_is_only_a_little_lighter(game):
    game.clear_area(10)
    game.stamp(-2, 6, ["....."] * 5, levels=["66666"] * 5)      # a stone top six levels up (drawn three tiles up the picture)
    x, y = game.pos()
    game.rpc("dev_time", phase=.37); game.sleep(1200)
    on, off = game.js(RGB, [x - .5, y + 5 - .5, x + .5, y + 5 + .5])      # the middle of its top
    assert max(off) - min(off) < 30, off                        # (stone: grey)
    by = [a / b for a, b in zip(on, off)]
    assert all(1.0 < k < 1.1 for k in by) and max(by) / min(by) < 1.04, (on, off, by)      # a small step of light, its hue kept
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
