"""The first screen's background (web/js/title_scene.js): an island of the page's own, with its little life."""

CAST = "[...ents.values()].map((p) => [p.e.kind, p.e.name || '', p.e.x - (-8000), p.e.y - (-8000), !!p.e.sail, !!p.e.swim])"
ASKED = "window.__asked"


def open_page(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("window.__asked = []; const W = window.WebSocket; window.WebSocket = function (...a) { const s = new W(...a), send = s.send.bind(s);"
                         " s.send = (m) => { try { window.__asked.push(JSON.parse(m).op); } catch (e) {} return send(m); }; return s; }; window.WebSocket.prototype = W.prototype;")
    page.goto(server)
    return page, errors


def test_the_first_screen_shows_an_island_of_its_own_at_once(browser, server):
    """Behind the first screen there was the world, once the server had sent it (in the demo, once Python had
    started: many seconds of an empty screen). There is an island that is part of the page: it shows as soon as the
    pictures are loaded, asks the server for no land, and has its own life: its people go about, Pip sails, Lou swims
    the pond, hens in their pen; the hours pass; the view goes after someone."""
    page, errors = open_page(browser, server)
    page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on && !arrivingNow", timeout=10000)
    assert page.evaluate("blocks.size") >= 6 and page.evaluate("[...blocks.values()].every((b) => b.bx < -200 && b.by < -200)")      # its land: far from where anyone lives
    cast = page.evaluate(CAST)
    names = sorted(c[1] for c in cast if c[0] == "agent")
    assert names == ["Lou", "Mira", "Nell", "Pip", "Tobi"] and sorted(c[0] for c in cast if c[0] != "agent") == ["chick", "chicken", "chicken", "chicken", "cow", "cow"]
    page.wait_for_function("document.body.classList.contains('scene') && HdLook.live", timeout=10000)          # (drawn by the HD look, hd.js: its own canvas)
    look = "(() => { const c = HdLook.read(0, 0, cv.width, cv.height).data, kinds = new Set(); for (let i = 0; i < c.length; i += 4 * 97) kinds.add(c[i] >> 3 << 10 | c[i + 1] >> 3 << 5 | c[i + 2] >> 3); return kinds.size; })()"
    assert page.evaluate(look) > 40                                 # drawn: land, water, things (not one colour)
    # (the dice are thrown anew at each visit, and in one of them Pip is coming ashore: for what follows, a play that is known)
    page.evaluate("(() => { TitleScene.stop(); document.getElementById('joinbox').style.display = ''; TitleScene.start(3); })()")
    page.wait_for_function("TitleScene.on && !arrivingNow", timeout=10000)
    cast = page.evaluate(CAST)
    start, cam0, phase0 = {c[1] or f"{c[0]}{i}": c[2:4] for i, c in enumerate(cast)}, page.evaluate("[cam.x, cam.y]"), page.evaluate("clock.phase")
    page.wait_for_timeout(4000)
    cast = page.evaluate(CAST)
    now = {c[1] or f"{c[0]}{i}": c[2:4] for i, c in enumerate(cast)}
    assert now["Pip"] != start["Pip"] and sum(now[n] != start[n] for n in ("Mira", "Tobi", "Nell")) >= 2       # the boat goes on; its people go about
    pip, lou = [c for c in cast if c[1] == "Pip"][0], [c for c in cast if c[1] == "Lou"][0]
    wet = "([x, y]) => { const t = tile(-8000 + x, -8000 + y); return !!t && '~=()'.includes(t[1]); }"
    assert pip[4] and lou[5] and page.evaluate(wet, pip[2:4]) and page.evaluate(wet, lou[2:4])           # the boat and the duck are on water
    pen = page.evaluate("TITLE_MAP.cast.pen")
    assert all(pen[0] <= c[2] <= pen[2] and pen[1] <= c[3] <= pen[3] for c in cast if c[0] in ("chicken", "chick"))      # the hens keep to their pen
    assert page.evaluate("clock.phase") > phase0 and page.evaluate("[cam.x, cam.y]") != cam0             # the hours pass; the view goes after someone
    assert set(page.evaluate(ASKED)) <= {"recipes", "agents", "metrics"}, page.evaluate(ASKED)           # the server was asked for no land, and told of nothing watched
    # its sounds are the game's own, heard from the middle of the view and kept under the music: a voice there at
    # half what it is in the game, anything else at a quarter, less from further, nothing from out of hearing
    vols = page.evaluate("[heard(cam.x, cam.y, 12, 'People').vol, heard(cam.x + 6, cam.y, 12, 'Work').vol, heard(cam.x + 20, cam.y, 12, 'Work'), SOUND.scene.People, SOUND.scene.rest, SOUND.music]")
    assert vols[0] == vols[3] and abs(vols[1] - vols[4] / 2) < 1e-9 and vols[2] is None and vols[4] < vols[3] < vols[5], vols
    assert page.evaluate("document.querySelector('#joinbox .logo') !== null && titleOpen()")
    page.close()
    assert not errors, errors


def test_waking_up_leaves_the_island_for_the_world(game):
    """A player who wakes up: the island's land and its cast are gone, the land round them is the world's."""
    assert game.js("!TitleScene.on && typeof TITLE_MAP === 'object'")
    x, y = game.pos()
    assert game.js("[...blocks.values()].every((b) => b.bx > -200 && b.by > -200)") and game.js(f"!!tile({x}, {y})")
    assert not any(c[1] in ("Mira", "Tobi", "Pip", "Lou", "Nell") for c in game.js("[...ents.values()].map((p) => [p.e.kind, p.e.name || ''])"))
    assert game.js("bubbles.every((b) => !['Mira', 'Tobi', 'Pip', 'Lou', 'Nell'].includes(b.name))")           # ...and nothing they said hangs over it
    assert game.js(f"ears === null && heard({x}, {y}, 12, 'Work').vol === 1")                                 # the world is heard by you, as loud as it is


# The island's clock run by hand, a tenth of a second a step, with a seed: what each one did (never the same twice
# running), what was said, what changed on the island, and whether anyone was ever where a body cannot be
RUN = """([seed, steps]) => { TitleScene.stop(); document.getElementById('joinbox').style.display = ''; TitleScene.start(seed); clearInterval(TitleScene.S.timer);
  const S = TitleScene.S, did = {}, said = [], shouts = [], wrong = [], was = new Map(), oe = window.onEvent, push = bubbles.push.bind(bubbles); let tiles = 0, fire = 0, ashore = 0;
  window.onEvent = (e) => { if (e.type === 'tile') tiles++; return oe(e); };
  bubbles.push = (b) => { (b.shout ? shouts : said).push(b.name + ': ' + b.text); if (b.shout && shouts.length === 1) shouts.first = S.tick; return push(b); };
  for (let i = 0; i < steps; i++) { TitleScene.step(); bubbles.length = 0;
    for (const p of S.people) { const l = did[p.name] || (did[p.name] = []), t = S.at(p.x, p.y), w = was.get(p) || [p.x, p.y];
      if (l[l.length - 1] !== p.last) l.push(p.last);
      const water = !!t && wet(t[1]) && GROUND.has(t[0]), ground = !!t && WALKABLE_GROUND.has(t[1]) && !SOLID.has(t[0]) && !(p.still && (t[0] === '+' || t[1] === 'n'));
      if (!(p.sail || p.swim ? water : ground) || Math.abs(p.x - w[0]) + Math.abs(p.y - w[1]) > 1) wrong.push([i, p.name, p.x, p.y, t && t.slice(0, 2)]);
      was.set(p, [p.x, p.y]); }
    fire = Math.max(fire, S.people.filter((p) => p.last === 'fire' && p.still).length); if (!S.people[2].sail) ashore++; }
  window.onEvent = oe; bubbles.push = push;
  const things = (c) => [...blocks.values()].reduce((n, b) => n + [...b.objs.values()].filter((q) => q === c).length, 0);
  return {did, said, shouts: [...shouts], first: shouts.first, wrong, tiles, fire, ashore, trees: things('T'), stumps: things('t'), boat: things('V')}; }"""


def test_the_islands_people_choose_what_they_do(browser, server):
    """Each of them did one thing over and over (Mira to her field and back, Tobi at one tree, the boat and the duck
    round and round). They choose (web/js/title_cast.js): over a day and a half each does many kinds of things and
    never the same twice running, they speak to each other, what they do changes the island (a tree is felled and
    grows back, wheat is watered, pulled and sown), in the evening they come round the fire, Pip ties his boat up and
    takes it out again; nobody is ever on water on foot, in a wall, or a tile further than a step, nor stands
    in a doorway or indoors (under the roof they are not seen). And another visit is another play."""
    page, errors = open_page(browser, server)
    page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on && !arrivingNow", timeout=10000)
    trees = page.evaluate("[...blocks.values()].reduce((n, b) => n + [...b.objs.values()].filter((q) => q === 'T').length, 0)")
    one, two = page.evaluate(RUN, [5, 3000]), page.evaluate(RUN, [6, 3000])
    for run in (one, two):
        did = run["did"]
        assert not run["wrong"], run["wrong"][:5]
        assert all(len(set(did[n])) >= 7 for n in ("Mira", "Tobi", "Nell")) and len(set(did["Pip"])) >= 4, did       # many kinds of things
        assert all(a != b for n in ("Mira", "Tobi", "Nell", "Pip") for a, b in zip(did[n], did[n][1:])), did        # never the same twice running
        assert {"harvest", "water"} <= set(did["Mira"]) and {"chop", "mine"} <= set(did["Tobi"]) and "sail" in did["Pip"]
        assert len(run["said"]) >= 20 and len(set(run["said"])) >= 15, run["said"]                                    # they speak, and not the one line
        # now and then one shouts across the island and is shouted back at: the first within ten seconds, never the same twice running
        assert len(run["shouts"]) >= 8 and run["first"] <= 100, run["shouts"]
        assert all(a != b for a, b in zip(run["shouts"][::2], run["shouts"][2::2])), run["shouts"]
        assert run["tiles"] >= 60 and run["fire"] >= 2 and 300 < run["ashore"] < 2700, run                         # the island changes; the fire; the boat out and in
        assert run["trees"] + run["stumps"] == trees and 0 < run["trees"] and run["boat"] <= 1, run                # a felled tree is a stump, then a tree again
    assert one["did"] != two["did"] and one["said"] != two["said"]                                                # another visit, another play
    page.close()
    assert not errors, errors



# every bubble drawn, and the boxes of what the first screen writes (title_scene.js `hides`): [[x, y, w, h] of each bubble], [boxes], bubbles in all
SPOKEN = """(() => { TitleScene.hides(0, 0, 1, 1); return {drawn: bubbles.filter((b) => b.at).map((b) => [b.at[0], b.at[1], b.w, b.h, b.name]), boxes: TitleScene.boxes.map((b) => [b.x, b.y, b.w, b.h]), all: bubbles.length}; })()"""


def test_nobody_s_words_or_name_are_drawn_under_the_name_of_the_game_its_line_or_its_window(browser, server):
    """The fifth audit, upright phone: the line "Step aside. No, further." lay across a bubble cut off by the logo, a
    scrap of another stuck out under it. Everybody speaks at once here, eye after eye: what would lie on the logo, the
    line or the window is not drawn (nor their name there); the others are, and none of them touches those boxes."""
    for w, h in ((390, 844), (1280, 760)):
        page = browser.new_page(viewport={"width": w, "height": h})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(server)
        page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on && document.body.classList.contains('scene')", timeout=15000)
        drawn = hidden = 0
        for who in range(5):                                     # the eye on each of them in turn: they come under every box
            page.evaluate("""(i) => { const S = TitleScene.S, p = S.people[i % S.people.length]; cam.x = camT.x = S.ox + p.x; cam.y = camT.y = S.oy + p.y; S.till = S.tick + 1e6; S.eye = p; bubbles.length = 0;
              S.people.forEach((q) => S.say(q, 'Did you water the wheat today?')); window.__f = 0; return 1; }""", who)
            page.wait_for_function("++window.__f > 12", polling="raf")
            s = page.evaluate(SPOKEN)
            assert len(s["boxes"]) == 3, s["boxes"]
            for x, y, bw, bh, name in s["drawn"]:
                assert not any(x < b[0] + b[2] and b[0] < x + bw and y - 22 < b[1] + b[3] and b[1] < y + bh + 6 for b in s["boxes"]), (w, name, [x, y, bw, bh], s["boxes"])     # (its name's tab is over it, its tail under it)
            drawn += len(s["drawn"]); hidden += s["all"] - len(s["drawn"])
        assert drawn + hidden >= 20, (w, drawn, hidden)          # (how many are on the screen and clear of the boxes is the island's own play: one, or a dozen)
        logo = page.evaluate("(() => { const b = TitleScene.boxes[0]; return [TitleScene.hides(b.x + 10, b.y + 10, 40, 20), TitleScene.hides(-500, -500, 10, 10)]; })()")
        assert logo == [True, False] and not errors, errors
        page.close()


def test_over_a_terrace_the_islands_eye_cuts_no_hole_in_the_hill(browser, server):
    """The owner's picture: a flat black tile beside a tree on a terrace of the first screen, a lit strip at its foot.
    The island's eye is nobody (hd.js: a free eye, its level the meadow's); over a terrace the search for "your space"
    found it under the land and the x-ray window opened there: the window's dark back and its lit near edge. A free
    eye has no space of its own and no window, wherever the view goes."""
    page, errors = open_page(browser, server)
    page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on && document.body.classList.contains('scene') && HdLook.live && !HdLook.busy", timeout=15000)
    at = page.evaluate("""(() => { const S = TitleScene.S, [x0, y0, x1, y1] = S.C.view; clearInterval(S.timer); for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (levelAt(S.ox + x, S.oy + y) >= 2) {
      cam.x = camT.x = S.ox + x; cam.y = camT.y = S.oy + y; window.__b = HdLook.builds; return [x, y, levelAt(S.ox + x, S.oy + y), HdLook.eye().z]; } return null; })()""")
    assert at and at[2] > at[3] + 1, at                              # (the eye's level under the terrace's top)
    page.wait_for_function("HdLook.builds > window.__b && !HdLook.busy", timeout=10000)
    page.wait_for_function("(window.__f = (window.__f || 0) + 1) > 8", polling="raf")     # (the window eases open over frames)
    assert page.evaluate("[HdLook.win.n, HdLook.win.a]") == [0, 0], at
    page.close()
    assert not errors, errors


# the share of the land's picture that has land drawn on it
LAND = """(() => { const c = HdView.pic, g = document.createElement('canvas').getContext('2d'); g.canvas.width = c.width; g.canvas.height = c.height; g.drawImage(c, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n / (c.width * c.height); })()"""


def test_a_lost_gpu_context_gives_the_land_back(browser, server):
    """"Sometimes the map disappears": a phone takes a page's WebGL contexts back (its tab put away, its GPU's memory
    wanted). The land's own and the sky's were never asked for again: the land gone for good, the sky and the names
    left. Both are made again: the land comes back whole, every face with its paint."""
    page, errors = open_page(browser, server)
    page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on && document.body.classList.contains('scene') && HdLook.live && !HdLook.busy", timeout=15000)
    assert page.evaluate(LAND) > .5
    page.evaluate("[HdView.pic.getContext('webgl2'), VoxGL.gl].forEach((g) => g.getExtension('WEBGL_lose_context').loseContext())")
    page.wait_for_function(f"HdLook.live && !HdView.pic.getContext('webgl2').isContextLost() && VoxGL.gl && !VoxGL.gl.isContextLost() && {LAND} > .5 && HdLook.raw() === 0", timeout=5000)
    page.close()
    assert not errors, errors
