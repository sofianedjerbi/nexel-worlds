"""From high up, the distance is the land's and the sky's, never the backdrop's ("that blue mass behind... a weird
horizon glitch"): on a mountain top the sky's line was where ground at YOUR level would meet the sky past the bend;
the land round, lower, drops away past the bend lower on the screen, and between the two lay the backdrop
(hd_view.js show): the far land's flat colour, the sea's flat blue in whole columns, a 2 x 2 checker at their ends.
The sky's edge is now where the lowest land ahead meets the sky (hd.js eyeLine, lowAhead; the sky's own line stays the
eye's, its lowest colour going on down to the edge), and the far land the HD look draws is asked of the server too
(state.js: HdLook.far), not only the top-down screen's blocks."""

# below the sky's edge, on the world's canvas (art px): px of the backdrop's own two colours, 8 x 8 cells of one
# colour, and columns of a 2 x 2 checker (more than 16 px of one column)
LOOK = """() => { const el = HdView.el, c = document.createElement('canvas'); c.width = el.width; c.height = el.height; const g = c.getContext('2d'); g.drawImage(el, 0, 0);
  const W = el.width, H = el.height, d = g.getImageData(0, 0, W, H).data, px = (x, y) => { const i = (y * W + x) * 4; return d[i] << 16 | d[i + 1] << 8 | d[i + 2]; };
  const line = Math.max(0, Math.round(HdLook.sky(0).edge / zoom)), bk = new Set((HdView.backdrop || []).map((q) => q[0] << 16 | q[1] << 8 | q[2]));
  let back = 0, flat = 0, cells = 0; const checker = [];
  for (let y = line; y < H; y++) for (let x = 0; x < W; x++) if (bk.has(px(x, y))) back++;
  for (let y = line; y + 8 <= H; y += 8) for (let x = 0; x + 8 <= W; x += 8) { cells++; const v = px(x, y); let one = true; for (let j = 0; j < 8 && one; j++) for (let i = 0; i < 8; i++) if (px(x + i, y + j) !== v) { one = false; break; } if (one) flat++; }
  for (let x = 0; x + 3 < W; x++) { let n = 0; for (let y = line; y + 3 < H; y++) { const v = px(x, y);
    if (v === px(x + 2, y) && v === px(x, y + 2) && v === px(x + 1, y + 1) && v !== px(x + 1, y) && v !== px(x, y + 1) && px(x + 1, y) === px(x, y + 1)) n++; }
    if (n > 16) checker.push([x, n]); }
  return {line, back, flat, cells, checker: checker.slice(0, 6), H}; }"""


def test_from_a_peak_the_distance_is_land_and_sky_not_the_backdrop(game):
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    for dy in (-26, -20):                                # a lake north of you, 41 wide: where the backdrop laid the sea's flat blue, its columns' ends a checker
        game.stamp(-20, dy, ["~" * 41] * 6)
    game.rpc("dev_col", tiles=[[x + i, y + j] for j in (-1, 0, 1) for i in (-1, 0, 1)], col=[16])     # a peak 16 high under you, the meadow round
    game.rpc("dev_teleport", x=x, y=y)
    game.until(f"myAt && myAt.x === {x} && myAt.y === {y} && topAt({x}, {y}) === 16 && myAt.z === 16")
    game.until("HdLook.live && farLeft() === 0")         # (the far land's blocks come, four a tenth of a second, nearest first: all of them that will come, state.js farLeft)
    game.rest()                                          # (made, and the eye's level eased up to it)
    out = game.js(LOOK)
    assert out["line"] < out["H"], out                   # (the sky does not fill the picture)
    assert out["back"] < 200 and not out["checker"], out     # no flat backdrop, no checker strip
    assert out["flat"] < max(4, out["cells"] // 50), out   # no flat slab of the far land's colour
