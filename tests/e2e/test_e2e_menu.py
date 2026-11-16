"""The game's menu and its settings (menu.js, options.js): "implement a full settings menu into the game (echap) like
minecraft with lot of options". Esc opens a short list; the settings are pages of rows; every row does what it says,
at once, and is kept."""

ROW = "document.querySelector('#menu .row.on .name').textContent"


def at_row(game, name):
    for _ in range(20):
        if game.js(ROW) == name:
            return
        game.press("ArrowDown", 30)
    raise AssertionError(f"no row {name}")


def test_esc_opens_the_menu_and_no_key_acts_behind_it(game):
    game.press("Escape")
    assert game.js("menuOpen()") and game.js("[...document.querySelectorAll('#menu .row .name')].map((e) => e.textContent)") == ["Back to the game", "Settings", "Help", "Leave the world"]
    at = game.pos()
    game.press("i"); game.hold(["d"], 400)                     # the inventory's key, and a step: neither happens
    assert not game.js("isOpen('bag')") and game.pos() == at
    game.press("Escape")
    assert not game.js("menuOpen()")
    game.press("i")
    assert game.js("isOpen('bag')")
    game.press("Escape"); assert not game.js("isOpen('bag')") and not game.js("menuOpen()")      # Esc shuts a window first
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter")
    assert game.js("[...document.querySelectorAll('#menu .tab')].map((e) => e.textContent)") == ["Sound", "Picture", "Shaders", "Screen", "Keys"]
    assert game.js("document.querySelectorAll('#menu .row').length") == 11
    game.press("Escape"); assert game.js("MENU.view") == "main"   # back to the list, then out
    game.press("Escape"); assert not game.js("menuOpen()")


def test_the_volumes_act_at_once_and_are_kept(game):
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter")
    at_row(game, "Everything")
    game.press("ArrowLeft"); game.press("ArrowLeft")
    at_row(game, "Music"); game.press("ArrowLeft")
    at_row(game, "Footsteps")
    for _ in range(5):
        game.press("ArrowLeft", 40)
    assert game.js("[opt('master'), opt('music'), opt('steps'), soundShare('Footsteps'), soundShare('Work')]") == [80, 90, 50, .5, 1]
    assert game.js("audio && [Math.round(soundOut.gain.value * 100), Math.round(musicOut.gain.value * 100)]") == [64, 72]      # (.8 of SOUND.master; .8 x .9)
    assert game.js("JSON.parse(localStorage.getItem('megastructure-options'))") == {"master": 80, "music": 90, "steps": 50}
    assert game.js("document.querySelectorAll('#menu .row.own').length") == 3
    box = game.page.locator("#menu .row.on .bar").bounding_box()                    # a bar is dragged with the mouse
    game.page.mouse.click(box["x"] + box["width"] * .8, box["y"] + 3)
    assert game.js("opt('steps')") == 80
    at_row(game, "Sound"); game.press("Enter")
    assert game.js("muted") is True
    game.press("r")                                             # this page as it came
    assert game.js("[opt('master'), opt('music'), opt('steps'), muted, localStorage.getItem('megastructure-options')]") == [100, 100, 100, False, "{}"]


def test_the_picture_and_screen_settings_do_what_they_say(game):
    game.clear_area(5)
    game.js("zoom = 3; ZOOM.to = 3")
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab")
    assert game.js(ROW) == "Zoom"
    game.press("ArrowRight", 500)
    assert game.js("zoom") == 4
    game.press("ArrowDown"); game.press("ArrowLeft")            # Sharpness: light
    assert game.js("[opt('sharp'), DPR]") == ["light", 1]
    at_row(game, "Particles"); game.press("ArrowLeft")          # none
    assert game.js("(() => { parts.length = 0; puffs.length = 0; burst(0, 0, 'hit', 6); debris(0, 0, null, 5, {dust: true}); smoke(0, 0, 8); return parts.length + puffs.length; })()") == 0
    game.press("ArrowLeft")                                     # fewer
    assert game.js("(() => { parts.length = 0; burst(0, 0, 'hit', 6); return parts.length; })()") == 2
    for name, key in (("Water shimmer", "shimmer"), ("Shake on a hard fall", "shake"), ("Smooth zoom", "glide"), ("Hearts and gains over heads", "floats")):
        at_row(game, name); game.press("Enter")
        assert game.js(f"opt('{key}')") is False
    game.js("fallQuake = {t0: performance.now(), amp: 5}; floats.push({x: 0, y: 0, text: '-1', color: '#fff', t: performance.now() / 1000})")
    game.sleep(200)
    assert game.js("[fallShake(performance.now()), floats.length]") == [0, 0]
    game.press("Tab"); game.press("Tab")                        # Screen (past Shaders)
    for name, key in (("Speech bubbles", "bubbles"), ("Names over heads", "names"), ("Key hints", "hints"), ("Mouse tips", "tips")):
        at_row(game, name); game.press("Enter")
        assert game.js(f"opt('{key}')") is False
    assert game.js("[document.body.classList.contains('nohints'), document.body.classList.contains('notips'), getComputedStyle($('actions')).display]") == [True, True, "none"]
    at_row(game, "A chat line stays"); game.press("ArrowRight")
    assert game.js("opt('chat')") == 30
    at_row(game, "Goals card"); game.press("Enter")
    assert game.js("[goalsOff, localStorage.getItem('megastructure-goals-off')]") == [False, "0"]
    at_row(game, "Coordinates"); game.press("Enter")
    assert game.js("[DEBUG.coords, localStorage.getItem('megastructure-coords')]") == [True, "1"]
    game.press("Escape"); game.press("Escape")
    game.act("say", text="hello there")
    game.sleep(700)
    assert game.js("bubbles.length") == 0                       # nothing over your head
    assert game.js("$('xyz').textContent").startswith("X ")
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); DEBUG.coords = false; localStorage.clear()")


def test_a_key_can_be_changed_and_the_game_follows(game):
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab"); game.press("Tab"); game.press("Tab"); game.press("Tab")
    at_row(game, "Inventory"); game.press("Enter")
    assert game.js("document.querySelector('#menu .row.on .ctl').textContent") == "press a key"
    game.press("w")                                             # a key of the game's own: refused, and said
    assert game.js("keyOf('bag')") == "i" and "another one" in game.js("document.querySelector('#menu .hf').textContent")
    game.press("Enter"); game.press("p")
    assert game.js("[keyOf('bag'), document.querySelector('#menu .row.on kbd').textContent]") == ["p", "P"]
    at_row(game, "Craft"); game.press("Enter"); game.press("p")   # a key another action has: they change places
    assert game.js("[keyOf('craft'), keyOf('bag')]") == ["p", "c"]
    at_row(game, "Pick up"); game.press("Enter"); game.press("j")
    game.press("Escape"); game.press("Escape")
    game.press("p"); assert game.js("isOpen('craft')")
    game.press("p"); assert not game.js("isOpen('craft')")
    game.press("c"); assert game.js("isOpen('bag')")
    game.press("c"); assert not game.js("isOpen('bag')")
    game.press("i"); assert not game.js("isOpen('bag')")        # its old key does nothing now
    game.give(plank=1)
    game.act("drop", item="plank", n=1)
    game.wait("groundItems.length > 0")
    game.sleep(300)
    assert "J" in game.js("$('actions').textContent")           # the hint names the new key
    game.press("f"); game.sleep(400); assert game.inv("plank") == 0
    game.press("j"); game.wait("meObs.self.inventory.plank === 1")
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter")      # the settings open on the page you left
    assert game.js(ROW) == "Sprint"
    game.press("ArrowRight")                                    # Shift once
    assert game.js("opt('sprint')") == "toggle"
    game.press("r")
    assert game.js("[opt('sprint'), JSON.stringify(opt('keys'))]") == ["hold", "{}"]
    game.js("setOpt('sprint', 'toggle')")
    game.press("Escape"); game.press("Escape")
    game.press("Shift"); assert game.js("runKey") is True       # pressed and let go: still running
    game.press("Shift"); assert game.js("runKey") is False
    game.js("setOpt('sprint', 'hold'); localStorage.clear()")


def test_a_shader_repaints_the_picture_and_off_is_as_before(game):
    assert game.js("[opt('shader'), !!Shader.el, Sun.shades()]") == ["off", False, False]            # nothing of it until asked for
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab"); game.press("Tab")
    assert game.js("[...document.querySelectorAll('#menu .row .name')].map((e) => e.textContent)") == ["Shader", "Strength", "Glow", "Shadows", "Water reflections", "Cloud shadows", "Dark corners"]
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
    assert 1 < d < 90 and lit > 40, (d, lit)                    # the same picture, graded: not the plain one, not a blank or a white-out
    game.js("setOpt('shaderk', 0); setOpt('clouds', false); window.shot = null; requestAnimationFrame(() => requestAnimationFrame(() => { window.shot = " + look + "; }))")
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
    game.js("setOpt('shader', 'natural')")
    game.sleep(800)
    on = [game.js(lit, r) for r in (west, east, pond)]
    assert on[0] < plain[0] - 3 and abs(on[1] - plain[1]) < 1.5, (plain, on)      # its shadow lies to the west, none to the east
    assert game.js("Sun.shades()") is True                      # (and the pale mark under you is not drawn: you have a shadow)
    game.js("setOpt('reflect', false)"); game.sleep(600)        # the tree is in the water under it: the water without it is not the same
    bare = game.js(lit, pond)
    assert abs(on[2] - bare) > 1 and abs(game.js(lit, pond) - bare) < .3, (on, bare)
    game.rpc("dev_time", phase=.7)                              # evening: the other side
    game.sleep(1200)
    game.js("setOpt('shader', 'off')"); game.sleep(600)
    plain = [game.js(lit, r) for r in (west, east)]
    game.js("setOpt('shader', 'natural')"); game.sleep(800)
    on = [game.js(lit, r) for r in (west, east)]
    assert on[1] < plain[1] - 3 and abs(on[0] - plain[0]) < 1.5, (plain, on)
    game.js("setOpt('shadows', false)"); game.sleep(600)
    assert game.js(lit, east) > on[1] + 3                       # (the hour's light moves on meanwhile: lighter than shaded, not equal to before)
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")


def test_nothing_is_reflected_in_water_that_a_hill_hides(game):
    # "player reflection is visible even if player is standing on a mountain, because there's water under it"
    game.clear_area(8)
    game.stamp(-3, -3, ["~~~~~~~", "~~~~~~~", ".......", ".......", "......."], levels=["0000000", "0000000", "5555555", "5555555", "5555555"])
    game.rpc("dev_time", phase=.3)
    game.js("setOpt('shimmer', false); setOpt('shadows', false); setOpt('reflect', false); setOpt('shader', 'natural')")
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
    game.js("setOpt('reflect', true)"); game.sleep(800)
    assert game.js(grab, box) == off
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")
