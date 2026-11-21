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
