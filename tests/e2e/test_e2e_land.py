"""Land coming in: a tile's paint (the HD look's tops: drawTile), a block's water made again only when it changed,
and land coming in at a sprint taking little of a frame."""

import pytest

COBBLES = ["..........", ".________.", ".___.._...", ".._..._...", ".._.._____", ".._......_", ".._......_", ".........."]
# every stone of the tiles from (x, y), w by h of them: the px of each (joined by a side), as [wide, high, how many]
STONES = """([x0, y0, w, h]) => { const W = w * 16, H = h * 16, px = new Uint32Array(W * H);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) drawTile(x0 + x, y0 + y, {px, o: y * 16 * W + x * 16, w: W});
  const d = new Uint8Array(px.buffer), grey = (i, r, gg, b) => d[i * 4] === r && d[i * 4 + 1] === gg && d[i * 4 + 2] === b;
  const stone = (i) => grey(i, 157, 168, 154) || grey(i, 129, 139, 131), seen = new Uint8Array(W * H), out = [];
  for (let i = 0; i < W * H; i++) { if (seen[i] || !stone(i)) continue;
    let n = 0, x1 = W, x2 = -1, y1 = H, y2 = -1; const q = [i]; seen[i] = 1;
    while (q.length) { const k = q.pop(), x = k % W, y = (k - x) / W; n++; x1 = Math.min(x1, x); x2 = Math.max(x2, x); y1 = Math.min(y1, y); y2 = Math.max(y2, y);
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const nx = x + dx, ny = y + dy, m = ny * W + nx; if (nx >= 0 && ny >= 0 && nx < W && ny < H && !seen[m] && stone(m)) { seen[m] = 1; q.push(m); } } }
    out.push([x2 - x1 + 1, y2 - y1 + 1, n]); }
  return out; }"""


def test_no_cobble_is_cut_at_a_tiles_edge(game):
    """Cobbled tiles were picked at random from a sheet that holds a strip, a square and a tile on its own: every
    tile cut its neighbour's stones at the edge. The stones are laid in rows over the tiles (web/js/pavement.js):
    on a path that runs, turns, forks and widens every stone is whole, one of the pack's (5 to 7 px wide, 5 or 6
    high, its four corners off), and every cobbled tile has some."""
    x, y = game.pos()
    game.stamp(2, -9, COBBLES, levels=["0" * 10] * 8); game.rest()
    stones = game.js(STONES, [x + 2, y - 9, 10, 8])
    cut = [s for s in stones if not (s[0] in (5, 6, 7) and s[1] in (5, 6) and s[2] == s[0] * s[1] - 4)]
    tiles = sum(row.count("_") for row in COBBLES)
    assert not cut and 3.2 * tiles <= len(stones) <= 4 * tiles, (cut, len(stones), tiles)          # (four to a tile, fewer at an end)
    game.stamp(2, -9, ["." * 10] * 8)


def test_a_blocks_water_is_made_again_only_when_it_changed(game):
    """Its bottom and its tint were made again whenever a tile of the block was drawn again, in the frame that showed it.
    (The pond, the tile it grows by and the cobbled tile are put inside one block: at fixed places they fell on two
    when the player woke near a block's edge, and the pond's block was then made again for a tile that is not its own.)"""
    x, y = game.pos()
    px, py = x + 3, y - 3
    px -= max(0, px % 32 + 3 - 32)
    py -= max(0, py % 32 + 3 - 32)
    cx = px - 6 if px % 32 >= 6 else px + 7                      # a cobbled tile, away from the water, in its block
    game.stamp(px - x, py - y, ["~~~", "~~~"]); game.rest()
    game.js(f"(() => {{ const b = tileIdx({px + 1}, {py})[0]; window.__b = b; window.__w = b.water; return b.water.any; }})()")
    assert game.js("__w.any") is True and game.js(f"tileIdx({cx}, {py})[0] === __b && tileIdx({px}, {py + 2})[0] === __b") is True
    built = "!dirtyTiles.length && Voxels.made(__b) && __b.seaAt === __b.ver"
    game.stamp(cx - x, py - y, ["_"])                            # its block is built again
    game.sleep(500); game.wait(built)
    assert game.js("__b.water === __w") is True
    game.stamp(px - x, py + 2 - y, ["~"])                        # the pond grows
    game.wait("__b.water !== __w", 8000); game.wait(built)
    assert game.js("__b.water !== __w && __b.water.any && __b.water.foam.length > __w.foam.length") is True


GLIDE = """() => new Promise((ok) => { follow = null; const out = [], of = window.__frame0 || (window.__frame0 = window.frame), x0 = cam.x, y0 = cam.y, t0 = performance.now(); let done = false;
  window.frame = function (now) { if (done) return of(now); const s = (performance.now() - t0) / 1000; cam.x = camT.x = x0 + 7 * s; cam.y = camT.y = y0 + 7 * s;
    let land = 0; const pf = window.perfFrame; window.perfFrame = (n, js, ms) => { land = ms; return pf(n, js, ms); };   // (the land's share of the frame, as render.js measures it for /perf)
    try { of(now); } finally { window.perfFrame = pf; }
    const [qx, qy, qw, qh] = viewRect(0); let miss = 0;
    for (const b of blocks.values()) if (!Voxels.made(b) && b.bx * B < qx + qw && (b.bx + 1) * B > qx && b.by * B < qy + qh && (b.by + 1) * B > qy) miss++;
    out.push([land, miss]); if (s > 6) { done = true; window.frame = of; ok(out); } }; })"""   # (the page's own frame kept once (__frame0), and a glide that is done only passes on: a second glide hung, its frame put away by the first one's, which a frame already asked for still ran)


@pytest.mark.realtime
def test_land_coming_in_at_a_sprint_takes_little_of_a_frame(browser, server):
    """Watching, the camera glides ten tiles a second into new land for six seconds: all the land is there when it
    comes on the screen, and building it never takes a frame (it took 9-13 ms of some on a fast machine, 36 ms on a
    phone-speed one: the only late frames there were). What is measured is the land's own share of each frame
    (render.js `landMs`, kept to LAND_MS): the whole frame is the machine's drawing too (13 to 97 ms on a runner's CPU
    renderer, 30 frames a second: what the land costs was not what was read)."""
    page = browser.new_page(viewport={"width": 844, "height": 390})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{server}/?zoom=2&follow=nobody")                 # (a link that follows someone: no first screen, the world's own land; no one by that name: the view stays at its middle)
    page.wait_for_function("typeof TitleScene !== 'undefined' && !TitleScene.on && blocks.size > 0 && !arrivingNow", timeout=20000)
    page.wait_for_timeout(1500)
    # (a frame's ms measure the machine as much as the code, README.md rule 6: with three browsers at work the 99th
    # frame in a hundred took 8.2 to 11 ms, one whole run in four. The best of three glides, each on into new land;
    # one is enough on a quiet machine)
    for _ in range(3):
        frames = page.evaluate(GLIDE)[5:]
        work = sorted(f[0] for f in frames)
        seen = (len(frames), sum(1 for f in frames if f[1]), work[-5:])
        if len(frames) > 60 and not seen[1] and work[int(len(work) * .99)] < 8 and work[-1] < 25:
            break
    page.close()
    assert len(frames) > 60 and not errors, seen
    assert sum(1 for f in frames if f[1]) == 0, seen             # nothing missing on the screen, in any frame
    assert work[int(len(work) * .99)] < 8 and work[-1] < 25, seen
