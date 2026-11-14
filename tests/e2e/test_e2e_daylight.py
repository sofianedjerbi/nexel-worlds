"""The light of the day (web/js/daylight.js): the hours have their colours, the night's lights are whole pixels."""


def test_the_day_is_a_gradient_not_day_then_night(game):
    """It was plain day until a twentieth of a day before night, then one blue. The light changes all day long, with
    no jump from one moment to the next (nor from the end of a night to the day after), plain white only through the
    middle of the day, darkest and bluest in the middle of the night; the hour's colour is laid thinly (a tenth at
    most: more, and grass turns to mud)."""
    d = game.js("""(() => { const at = [...Array(1001)].map((_, i) => i / 1000), light = at.map(lightAt), wash = at.map(washAt);
      const lum = (c) => .3 * c[0] + .59 * c[1] + .11 * c[2], jump = Math.max(...light.slice(1).map((c, i) => Math.max(...c.map((v, k) => Math.abs(v - light[i][k])))));
      return {jump, ends: [light[0], light[1000]], white: at.filter((p, i) => light[i].every((v) => v === 255) && wash[i][3] === 0).map((p) => p), lum: light.map(lum),
        night: light[900], wash: Math.max(...wash.map((w) => w[3])), warm: [washAt(.69), washAt(.02)], kinds: new Set(light.map((c) => c.join())).size}; })()""")
    assert d["jump"] <= 3 and d["ends"][0] == d["ends"][1]                         # no step anywhere, and midnight joins the two days
    assert .155 <= min(d["white"]) <= .165 and .495 <= max(d["white"]) <= .505     # plain day: from mid morning to mid afternoon only
    darkest = d["lum"].index(min(d["lum"])) / 1000
    assert .85 <= darkest <= .95 and d["night"][2] > d["night"][0] + 60            # the night: blue, deepest in its middle
    assert d["lum"][700] > d["lum"][740] > d["lum"][780] > d["lum"][850] and d["lum"][970] < d["lum"][20] < d["lum"][80]   # it comes on by degrees, and goes by degrees
    assert .1 <= d["wash"] <= .121 and d["warm"][0][0] > d["warm"][0][2] + 100 and d["warm"][1][3] > .05   # warm at sunset and at sunrise, thinly
    assert d["kinds"] > 200                                                        # (hundreds of lights in a day, not two)


def test_the_days_bar_is_bands_and_checkers_in_big_cells(game):
    """The bar on what Tab shows was gold for the day and dark for the night, then a fine gradient that read as smooth.
    It is the sky's colours hour by hour as a pixel picture: 68 by 3 cells, each two px of the window's, flat bands of
    few colours, and a checker of the two where two bands meet."""
    game.page.keyboard.down("Tab")
    game.sleep(200)
    bar = game.js("""(() => { const c = $('whoband'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data, px = (x, y) => [d[(y * c.width + x) * 4], d[(y * c.width + x) * 4 + 1], d[(y * c.width + x) * 4 + 2]];
      const cols = [...Array(c.width)].map((_, x) => px(x, 0).join()), all = new Set(), checks = [...Array(c.width - 1)].filter((_, x) => px(x, 0).join() === px(x + 1, 1).join() && px(x, 1).join() === px(x + 1, 0).join() && px(x, 0).join() !== px(x, 1).join()).length;
      for (let x = 0; x < c.width; x++) for (let y = 0; y < c.height; y++) all.add(px(x, y).join());
      let run = 1, longest = 1; for (let x = 1; x < c.width; x++) { run = cols[x] === cols[x - 1] && px(x, 0).join() === px(x, 1).join() ? run + 1 : 1; longest = Math.max(longest, run); }
      return {size: [c.width, c.height], shown: [Math.round(c.getBoundingClientRect().width), Math.round(c.getBoundingClientRect().height)], kinds: all.size, checks, longest,
        noon: px(22, 1), dusk: px(48, 1), night: px(60, 1), ends: [px(0, 1), px(67, 1)], smooth: getComputedStyle(c).imageRendering, q: parseFloat(getComputedStyle($('who')).getPropertyValue('--q'))}; })()""")
    game.page.keyboard.up("Tab")
    assert bar["size"] == [68, 3] and bar["shown"] == [round(136 * bar["q"]), round(6 * bar["q"])] and bar["smooth"] == "pixelated"   # a cell: two px of the window's, cut clean
    assert 12 <= bar["kinds"] <= 26 and bar["checks"] >= 5 and bar["longest"] >= 12                      # few colours; checkers where bands meet; a long flat band (the day)
    assert bar["noon"][0] > 240 and bar["noon"][2] > 140 and bar["night"][2] > bar["night"][0] + 40 and sum(bar["night"]) < 330   # pale gold at noon, deep blue at night
    assert bar["dusk"][0] > bar["dusk"][2] + 60 and bar["dusk"][1] < 190                                 # ...orange and rose between them
    assert max(abs(a - b) for a, b in zip(*bar["ends"])) < 100 and bar["ends"][1][0] > 150               # it ends near where it begins: the rose of sunrise coming back


def test_at_night_the_lights_are_whole_pixels_in_steps(game):
    """A fire's light and your own were smooth round glows added over the picture. They are worked out an art px at a
    time: on the screen each art px of the lit ground is one colour, the light falls off in a few steps, and where
    there is no light the night's blue is the same everywhere."""
    game.stamp(3, 0, ["^"])
    game.rpc("dev_time", phase=.88)
    game.sleep(1200)
    seen = game.js("""() => new Promise((ok) => requestAnimationFrame(() => { const z = zoom * DPR, c = cv.getContext('2d'), s = myPos();
      const S = TS(), [ox, oy] = screenOrigin(S), gx = Math.round((ox + (s.x + 3) * S + S / 2) * DPR), gy = Math.round((oy + s.y * S + S / 2) * DPR);     // the fire, on the canvas
      const x0 = gx - ((gx - Math.round(ox * DPR)) % z + z) % z, y0 = gy + 20 * z - ((gy - Math.round(oy * DPR)) % z + z) % z;                           // an art px of the land, under it
      const row = c.getImageData(x0, y0, 90 * z, z).data; let blocky = true; const steps = [];
      for (let i = 0; i < 90; i++) { const o = i * z * 4, a = [row[o], row[o + 1], row[o + 2]].join();
        for (let k = 1; k < z; k++) for (let j = 0; j < z; j++) { const q = (j * 90 * z + i * z + k) * 4; if ([row[q], row[q + 1], row[q + 2]].join() !== a) blocky = false; }
        if (steps[steps.length - 1] !== a) steps.push(a); }
      const ground = (im) => { let n = 0, sum = 0; for (let o = 0; o < im.length; o += 4) { sum += im[o] + im[o + 1] + im[o + 2]; n++; } return sum / n; };     // how bright a patch is
      const lit = ground(c.getImageData(gx - 8 * z, gy + 6 * z, 16 * z, 8 * z).data), far = ground(c.getImageData(Math.round(30 * DPR), Math.round(H * DPR * .6), 16 * z, 8 * z).data);
      ok({blocky, steps: steps.length, lit, far, tint: lightAt(clock.phase)}); }))""")
    assert seen["blocky"]                                                          # every art px one colour
    assert seen["tint"][0] < 150 < seen["tint"][2] and seen["far"] < seen["lit"] * .75, seen      # the night's light is blue; by the fire the ground is far brighter than away from it
    assert 4 <= seen["steps"] <= 60, seen                                          # (along ninety px out from under the fire: steps, the grass's own colours among them, not ninety shades)
    game.clear_area(6)                                                             # (the fire is not left for the next test's player to wake by)
