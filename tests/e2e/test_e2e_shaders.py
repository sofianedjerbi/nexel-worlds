"""Shaders (shader.js, sun.js; the settings' Shaders page): the finished picture repainted (glow, colours, old
screens' lines), and what a shader adds to the world: shadows that follow the sun, reflections, light on water, rays,
a fire's shadows. Each shader's own settings."""

ROW = "document.querySelector('#menu .row.on .name').textContent"


def at_row(game, name):
    for _ in range(20):
        if game.js(ROW) == name:
            return
        game.press("ArrowDown", 30)
    raise AssertionError(f"no row {name}")


def test_a_shader_repaints_the_picture_and_off_is_as_before(game):
    assert game.js("[opt('shader'), !!Shader.el, Sun.shades()]") == ["off", False, False]            # nothing of it until asked for
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab"); game.press("Tab")
    assert game.js("[...document.querySelectorAll('#menu .row .name')].map((e) => e.textContent)") == ["Shader", "Strength", "Glow", "Shadows", "Shadow length", "Land shadows", "Water reflections", "Light on water", "Sun rays", "Cloud shadows", "Dark corners"]
    game.press("ArrowRight", 500)                               # the first look
    assert game.js("[opt('shader'), Shader.works, getComputedStyle(Shader.el).display, Shader.el.width === cv.width, Shader.el.height === cv.height]") == ["natural", True, "block", True, True]
    game.press("Escape"); game.press("Escape")
    game.js("setOpt('shader', 'golden')")                       # (Natural keeps the colours: a graded one, to see it act)
    game.sleep(300)
    look = """(() => { const c = document.createElement("canvas"); c.width = 40; c.height = 30; const g = c.getContext("2d");
      g.drawImage(Shader.el, 0, 0, 40, 30); const fx = [...g.getImageData(0, 0, 40, 30).data];
      g.drawImage(cv, 0, 0, 40, 30); const plain = [...g.getImageData(0, 0, 40, 30).data];
      let d = 0, lit = 0; for (let i = 0; i < fx.length; i += 4) { d += Math.abs(fx[i] - plain[i]) + Math.abs(fx[i + 1] - plain[i + 1]) + Math.abs(fx[i + 2] - plain[i + 2]); lit += fx[i] + fx[i + 1] + fx[i + 2]; }
      return [d / 1200, lit / 3600]; })()"""
    game.js("window.shot = null; requestAnimationFrame(() => requestAnimationFrame(() => { window.shot = " + look + "; }))")      # (read it in the frame it was drawn in)
    game.wait("window.shot")
    d, lit = game.js("shot")
    assert 1 < d < 150 and lit > 40, (d, lit)                   # the same picture, graded: not the plain one, not a blank or a white-out
    game.js("setOpt('shaderk', 0); setOpt('clouds', 0); window.shot = null; requestAnimationFrame(() => requestAnimationFrame(() => { window.shot = " + look + "; }))")
    game.wait("window.shot")
    assert game.js("shot")[0] < 2, game.js("shot")              # strength 0: the picture as it is
    game.js("setOpt('shader', 'off')"); game.sleep(200)
    assert game.js("getComputedStyle(Shader.el).display") == "none"
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_a_shader_gives_things_a_shadow_that_follows_the_sun_and_a_reflection_in_water(game):
    game.clear_area(8)
    game.stamp(-6, -1, ["...........", ".T.........", "~~~~~~~~~~~", "~~~~~~~~~~~", "..........."])      # a tree, a pond under it
    x, y = game.pos()
    tx, ty = x - 5, y                                           # the tree (you stand well east of it: your own shadow is not in what is measured)
    lit = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
      const S = TS(), [ox, oy] = screenOrigin(S), a = Math.round((ox + x0 * S) * DPR), b = Math.round((oy + y0 * S) * DPR);
      const d = cv.getContext("2d").getImageData(a, b, Math.round((x1 - x0) * S * DPR), Math.round((y1 - y0) * S * DPR)).data;
      let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] + d[i + 1] + d[i + 2];
      ok(sum / d.length * 4 / 3); })))"""
    west, east, pond = [tx - 2, ty + .4, tx, ty + 1], [tx + 1, ty + .4, tx + 3, ty + 1], [tx - .5, ty + 1.1, tx + 1.5, ty + 2.6]
    game.js("setOpt('shimmer', false)")                         # (still water: what is measured is the reflection, not a wave)
    game.rpc("dev_time", phase=.06)                             # early morning: the sun in the east
    game.sleep(1200)
    plain = [game.js(lit, r) for r in (west, east, pond)]
    game.js("setOpt('clouds', 0); setOpt('shader', 'natural')")      # (no clouds: their shadows are in the land's own picture, and drift)
    game.sleep(800)
    on = [game.js(lit, r) for r in (west, east, pond)]
    assert on[0] < plain[0] - 3 and abs(on[1] - plain[1]) < 1.5, (plain, on)      # its shadow lies to the west, none to the east
    assert game.js("Sun.shades()") is True                      # (and the pale mark under you is not drawn: you have a shadow)
    game.js("setOpt('reflect', 0)"); game.sleep(600)        # the tree is in the water under it: the water without it is not the same
    bare = game.js(lit, pond)
    assert abs(on[2] - bare) > 1 and abs(game.js(lit, pond) - bare) < .3, (on, bare)
    game.rpc("dev_time", phase=.7)                              # evening: the other side
    game.sleep(1200)
    game.js("setOpt('shader', 'off')"); game.sleep(600)
    plain = [game.js(lit, r) for r in (west, east)]
    game.js("setOpt('shader', 'natural')"); game.sleep(800)
    on = [game.js(lit, r) for r in (west, east)]
    assert on[1] < plain[1] - 3 and abs(on[0] - plain[0]) < 1.5, (plain, on)
    game.js("setOpt('shadows', 0)"); game.sleep(600)
    assert game.js(lit, east) > on[1] + 3                       # (the hour's light moves on meanwhile: lighter than shaded, not equal to before)
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_nothing_is_reflected_in_water_that_a_hill_hides(game):
    # "player reflection is visible even if player is standing on a mountain, because there's water under it"
    game.clear_area(8)
    game.stamp(-3, -3, ["~~~~~~~", "~~~~~~~", ".......", ".......", "......."], levels=["0000000", "0000000", "5555555", "5555555", "5555555"])
    game.rpc("dev_time", phase=.3)
    game.js("setOpt('shimmer', false); setOpt('shadows', 0); setOpt('reflect', 0); setOpt('clouds', 0); setOpt('shader', 'natural')")      # (no clouds: their shadows drift over the land's own picture)
    game.sleep(1200)
    x, y = game.pos()
    grab = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
      const a = Math.round(x0 * DPR), b = Math.round(y0 * DPR), d = cv.getContext("2d").getImageData(a, b, Math.round((x1 - x0) * DPR), Math.round((y1 - y0) * DPR)).data;
      let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] * 3 + d[i + 1] * 5 + d[i + 2] * 7; ok(sum); })))"""
    # you stand on the hill's top; drawn lifted, it covers the pond behind it. The screen under your feet, where your
    # reflection would be turned over to: the same with reflections on and off.
    box = game.js("(() => { const S = TS(), [ox, oy] = screenOrigin(S), p = ents.get('agent' + myId), sy = (yy) => oy + yy * S; const fy = bodyY(p, sy) + 14 * zoom, fx = ox + p.x * S; return [fx - S, fy, fx + 2 * S, fy + 2 * S]; })()")
    assert game.js("liftOf({x: %d, y: %d})" % (x, y)) > 0
    off = game.js(grab, box)
    game.js("setOpt('reflect', 100)"); game.sleep(800)
    assert game.js(grab, box) == off
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_a_shadow_adds_no_dust_or_spray_and_a_swimmer_has_none(game):
    # "particle shadow create weird patterns.. especially the one when sprinting in water": drawing a body again for
    # its shadow and its reflection threw up its dust and its spray again
    game.clear_area(15)                                             # (all the screen, and four tiles on: a tree left at its edge has a shadow too, and "nothing on the layer" was then by luck of where you woke)
    game.stamp(1, -1, ["~~~~~~~", "~~~~~~~", "~~~~~~~"])
    count = """(ms) => new Promise((ok) => { let n = 0, seen = new Set(); const t0 = performance.now();
      const tick = () => { for (const q of parts) if (!seen.has(q)) { seen.add(q); n++; } if (performance.now() - t0 < ms) requestAnimationFrame(tick); else ok(n); };
      requestAnimationFrame(tick); })"""
    def swim():
        game.rpc("dev_teleport", x=game.home[0], y=game.home[1]); game.sleep(500)
        game.page.keyboard.down("Shift"); game.page.keyboard.down("d")
        game.sleep(600)
        n = game.js(count, 1500)
        game.page.keyboard.up("d"); game.page.keyboard.up("Shift"); game.sleep(300)
        return n
    game.home = game.pos()
    plain = swim()
    game.js("setOpt('shader', 'natural')"); game.sleep(500)
    shaded = swim()
    assert plain > 5 and shaded < plain * 1.5, (plain, shaded)      # as much spray as without (it came three times over)
    lit = """() => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => { let seen = 0; const d = Sun.layerData(); for (let i = 3; i < d.length; i += 4) if (d[i]) seen++; ok(seen); })))"""
    game.rpc("dev_teleport", x=game.home[0], y=game.home[1]); game.sleep(600)
    assert game.js(lit) > 20                                        # on land: your shadow is on the layer
    game.rpc("dev_teleport", x=game.home[0] + 4, y=game.home[1]); game.sleep(600)
    game.wait(f"(() => {{ const p = ents.get('agent' + myId); return !!p && p.x === {game.home[0] + 4} && p.y === {game.home[1]} && parts.length === 0; }})()", 8000)   # (there, as drawn, and the spray of getting there gone: on a busy machine 0.6 s was not always enough)
    assert game.js("DEPTH_OF[gndAt(myPos().x, myPos().y)] > 0")     # in the water: nothing of you on it
    assert game.js(lit) == 0, game.js(lit)
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_the_old_school_shaders_draw_their_lines(game):
    # "add old school shaders, lines": a tube's lines, a handheld's greens, a terminal's one green
    assert game.js("['screen', 'crt', 'arcade', 'tape', 'handheld', 'terminal'].every((k) => SHADERS[k])")
    game.clear_area(6)
    game.rpc("dev_time", phase=.3)
    game.js("zoom = 4; ZOOM.to = 4; setOpt('clouds', 0); setOpt('corners', 0); setOpt('shadows', 0)")
    rows = """(k) => new Promise((ok) => { setOpt('shader', k); setTimeout(() => requestAnimationFrame(() => requestAnimationFrame(() => {
      const c = document.createElement("canvas"); c.width = 64; c.height = 64; const g = c.getContext("2d");
      g.drawImage(Shader.el, Shader.el.width / 2 + 40, Shader.el.height / 2 + 40, 64, 64, 0, 0, 64, 64);      // (a patch of meadow, device px as they are)
      const d = g.getImageData(0, 0, 64, 64).data, row = [], sum = [0, 0, 0];
      for (let y = 0; y < 64; y++) { let v = 0; for (let x = 0; x < 64; x++) { const i = (y * 64 + x) * 4; v += d[i] + d[i + 1] + d[i + 2]; sum[0] += d[i]; sum[1] += d[i + 1]; sum[2] += d[i + 2]; } row.push(v / 64); }
      const art = Math.round(zoom * DPR), dark = row.filter((v, y) => y % art === (64 - 1 - (Shader.el.height - (Shader.el.height / 2 + 40) - 64)) % art);
      ok({spread: Math.max(...row) - Math.min(...row), rgb: sum.map((v) => v / 4096), works: Shader.works}); })), 400); })"""
    plain, tube, hand, term = (game.js(rows, k) for k in ("natural", "crt", "handheld", "terminal"))
    assert all(r["works"] for r in (plain, tube, hand, term))
    assert tube["spread"] > plain["spread"] + 40, (plain, tube)                 # dark lines across it
    assert hand["rgb"][1] > hand["rgb"][0] * 1.1 and hand["rgb"][2] < 80, hand    # greens, next to no blue
    assert term["rgb"][1] > term["rgb"][0] * 3 and term["rgb"][1] > term["rgb"][2] * 2, term
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_what_is_written_in_the_world_is_drawn_over_a_shader_not_through_it(game):
    # "your shaders make text bubble unreadable and too bright": a bubble went through the glow with the rest
    game.clear_area(5)
    game.js("setOpt('names', false)")
    # One frame drawn twice, with what is said and without it: `sum` is the light of the meadow over your head with it,
    # `bare` without. (It was two frames seconds apart: whatever else moved there in between, the curved world's sky
    # at first, was taken for the bubble: one run in three failed.)
    ink = """() => new Promise((ok) => requestAnimationFrame((T) => {
      const count = (c) => { if (!c) return -1; const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 200) n++; return n; };
      const S = TS(), [ox, oy] = screenOrigin(S), p = ents.get("agent" + myId), raf = window.requestAnimationFrame, said = bubbles.slice(); window.requestAnimationFrame = () => 0;
      const lit = () => { const d = cv.getContext("2d").getImageData(Math.round((ox + p.x * S - 3 * S) * DPR), Math.round((oy + p.y * S - 3.5 * S) * DPR), Math.round(7 * S * DPR), Math.round(3 * S * DPR)).data;
        let sum = 0; for (let i = 0; i < d.length; i += 4) sum += d[i] + d[i + 1] + d[i + 2]; return sum; };
      const out = {said: said.length};
      try { frame(T); out.sum = lit(); out.words = count(Shader.words); out.shown = Shader.words ? getComputedStyle(Shader.words).display : "none"; bubbles.length = 0; frame(T); out.bare = lit(); }
      finally { bubbles.length = 0; bubbles.push(...said); window.requestAnimationFrame = raf; raf(frame); }
      ok(out); }))"""
    game.act("say", text="hello there, a long line to see")
    game.wait("bubbles.length > 0")
    game.sleep(400)
    plain = game.js(ink)
    by = abs(plain["sum"] - plain["bare"])
    assert plain["said"] and by > 20000 and plain["shown"] == "none", plain     # no shader: the bubble is on the picture
    game.js("setOpt('shader', 'soft'); setOpt('shadows', 0); setOpt('clouds', 0)"); game.sleep(600)
    on = game.js(ink)
    assert on["said"] and abs(on["sum"] - on["bare"]) < by / 8 and on["words"] > 300 and on["shown"] == "block", (plain, on)    # a shader: not in what it repaints, over it
    game.js("setOpt('shader', 'off')"); game.sleep(400)
    off = game.js(ink)
    assert off["said"] and off["shown"] == "none" and abs(off["sum"] - off["bare"]) > by / 2, (plain, off)
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_the_shaders_light_the_water_send_rays_at_low_sun_and_a_fire_throws_shadows(game):
    # "can you make the shaders even more beautiful ?"
    game.clear_area(8)
    game.stamp(-6, -1, ["...........", ".T.^.......", "...........", "~~~~~~~~~~~", "~~~~~~~~~~~"])      # a tree, a fire east of it, a pond
    x, y = game.pos()
    tx, ty = x - 5, y
    game.js("setOpt('shimmer', false); setOpt('clouds', 0); setOpt('corners', 0)")
    assert game.js("Sun.water") is None                         # no shader: nothing is worked out
    game.js("setOpt('shader', 'natural')"); game.sleep(800)
    assert game.js("!!Sun.water && Sun.water.width === Math.ceil(W / 4)")       # where the water is seen, for the sky, the clouds and the glitter
    fx = """([x0, y0, x1, y1]) => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
      const c = document.createElement("canvas"); c.width = 60; c.height = 40; const g = c.getContext("2d");
      g.drawImage(Shader.el, x0 * Shader.el.width, y0 * Shader.el.height, (x1 - x0) * Shader.el.width, (y1 - y0) * Shader.el.height, 0, 0, 60, 40);
      const d = g.getImageData(0, 0, 60, 40).data; let sum = 0, blue = 0; for (let i = 0; i < d.length; i += 4) { sum += d[i] + d[i + 1] + d[i + 2]; blue += d[i + 2] - d[i]; }
      ok([sum / 2400, blue / 2400]); })))"""
    pond = game.js("(() => { const S = TS(), [ox, oy] = screenOrigin(S); return [(ox + %d * S) / W, (oy + %d * S) / H, (ox + %d * S) / W, (oy + %d * S) / H]; })()" % (x - 5, y + 2, x + 3, y + 4))
    game.rpc("dev_time", phase=.37); game.sleep(1200)
    lit = game.js(fx, pond)
    game.js("setOpt('waterlight', 0)"); game.sleep(600)
    assert game.js("Sun.water") is None
    dull = game.js(fx, pond)
    assert lit[1] > dull[1] + 4, (lit, dull)                    # noon: the sky's blue lies in the water
    game.rpc("dev_time", phase=.05); game.sleep(1200)           # the sun low in the east: shafts of light from that side
    corner = [.55, .0, 1, .45]
    rays = game.js(fx, corner)
    game.js("setOpt('rays', 0)"); game.sleep(600)
    assert rays[0] > game.js(fx, corner)[0] + 1.5, rays
    game.rpc("dev_time", phase=.87); game.sleep(1500)           # night: the tree's shadow lies away from the fire, to the west
    # (one frame drawn with the shadows and without: the fire's light flickers from a frame to the next by as much as
    # its shadow darkens this part, which is what made this test fail one run in three)
    from test_e2e_sunland import twice
    (shaded, bare), = twice(game, [[tx - 2, ty + .3, tx, ty + 1.1]], "shadows", 0)
    assert bare > shaded + .3, (shaded, bare)                   # (little, in numbers: the night darkens all of it afterwards, and a thin tree's is a line; but it is the same frame: nothing else differs)
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_each_shader_has_settings_of_its_own_and_keeps_them(game):
    # "add more settings also. feel free to add per-shader settings"
    game.clear_area(6)
    game.rpc("dev_time", phase=.3)
    game.js("zoom = 4; ZOOM.to = 4; setOpt('clouds', 0); setOpt('corners', 0); setOpt('shadows', 0)")
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab"); game.press("Tab")
    names = "[...document.querySelectorAll('#menu .row .name')].map((e) => e.textContent).filter((n) => n.startsWith('· '))"
    assert game.js(names) == []                                 # no shader: nothing of a shader's own
    game.press("ArrowRight")
    assert game.js("opt('shader')") == "natural" and game.js(names) == ["· Colour", "· Warmth", "· Contrast", "· Haze"]
    game.js("setOpt('shader', 'crt'); drawMenu()")
    assert game.js(names) == ["· Colour", "· Warmth", "· Contrast", "· Haze", "· Lines", "· Screen bulge", "· Colour stripes", "· Colour fringe"]
    game.js("setOpt('shader', 'handheld'); drawMenu()")
    assert game.js(names) == ["· Contrast", "· Haze", "· Pixel grid"]
    game.js("setOpt('shader', 'crt'); drawMenu()")
    at_row(game, "· Lines")
    for _ in range(5):
        game.press("ArrowLeft", 40)                             # the tube's lines: none
    assert game.js("[lookOpt('scan'), JSON.stringify(opt('looks'))]") == [0, '{"crt":{"scan":0}}']
    assert game.js("document.querySelector('#menu .row.on').classList.contains('own')")
    game.press("Escape"); game.press("Escape")
    spread = """() => new Promise((ok) => setTimeout(() => requestAnimationFrame(() => requestAnimationFrame(() => {
      const c = document.createElement("canvas"); c.width = 64; c.height = 64; const g = c.getContext("2d");
      g.drawImage(Shader.el, Shader.el.width / 2 + 40, Shader.el.height / 2 + 40, 64, 64, 0, 0, 64, 64);
      const d = g.getImageData(0, 0, 64, 64).data, row = [];
      for (let y = 0; y < 64; y++) { let v = 0; for (let x = 0; x < 64; x++) { const i = (y * 64 + x) * 4; v += d[i] + d[i + 1] + d[i + 2]; } row.push(v / 64); }
      ok(Math.max(...row) - Math.min(...row)); })), 400))"""
    none = game.js(spread)
    game.js("setOpt('shader', 'arcade')")                       # another shader: its own lines, as it comes
    assert game.js("lookOpt('scan')") == 100 and game.js(spread) > none + 40
    game.js("setOpt('shader', 'crt')")                          # and the tube's are still off
    assert game.js("lookOpt('scan')") == 0 and game.js(spread) < none + 10
    game.js("setLookOpt('scan', 200)")
    assert game.js(spread) > none + 60
    game.js("setLookOpt('scan', 100)")
    assert game.js("JSON.stringify(opt('looks'))") == "{}"      # as it comes: nothing kept
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")
