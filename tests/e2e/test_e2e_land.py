"""Land coming in: only what shows is painted, a little a frame, in the page, and it is the same land to the pixel."""

LV = "0123456789ABC"
# a mountain of terraces twelve layers high, 13 tiles across
MOUNTAIN = ["".join(LV[max(0, 12 - 2 * max(abs(dx), abs(dy)))] for dx in range(-6, 7)) for dy in range(-6, 7)]

# every block's ground and raised picture, drawn again from nothing: a hash of each
SIG = """() => { const hash = (c) => { if (!c) return 0; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let a = 2166136261;
    for (let i = 0; i < d.length; i++) a = Math.imul(a ^ d[i], 16777619); return a >>> 0; };
  return [...blocks.values()].filter((b) => b.canvas).sort((p, q) => p.by - q.by || p.bx - q.bx).map((b) => {
    let n = 0; const o = window.layCell; window.layCell = function (...a) { n++; return o(...a); };
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly);
    window.layCell = o; buildRelief(b);
    return {key: [hash(b.canvas), hash(b.relief.flat), b.relief.up, b.relief.minLv, (b.relief.box || []).join()].join(':'), n}; }); }"""


def test_only_what_shows_is_painted_and_the_land_is_the_same(game):
    """A tile is painted from its last solid layer, and a level's tiles hidden under the level above are passed over
    (tiles.js, relief.js). The pictures are the same to the pixel as with every layer laid (nothing taken for
    solid); a block cost 42 ms to build at the foot of a twelve-layer mountain, on a fast machine."""
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN)
    pond(game)                                                   # a pond, and a pit under it
    game.sleep(900)
    game.js(SIG)                                                 # (read once first: Chrome paints a canvas another way once it has been read)
    quick = game.js(SIG)
    game.js("(() => { window.__solid = cellSolid; window.cellSolid = () => false; return 1; })()")
    whole = game.js(SIG)
    game.js("(() => { window.cellSolid = window.__solid; return 1; })()")
    assert [b["key"] for b in quick] == [b["key"] for b in whole] and len(quick) >= 2
    assert sum(b["n"] for b in quick) * 5 < sum(b["n"] for b in whole) * 3    # (about half the paint on a meadow, a tenth on the mountain)
    assert game.js(SIG) == quick                                              # ...and drawn again, the same


PAGE = """() => { const P = CanvasRenderingContext2D.prototype, od = P.drawImage, op = P.putImageData, out = [];
  for (const b of blocks.values()) { if (!b.px || !b.relief) continue;
    const c = document.createElement('canvas'); c.width = c.height = BW; const g = c.getContext('2d', {willReadFrequently: true});
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly, {g, ox: lx * 16, oy: ly * 16});
    const d = new Uint8Array(g.getImageData(0, 0, BW, BW).data.buffer), p = new Uint8Array(b.px.buffer); let diff = 0, near = 0, shown = 0, draws = 0, puts = 0;
    for (let i = 0; i < d.length; i += 4) { const solid = d[i + 3] === 255 && p[i + 3] === 255, by = Math.max(Math.abs(d[i] - p[i]), Math.abs(d[i + 1] - p[i + 1]), Math.abs(d[i + 2] - p[i + 2]));
      if (solid ? by > 1 : Math.abs(d[i + 3] - p[i + 3]) > 1) diff++; else if (by) near++; }
    P.drawImage = function (...a) { draws++; return od.apply(this, a); }; P.putImageData = function (...a) { puts++; return op.apply(this, a); };
    b.shown = -1; buildRelief(b); P.drawImage = od; P.putImageData = op;
    const s = new Uint32Array(b.canvas.getContext('2d').getImageData(0, 0, BW, BW).data.buffer);
    for (let i = 0; i < s.length; i++) if (s[i] !== b.px[i]) shown++;
    out.push({diff, near, shown, draws, puts, levels: b.relief.maxLv - b.relief.minLv, water: b.water.any}); }
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
    """A block's ground and its raised picture are px worked out in the page, each made a canvas once (tiles.js,
    relief.js). Put together by the GPU a piece at a time (a mask, the ground drawn into it, a few rows put and a few
    rows drawn, on canvases used again for the next level), a phone showed the mask itself on cliff tops: black
    tiles, which no desktop drew. The px are the tiles as a canvas lays them (a sheet's see-through shadow rounds a
    step differently here and there, as it does from one canvas to another); and building a block draws on no
    canvas: two pictures are put, once each."""
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN)
    pond(game)
    game.sleep(900)
    blocks = game.js(PAGE)
    assert len(blocks) >= 2 and max(b["levels"] for b in blocks) >= 12
    assert all(b["diff"] == 0 and b["shown"] == 0 and b["near"] < 2000 for b in blocks), blocks
    dry = [b for b in blocks if not b["water"]]
    assert dry and all(b["draws"] == 0 and b["puts"] == (2 if b["levels"] else 1) for b in dry), blocks
    assert all(b["puts"] <= 3 and b["draws"] <= 1 for b in blocks), blocks      # (water: its tint, a px a tile, blown up)


def test_a_blocks_raised_ground_is_built_in_small_steps(game):
    """No step of building a block is long (they were up to 10 ms each on a fast machine: a late frame on a slow one)."""
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN)
    game.sleep(900)
    worst = game.js("""(() => { let worst = 0, steps = 0; for (const b of blocks.values()) { if (!b.canvas) continue;
      for (let r = 0; r < 3; r++) { let w = 0, n = 0; const it = blockRelief(b); for (;;) { const t0 = performance.now(), s = it.next(); w = Math.max(w, performance.now() - t0); n++; if (s.done) break; } if (!r || w < worst) worst = w; steps = Math.max(steps, n); } }
      return [worst, steps]; })()""")
    assert worst[0] < 5 and worst[1] > 100, worst                # (the mountain's block: over a hundred steps, none long)


def test_a_blocks_water_is_made_again_only_when_it_changed(game):
    """Its bottom and its tint were made again whenever a tile of the block was drawn again, in the frame that showed it.
    (The pond, the tile it grows by and the cobbled tile are put inside one block: at fixed places they fell on two
    when the player woke near a block's edge, and the pond's block was then made again for a tile that is not its own.)"""
    x, y = game.pos()
    px, py = x + 3, y - 3
    px -= max(0, px % 32 + 3 - 32)
    py -= max(0, py % 32 + 3 - 32)
    cx = px - 6 if px % 32 >= 6 else px + 7                      # a cobbled tile, away from the water, in its block
    game.stamp(px - x, py - y, ["~~~", "~~~"])
    game.sleep(900)
    game.js(f"(() => {{ const b = tileIdx({px + 1}, {py})[0]; window.__b = b; window.__w = b.water; return b.water.any; }})()")
    assert game.js("__w.any") is True and game.js(f"tileIdx({cx}, {py})[0] === __b && tileIdx({px}, {py + 2})[0] === __b") is True
    built = "!dirtyTiles.length && !__b.reliefGen && !__b.reliefDirty"
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
    for (const b of blocks.values()) if (!b.relief && b.bx * B < qx + qw && (b.bx + 1) * B > qx && b.by * B < qy + qh && (b.by + 1) * B > qy) miss++;
    out.push([js, miss]); if (s > 6) { window.frame = of; ok(out); } }; })"""


def test_land_coming_in_at_a_sprint_takes_little_of_a_frame(browser, server):
    """Watching, the camera glides ten tiles a second into new land for six seconds: all the land is there when it
    comes on the screen, and building it never takes a frame (it took 9-13 ms of some on a fast machine, 36 ms on a
    phone-speed one: the only late frames there were)."""
    page = browser.new_page(viewport={"width": 844, "height": 390})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{server}/?zoom=2")
    page.wait_for_function("typeof ready !== 'undefined' && typeof blocks !== 'undefined' && blocks.size > 0 && !arrivingNow", timeout=20000)
    page.wait_for_timeout(1500)
    frames = page.evaluate(GLIDE)[5:]
    page.close()
    work = sorted(f[0] for f in frames)
    assert len(frames) > 200 and not errors
    assert sum(1 for f in frames if f[1]) == 0                   # nothing missing on the screen, in any frame
    assert work[int(len(work) * .99)] < 8 and work[-1] < 25, work[-5:]
