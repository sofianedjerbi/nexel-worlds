"""Land that is edited is shown as the same land made from nothing. A tile's look is by its neighbours (its cap's lip
and shape, a narrow top's small cap, the thin side of a wall where the land beside it is lower, the dark of a narrow
hole a few tiles on): when a tile changes, all that depends on it is made again (vox_engine.js touch), in whichever
block of land it is."""

import random

# what is drawn, with the clock held and no bodies; then everything made is let go of and made again, and the px that
# differ are counted: -> [how many, the box they are in]
DIFFER = """async () => {
  const grab = () => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
    clock = Object.assign({}, clock, {phase: .3, night: false}); frame(window.__held); Object.assign(window, keep); return ctx.getImageData(0, 0, cv.width, cv.height).data; };
  window.__held = window.__held || performance.now();
  // (the same land both times: a block of land that came from the server meanwhile changed the edges of those beside it: once more then)
  const land = () => blocks.size + ':' + [...blocks.values()].map((b) => b.ver).join(); let shown, again;
  for (let tries = 0, was = ''; tries < 5 && was !== land(); tries++) {
    // (...and not while something still moves on it: a tree the stamp took falls and fades for seconds, its leaves fly: waited for until two pictures a moment apart are one)
    const same = (a, b) => { for (let i = 0; i < a.length; i += 4) if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2]) return false; return true; };
    for (let k = 0, before = null; k < 60; k++) { shown = grab(); if (before && same(before, shown)) break; before = shown; for (let i = 0; i < 12; i++) await new Promise((ok) => requestAnimationFrame(ok)); }
    was = land(); Voxels.engine.forget(() => false);
    for (let i = 0; i < 600; i++) { await new Promise((ok) => requestAnimationFrame(ok)); if (i > 3 && dirtyTiles.length === 0 && !arrivingNow) break; }
    again = grab(); }
  let n = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
  for (let i = 0; i < shown.length; i += 4) if (shown[i] !== again[i] || shown[i + 1] !== again[i + 1] || shown[i + 2] !== again[i + 2]) { n++; const p = i / 4, x = p % cv.width, y = p / cv.width | 0; x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  return [n, x0, y0, x1, y1]; }"""
LEVELS = "ba0123456"                                         # (a stamp's heights: -2 to 6)


def test_land_edited_is_shown_as_the_same_land_made_from_nothing(game):
    """A hill, a pillar one tile wide, a stair and a pond; then ten edits, the same each run: a tile dug, raised,
    lowered by two, earth put beside a wall, a tile at the edge of a block of land, a pillar raised, water. After
    each, not a px of what is shown differs from the same world made from nothing."""
    game.flat()                                              # (px are compared: the flat picture, whole art px)
    x, y = game.pos()
    game.stamp(-6, -4, ["...."] * 3, levels=["3333"] * 3)
    game.stamp(2, -3, ["."], levels=["3"])
    game.stamp(-3, 2, ["...."], levels=["1234"])
    game.stamp(3, 1, ["~~~"] * 2)
    game.settle("!arrivingNow")
    assert game.js(DIFFER)[0] == 0                           # (nothing edited: the picture is the same twice)
    rng, side = random.Random(5), game.js("B")
    for k, kind in enumerate(["dig", "raise", "lower", "beside", "edge", "pillar", "water", "dig", "raise", "edge"]):
        dx, dy = rng.randint(-6, 6), rng.randint(-4, 4)
        if kind == "edge": dx = ((side - x % side) if x % side > side // 2 else -(x % side)) - rng.randint(0, 1)      # the nearest edge of a block of land, one side of it or the other
        if kind == "pillar": dx, dy = 2, -3
        if (dx, dy) == (0, 0): dy = 1
        lv = game.js(f"levelAt({x + dx}, {y + dy})")
        new = max(-2, min(6, {"dig": lv - 1, "raise": lv + 1, "lower": lv - 2, "beside": lv + 2, "edge": lv + rng.choice([-1, 1, 2]), "pillar": lv + 1, "water": 0}[kind]))
        game.stamp(dx, dy, ["~" if kind == "water" else "."], levels=[LEVELS[new + 2]])
        game.wait("dirtyTiles.length === 0")
        d = game.js(DIFFER)
        assert d[0] == 0, (k, kind, (dx, dy), lv, new, d)
