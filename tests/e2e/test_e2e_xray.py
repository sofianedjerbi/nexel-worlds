"""The x-ray circle in Chrome (js/xray.js): behind a wall or a mountain, a circle round you shows the land without the
rock in front of you, painted by the land's own painter, and nothing else changes."""


def frames(game, body):
    """Frozen frames, one moment (water moves: two moments can't be compared). `body` is JS that returns something; it
    has shot(mode): the screen's px with the circle 'on', 'clear' (on, and clear to its rim), 'off', or 'whole' (no
    rock left out, all of its picture shown: then it must be the land's own picture); and box(d, x0, y0, x1, y1): the
    px of a box of tiles. The land alone: nobody is drawn, nor the tile you aim at."""
    return game.js("""() => { const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
      const T = performance.now(), keep = {...XRAY}, S = TS(), [ox, oy] = screenOrigin(S), real = {};
      for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { real[f] = window[f]; window[f] = () => null; }
      frame(T);
      const shot = (mode) => { Object.assign(XRAY, keep, {ms: 1e9, wait: 0, turn: 0}, mode === 'off' ? {from: 9, full: 10} : mode === 'whole' ? {from: -2, full: -1, whole: true, core: .999} : mode === 'clear' ? {core: .999} : {});
        xray.t = 1; frame(T); xray.a = mode === 'off' || !xray.t ? 0 : 1; frame(T); frame(T); return ctx.getImageData(0, 0, cv.width, cv.height).data; };   // (hidden or not, the frame itself says: t)
      const box = (d, x0, y0, x1, y1) => { const out = [], k = DPR;
        for (let y = Math.round((oy + y0 * S) * k); y < Math.round((oy + y1 * S) * k); y++) for (let x = Math.round((ox + x0 * S) * k); x < Math.round((ox + x1 * S) * k); x++) { const i = (y * cv.width + x) * 4; out.push(d[i], d[i + 1], d[i + 2]); }
        return out; };
      const differ = (a, b) => { let n = 0; for (let i = 0; i < a.length; i += 4) if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2]) n++; return n; };
      const out = (() => { %s })(); Object.assign(XRAY, keep); Object.assign(window, real); window.requestAnimationFrame = raf; return out; }""" % body)


def test_behind_a_mountain_you_are_seen_through_it(game):
    """Behind a wall or a mountain you were cut at its edge: gone. A circle round you is seen through it (xray.js),
    fading toward its edge: you show, on the ground you stand on; out from behind it, the circle goes."""
    game.clear_area(10)
    game.stamp(-5, 1, ["." * 11] * 4, levels=["66666666666"] * 4)   # a wall 6 layers high, right in front (south) of you
    game.sleep(900)
    look = """(() => { const k = DPR, w = Math.round(48 * k), d = ctx.getImageData(Math.round(W / 2 * k) - w / 2, Math.round(H / 2 * k) - w / 2, w, w).data;
      return Array.from(d); })()"""
    assert game.js("xray.a") > .95
    seen = game.js(look)
    game.js("(() => { XRAY.from = 1e9; XRAY.full = 2e9; return 1; })()")          # without it: the wall, and nothing of you
    game.sleep(700)
    assert game.js("xray.a") == 0
    hidden = game.js(look)
    assert sum(1 for a, b in zip(seen[::4], hidden[::4]) if abs(a - b) > 24) > len(seen) / 4 * .3
    game.js("(() => { XRAY.from = .7; XRAY.full = .8; return 1; })()")
    game.hold(["w"], 900)                                              # out from behind it
    game.sleep(600)
    assert game.js("xray.a") == 0
    assert not game.errors


def test_the_circle_is_painted_by_the_lands_own_painter(game):
    """The circle's picture is the land painted again by the same code (relief.js), not a likeness of it. So with no
    rock left out and all of it shown, the screen is the same as without the circle, to the pixel: water, a shore,
    cliffs, their sides and corners, a step, a cave's mouth. (It had its own simpler painting: every seam, square and
    stray edge came from where the two differed.)"""
    game.clear_area(12)
    rows, lv, roofs = [], [], []
    for j in range(-6, 7):
        r, l, f = "", "", ""
        for i in range(-7, 8):
            north, south = j <= -2 and i >= -4, j >= 2 and i <= 4                 # two plateaus, a channel between them
            water, step, cave = -1 <= j <= 1 and i <= -2, j == -1 and 2 <= i <= 4, north and j == -2 and i == 0
            r += "~" if water else "."; l += "1" if cave or step else "8" if north else "5" if south else "0"; f += "5" if cave else "0"
        rows.append(r); lv.append(l); roofs.append(f)
    game.stamp(-7, -6, rows, levels=lv, roofs=roofs)
    game.sleep(1500)
    for dx, dy in [(0, 0), (-3, 1), (3, 0), (1, 1)]:
        x, y = game.pos()
        game.rpc("dev_teleport", x=x + dx, y=y + dy); game.sleep(700)
        shown, bad = frames(game, "const A = shot('whole'), any = xray.a === 1 && xray.pic.any; return [any, differ(A, shot('off'))];")
        assert shown > 10000 and bad == 0, (dx, dy, shown, bad)
        game.rpc("dev_teleport", x=x, y=y); game.sleep(300)
    assert not game.errors


def test_the_circle_shows_what_is_there_without_the_rock_in_front(game):
    """In a canyon, the plateau in front is drawn up over you, over the canyon, and over the cliff behind you. The
    circle showed the canyon's floor alone: above you the front plateau's top layer was still there, over the cliff
    behind. Now it is the land without that plateau: the cliff behind you, down to its foot. Checked against the real
    thing: the same px with the plateau in front taken away."""
    game.clear_area(12)
    game.stamp(-6, -4, ["." * 13] * 9, levels=["8" * 13] * 4 + ["0" * 13] + ["8" * 13] * 4)
    game.sleep(1500)
    x, y = game.pos()
    assert game.js("xray.a") > .95
    area = f"{x} - 1, {y} - 2, {x} + 2, {y} + 1"            # the cliff behind you and your row, inside the circle
    on, off = frames(game, f"return [box(shot('clear'), {area}), box(shot('off'), {area})];")
    assert on != off
    game.stamp(-6, 1, ["." * 13] * 4, levels=["0" * 13] * 4)         # the plateau in front, gone
    game.sleep(1500)
    assert game.js("xray.a") == 0
    assert on == frames(game, f"return box(shot('off'), {area});")
    assert not game.errors


def test_the_circle_shows_only_the_hidden_ground(game):
    """The circle is what the rock in front hides, and nothing else: rock that hides none stays as it is drawn. (It had
    painted the rock too: first the walls beside you with a tall face down to the cut, walls that are not there; then
    all of it as a brown footprint, wherever the circle reached.)"""
    game.clear_area(10)
    game.stamp(-4, -3, ["." * 9] * 7, levels=["666606666"] * 4 + ["666666666"] * 3)   # a nook, open to the north: walls west, east and south
    game.sleep(1200)
    x, y = game.pos()
    look = lambda dx, dy: game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S), out = [];
      for (let k = 3; k <= 12; k++) out.push(...ctx.getImageData(Math.round((ox + ({x + dx} + .5) * S) * DPR), Math.round((oy + ({y + dy}) * S + k * zoom) * DPR), 1, 1).data.slice(0, 3));
      return out; }})()""")
    assert game.js("xray.a") > .95
    rock, ground = look(-1, 0), look(0, -2)                   # where the wall beside you stands; the channel behind you
    game.js("(() => { XRAY.from = 9; XRAY.full = 10; return 1; })()")
    game.sleep(700)
    assert game.js("xray.a") == 0
    assert rock == look(-1, 0)                                # rock: the same, circle or not
    assert ground != look(0, -2)                              # hidden ground: the circle showed it
    assert not game.errors


def test_the_circle_never_touches_ground_that_already_shows(game):
    """Behind a wall three layers high: its top covers you and half of the row behind you. The circle shows what it
    covers; a pixel further back, where the ground shows anyway, is the same with the circle or without (it was cut
    out in whole tile columns with a margin: seams and dark lines in open ground and open water)."""
    game.clear_area(10)
    game.stamp(-3, 1, ["." * 7] * 2, levels=["3333333"] * 2)
    game.sleep(1200)
    x, y = game.pos()
    assert game.js("xray.a") > .95
    shows, covered = f"{x} - 3, {y} - 4, {x} + 4, {y} - 1 + 9 / 16", f"{x} - 1, {y} - 3 / 16, {x} + 2, {y} + 1"   # behind the wall's top edge; under it
    same, seen = frames(game, f"const A = shot('on'), B_ = shot('off'); return [box(A, {shows}).join() === box(B_, {shows}).join(), box(A, {covered}).join() !== box(B_, {covered}).join()];")
    assert same and seen
    assert not game.errors


def test_the_side_of_a_cliff_beside_open_water_is_not_seen_through(game):
    """Only rock in front of you is seen through, and only where it is drawn over something. A cliff's side sticks
    out a few px over the tile beside it: with the circle on, the water showed through that edge and its corners,
    though nothing hides that water."""
    game.clear_area(12)
    rows, lv = [], []
    for j in range(-4, 5):
        r, l = "", ""
        for i in range(-6, 7):
            front, side = 1 <= j <= 3 and -3 <= i <= 1, -3 <= j <= 0 and 3 <= i <= 4       # the plateau in front of you; a wall to the east
            r += "." if front or side else "~"; l += "6" if front or side else "0"
        rows.append(r); lv.append(l)
    game.stamp(-6, -4, rows, levels=lv)
    game.sleep(1500)
    x, y = game.pos()
    assert game.js("xray.a") > .95
    # the open water beside the wall, under its side, and the water under the plateau in front
    edge, under = f"{x} + 2 + 9 / 16, {y} - 2, {x} + 3, {y} + 1", f"{x} - 1, {y} + 1 / 16, {x}, {y} + 1"
    same, seen = frames(game, f"const A = shot('on'), B_ = shot('off'); return [box(A, {edge}).join() === box(B_, {edge}).join(), box(A, {under}).join() !== box(B_, {under}).join()];")
    assert same and seen
    assert not game.errors


def test_things_on_the_rock_in_front_of_you_fade_with_it(game):
    """What stands or lies on the rock the circle looks through would cover you again: a tree, a creature, and
    things lying there (a pile was still drawn, right over you)."""
    game.clear_area(10)
    game.give(wood=1)
    game.act("drop", item="wood")
    game.sleep(300)
    px, py = game.pos()
    game.rpc("dev_teleport", x=px, y=py - 1)                  # a tile north of the pile...
    game.sleep(700)
    x, y = game.pos()
    assert (x, y) == (px, py - 1)
    game.stamp(-3, 1, ["." * 7] * 3, levels=["6666666"] * 3)  # ...and the ground under it, and beside it, goes up six layers
    game.sleep(1300)
    assert game.js("xray.a") > .95 and game.js(f"groundItems.some(([ix, iy]) => ix === {px} && iy === {py})")
    assert game.js(f"xrayOver({px}, {py})") > .98             # in the clear middle of the circle: not drawn at all
    drawn = game.js(f"""(() => {{ const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0; let n = 0;
      const icon = ghostIcon('wood'), d = ctx.drawImage; ctx.drawImage = function (img, ...a) {{ if (img === icon) n++; return d.call(ctx, img, ...a); }};
      const T = performance.now(); frame(T); const on = n; n = 0;
      XRAY.from = 9; XRAY.full = 10; xray.a = 0; frame(T); const off = n;
      XRAY.from = .5; XRAY.full = .6; ctx.drawImage = d; window.requestAnimationFrame = raf; return [on, off]; }})()""")
    assert drawn == [0, 1], drawn                             # with the circle: gone; without: there
    assert not game.errors


def test_creatures_fade_with_the_circle(game):
    """A creature behind the rock with you showed whole in the middle of the circle and not at all a step further
    out; one on the rock was there, then gone. Both now fade as the circle does: behind the rock, what it hides of the
    creature is drawn as faint as the circle is there; on the rock, the creature thins out toward the middle."""
    game.clear_area(10)
    game.stamp(-6, 1, ["." * 13] * 3, levels=["6" * 13] * 3)  # a wall in front of you, six layers
    behind, on_rock = game.spawn("cow", 2, 0, still=600), game.spawn("chicken", -2, 1, still=600)   # in the fading ring: beside you; on the wall
    game.sleep(1500)
    assert game.js("xray.a") > .95
    drawn = game.js("""(() => { const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
      const real = window.drawEntity, seen = {}; window.drawEntity = function (p, ...a) { (seen[p.e.id] = seen[p.e.id] || []).push(+ctx.globalAlpha.toFixed(2)); return real(p, ...a); };
      frame(performance.now()); window.drawEntity = real; window.requestAnimationFrame = raf; return seen; })()""")
    whole, faint = drawn[str(behind)]
    assert whole == 1 and 0.05 < faint < 0.95, drawn         # as hidden as ever, and over that the hidden part, faint
    assert len(drawn[str(on_rock)]) == 1 and 0.05 < drawn[str(on_rock)][0] < 0.95, drawn
    assert drawn[str(game.js("myId"))] == [1], drawn          # you, in the middle: whole, once
    assert not game.errors


def test_the_circle_is_painted_again_only_when_you_change_tile(game):
    """Its picture is kept: standing still nothing is painted again; walking along behind a wall, once a tile."""
    game.clear_area(10)
    game.stamp(-7, 1, ["." * 15] * 3, levels=["6" * 15] * 3)
    game.sleep(1200)
    assert game.js("xray.a") > .95
    game.js("(() => { window.__n = 0; const real = window.xrayPicture; window.xrayPicture = function* (...a) { window.__n++; return yield* real(...a); }; return 1; })()")
    game.sleep(800)
    assert game.js("__n") == 0
    x, y = game.pos()
    game.hold(["d"], 700)                                     # east along the wall
    game.sleep(500)
    moved = game.pos()[0] - x
    assert moved >= 2 and game.js("xray.a") > .95
    assert game.js("__n") <= moved + 1, (game.js("__n"), moved)
    assert not game.errors
