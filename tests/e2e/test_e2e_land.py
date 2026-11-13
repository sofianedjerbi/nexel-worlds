"""Land coming in: only what shows is painted, a little a frame, and it is the same land to the pixel."""

LV = "0123456789ABC"
# a mountain of terraces twelve layers high, 13 tiles across
MOUNTAIN = ["".join(LV[max(0, 12 - 2 * max(abs(dx), abs(dy)))] for dx in range(-6, 7)) for dy in range(-6, 7)]

# every block's ground and raised picture, drawn again from nothing: a hash of each
SIG = """() => { const hash = (c) => { if (!c) return 0; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let a = 2166136261;
    for (let i = 0; i < d.length; i++) a = Math.imul(a ^ d[i], 16777619); return a >>> 0; };
  return [...blocks.values()].filter((b) => b.canvas).sort((p, q) => p.by - q.by || p.bx - q.bx).map((b) => {
    let n = 0; const o = b.ctx.drawImage; b.ctx.drawImage = function (...a) { n++; return o.apply(this, a); };
    for (let ly = 0; ly < B; ly++) for (let lx = 0; lx < B; lx++) drawTile(b.bx * B + lx, b.by * B + ly);
    delete b.ctx.drawImage; buildRelief(b);
    return {key: [hash(b.canvas), hash(b.relief.flat), b.relief.up, b.relief.minLv, (b.relief.box || []).join()].join(':'), n}; }); }"""


def test_only_what_shows_is_painted_and_the_land_is_the_same(game):
    """A tile is painted from its last solid layer, and a level's tiles hidden under the level above are passed over
    (tiles.js, relief.js). The pictures are the same to the pixel as with every layer painted (nothing taken for
    solid); a block cost 42 ms to build at the foot of a twelve-layer mountain, on a fast machine."""
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN)
    game.stamp(-9, -4, ["..~~..", ".~~~~.", "..~~.."], levels=["000000", "0aaaa0", "000000"])     # a pond, and a pit under it
    game.sleep(900)
    game.js(SIG)                                                 # (read once first: Chrome paints a canvas another way once it has been read)
    quick = game.js(SIG)
    game.js("(() => { window.__solid = cellSolid; window.cellSolid = () => false; return 1; })()")
    whole = game.js(SIG)
    game.js("(() => { window.cellSolid = window.__solid; return 1; })()")
    assert [b["key"] for b in quick] == [b["key"] for b in whole] and len(quick) >= 2
    assert sum(b["n"] for b in quick) * 5 < sum(b["n"] for b in whole) * 3    # (about half the paint on a meadow, a tenth on the mountain)
    assert game.js(SIG) == quick                                              # ...and drawn again, the same


def test_a_blocks_raised_ground_is_built_in_small_steps(game):
    """No step of building a block is long (they were up to 10 ms each on a fast machine: a late frame on a slow one)."""
    game.stamp(-6, -18, ["." * 13] * 13, levels=MOUNTAIN)
    game.sleep(900)
    worst = game.js("""(() => { let worst = 0, steps = 0; for (const b of blocks.values()) { if (!b.canvas) continue;
      for (let r = 0; r < 3; r++) { let w = 0, n = 0; const it = blockRelief(b); for (;;) { const t0 = performance.now(), s = it.next(); w = Math.max(w, performance.now() - t0); n++; if (s.done) break; } if (!r || w < worst) worst = w; steps = Math.max(steps, n); } }
      return [worst, steps]; })()""")
    assert worst[0] < 5 and worst[1] > 100, worst                # (the mountain's block: over a hundred steps, none long)


def test_a_blocks_water_is_made_again_only_when_it_changed(game):
    """Its bottom and its tint were made again whenever a tile of the block was drawn again, in the frame that showed it."""
    game.stamp(3, -3, ["~~~", "~~~"])
    game.sleep(900)
    x, y = game.pos()
    game.js(f"(() => {{ const b = tileIdx({x + 4}, {y - 3})[0]; window.__b = b; window.__w = b.water; return b.water.any; }})()")
    assert game.js("__w.any") is True
    game.stamp(-4, 3, ["_"])                                     # a cobbled tile, away from the water: its block is built again
    game.sleep(900)
    assert game.js("__b.water === __w && !__b.reliefGen && !__b.reliefDirty") is True
    game.stamp(3, -1, ["~"])                                     # the pond grows
    game.sleep(900)
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
