"""Land coming in: only what shows is painted, a little a frame, in the page, and it is the same land to the pixel;
its blocks (voxels.js, vox_engine.js) are made a few tiles at a time."""

import pytest

LV = "0123456789ABC"
# a mountain of terraces twelve layers high, 13 tiles across
MOUNTAIN = ["".join(LV[max(0, 12 - 2 * max(abs(dx), abs(dy)))] for dx in range(-6, 7)) for dy in range(-6, 7)]

# every block's ground, its px painted again from nothing: a hash of each, and how many cells were laid for it
SIG = """() => { const hash = (px) => { let a = 2166136261; for (let i = 0; i < px.length; i++) a = Math.imul(a ^ px[i], 16777619); return a >>> 0; };
  return [...blocks.values()].filter((b) => b.px).sort((p, q) => p.by - q.by || p.bx - q.bx).map((b) => {
    let n = 0; const o = window.layCell; window.layCell = function (...a) { n++; return o(...a); };
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly);
    window.layCell = o; return {key: hash(b.px), n}; }); }"""


def test_only_what_shows_is_painted_and_the_land_is_the_same(game):
    """A tile is painted from its last solid layer (tiles.js). The px are the same as with every layer laid (nothing
    taken for solid); a block cost 42 ms to build at the foot of a twelve-layer mountain, on a fast machine."""
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN)
    pond(game)                                                   # a pond, and a pit under it
    game.sleep(900)
    quick = game.js(SIG)
    game.js("(() => { window.__solid = cellSolid; window.cellSolid = () => false; return 1; })()")
    whole = game.js(SIG)
    game.js("(() => { window.cellSolid = window.__solid; return 1; })()")
    assert [b["key"] for b in quick] == [b["key"] for b in whole] and len(quick) >= 2
    assert sum(b["n"] for b in quick) * 5 < sum(b["n"] for b in whole) * 3    # (about half the paint on a meadow, a tenth on the mountain)
    assert game.js(SIG) == quick                                              # ...and drawn again, the same


# each block's px against its tiles laid on a canvas (diff: px that are not the same; near: the same but for a shade),
# and what making its blocks again from nothing draws on a canvas or puts on one
PAGE = """() => { const P = CanvasRenderingContext2D.prototype, od = P.drawImage, op = P.putImageData, out = [], E = Voxels.engine;
  for (const b of blocks.values()) { if (!b.px || !Voxels.made(b)) continue;
    const c = document.createElement('canvas'); c.width = c.height = BW; const g = c.getContext('2d', {willReadFrequently: true});
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly, {g, ox: lx * 16, oy: ly * 16});
    const d = new Uint8Array(g.getImageData(0, 0, BW, BW).data.buffer), p = new Uint8Array(b.px.buffer); let diff = 0, near = 0, draws = 0, puts = 0, top = -99;
    for (let i = 0; i < d.length; i += 4) { const solid = d[i + 3] === 255 && p[i + 3] === 255, by = Math.max(Math.abs(d[i] - p[i]), Math.abs(d[i + 1] - p[i + 1]), Math.abs(d[i + 2] - p[i + 2]));
      if (solid ? by > 1 : Math.abs(d[i + 3] - p[i + 3]) > 1) diff++; else if (by) near++; }
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) top = Math.max(top, topAt(b.bx * B + lx, b.by * B + ly));
    const faces = E.faces;
    P.drawImage = function (...a) { draws++; return od.apply(this, a); }; P.putImageData = function (...a) { puts++; return op.apply(this, a); };
    E.forget((cx, cy) => cx !== b.bx || cy !== b.by); E.work([{cx: b.bx, cy: b.by}], performance.now() + 60000); P.drawImage = od; P.putImageData = op;
    out.push({diff, near, draws, puts, top, made: E.made(b.bx, b.by), same: E.faces === faces, water: b.water.any}); }
  return out; }"""


def pond(game):
    """A pond and a pit under it, up and to the left of you, wholly inside one block. (Stamped at a fixed place it fell
    across a corner of four blocks when the player woke near one: every block had water, and a test that needs one
    without failed; which player wakes where changes whenever a test is added.)"""
    x, y = game.pos()
    px, py = x - 9, y - 4
    px -= max(0, px % 32 + 6 - 32)
    py -= max(0, py % 32 + 3 - 32)
    game.stamp(px - x, py - y, ["..~~..", ".~~~~.", "..~~.."], levels=["000000", "0aaaa0", "000000"])


def test_the_land_is_painted_in_the_page_and_handed_to_the_gpu_whole(game):
    """A block's ground is px worked out in the page (tiles.js), and its blocks' tops and fronts are made from such
    px and handed to the GPU as they are (voxels.js, vox_pages.js). Put together by the GPU a piece at a time (a
    mask, the ground drawn into it, a few rows put and a few rows drawn, on canvases used again for the next
    level), a phone showed the mask itself on cliff tops: black tiles, which no desktop drew. The px are the tiles
    as a canvas lays them (a sheet's see-through shadow rounds a step differently here and there, as it does from
    one canvas to another); and making a block of land draws on no canvas and puts nothing on one."""
    game.stamp(-48, -48, ["." * 97] * 97)                    # (every block in view a plain meadow first: a stair another test
    game.wait("dirtyTiles.length === 0", 30000)              #  left open nearby has the foot of the tile behind it in the block's px only: 194 px "differ")
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN)
    pond(game)
    game.sleep(900)
    blocks = game.js(PAGE)
    assert len(blocks) >= 2 and max(b["top"] for b in blocks) >= 12
    assert all(b["diff"] == 0 and b["near"] < 2000 for b in blocks), blocks
    assert all(b["made"] and b["same"] and b["draws"] == 0 and b["puts"] == 0 for b in blocks), blocks


COBBLES = ["..........", ".________.", ".___.._...", ".._..._...", ".._.._____", ".._......_", ".._......_", ".........."]
# every stone of the tiles from (x, y), w by h of them: the px of each (joined by a side), as [wide, high, how many]
STONES = """([x0, y0, w, h]) => { const c = document.createElement('canvas'); c.width = w * 16; c.height = h * 16; const g = c.getContext('2d', {willReadFrequently: true});
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) drawTile(x0 + x, y0 + y, {g, ox: x * 16, oy: y * 16});
  const d = g.getImageData(0, 0, c.width, c.height).data, W = c.width, H = c.height, grey = (i, r, gg, b) => d[i * 4] === r && d[i * 4 + 1] === gg && d[i * 4 + 2] === b;
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


@pytest.mark.realtime
def test_a_block_of_land_is_made_in_small_steps(game):
    """No step of making a block of land is long (they were up to 10 ms each on a fast machine: a late frame on a slow
    one): its tiles are painted a few at a time, as much as the frame has time for (vox_engine.js work)."""
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN); game.rest()
    worst = game.js("""(() => { const E = Voxels.engine; let worst = 0, steps = 0;
      for (const b of blocks.values()) { if (!b.px || !Voxels.made(b)) continue;
        for (let r = 0; r < 3; r++) { let w = 0, n = 0; E.forget((cx, cy) => cx !== b.bx || cy !== b.by);
          while (!E.made(b.bx, b.by) && n < 5000) { const t0 = performance.now(); E.work([{cx: b.bx, cy: b.by}], 0); w = Math.max(w, performance.now() - t0); n++; }
          if (!r || w < worst) worst = w; steps = Math.max(steps, n); } }
      return [worst, steps]; })()""")
    assert worst[0] < 5 and 40 < worst[1] < 5000, worst          # (a block: over forty steps, none long)


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


GLIDE = """() => new Promise((ok) => { follow = null; const out = [], of = window.frame, x0 = cam.x, y0 = cam.y, t0 = performance.now();
  window.frame = function (now) { const s = (performance.now() - t0) / 1000; cam.x = camT.x = x0 + 7 * s; cam.y = camT.y = y0 + 7 * s;
    const t = performance.now(); of(now); const js = performance.now() - t;
    const [qx, qy, qw, qh] = viewRect(0); let miss = 0;
    for (const b of blocks.values()) if (!Voxels.made(b) && b.bx * B < qx + qw && (b.bx + 1) * B > qx && b.by * B < qy + qh && (b.by + 1) * B > qy) miss++;
    out.push([js, miss]); if (s > 6) { window.frame = of; ok(out); } }; })"""


@pytest.mark.realtime
def test_land_coming_in_at_a_sprint_takes_little_of_a_frame(browser, server):
    """Watching, the camera glides ten tiles a second into new land for six seconds: all the land is there when it
    comes on the screen, and building it never takes a frame (it took 9-13 ms of some on a fast machine, 36 ms on a
    phone-speed one: the only late frames there were)."""
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
        if len(frames) > 200 and not seen[1] and work[int(len(work) * .99)] < 8 and work[-1] < 25:
            break
    page.close()
    assert len(frames) > 200 and not errors, seen
    assert sum(1 for f in frames if f[1]) == 0, seen             # nothing missing on the screen, in any frame
    assert work[int(len(work) * .99)] < 8 and work[-1] < 25, seen
