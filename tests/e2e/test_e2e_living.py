"""Living: eating, fighting animals (on the move), deaths, beds, fire."""

import pytest


def test_eating_takes_three_bites_and_stops_when_full(game):
    game.give(bread=2)
    game.rpc("dev_needs", hunger=8)
    hunger0 = game.server()["hunger"]
    game.hold_item("bread")
    game.press("e", 0)
    game.wait("myAside && myAside.tool === 'eat' && biteIcon('bread', 1) !== null", 3000)   # (asked as it begins: 450 ms on, on a runner, the 0.9 s meal was over)
    game.until_world(lambda s: s["hunger"] == hunger0 + 10)    # (until the world has it: the meal's end, then its word)
    assert game.server()["hunger"] == hunger0 + 10            # one bread: five pieces
    game.rpc("dev_needs", hunger=20)
    while game.server()["hunger"] < 20 and game.inv("bread"):
        game.press("e", 1300)
    if game.inv("bread"):
        game.press("e", 600)
        assert "full" in game.toast()


def test_eating_your_hands_are_full(game):
    """While you eat you can walk, nothing else: X on a tree beside you asks for nothing and shows no swing, F
    picks nothing up, and the tree stands; once it is eaten the same keys work. (A player chopped and punched with
    the food at his mouth, and the meal stopped for it.)"""
    game.clear_area(6)
    game.stamp(1, 0, ["T"])
    game.give(bread=1, stone=1)
    game.rpc("dev_needs", hunger=8)
    game.act("drop", item="stone", n=1)                       # something to pick up, under you
    game.settle("groundItems.length > 0")                      # (on the ground as the page sees it: not 300 ms)
    game.face(1, 0)
    game.hold_item("bread")
    game.js("(() => { window.__asked = []; const o = rpc; rpc = function (op, d) { if (op === 'act') __asked.push(d.tool); return o(op, d); }; return 1; })()")
    game.js("(() => { window.__keys = []; addEventListener('keydown', (e) => __keys.push([e.key, eating()]), true); return 1; })()")
    game.press("e", 0)
    # X and F (and a dig asked past the page) as the meal begins, in the page's own frame: the meal is 0.9 s, and each key
    # sent from here, or each wait for the page, was a slow runner's frame or two (the meal was over before X, both pressed with free hands)
    game.js("""() => new Promise((ok) => { const go = () => { if (!(myAside && myAside.tool === 'eat')) return requestAnimationFrame(go);
      selectItem(null);
      for (const [key, code] of [['x', 'KeyX'], ['f', 'KeyF']]) for (const type of ['keydown', 'keyup']) dispatchEvent(new KeyboardEvent(type, {key, code, bubbles: true}));
      window.__dig = rpc('act', {tool: 'dig', args: {dir: 'E'}});
      ok(1); }; go(); })""")
    assert game.js("__keys.filter(([k]) => k === 'x' || k === 'f')") == [["x", True], ["f", True]]   # both pressed while eating
    # (the server's own rule, asked past the page, in that frame too: asked from here, a busy runner's two calls later, the
    # meal was over and the tree was chopped)
    assert game.js("() => __dig").get("error") == "hands_full"
    game.frames(1)
    assert game.js("__asked") == ["eat", "dig"]                                       # nothing asked for but the meal (and the dig asked past the page)
    assert game.js("!ents.get('agent' + myId).swing && !myAction")                   # no punch shown
    assert game.inv("stone") == 0 and game.js(f"combAt({game.pos()[0] + 1}, {game.pos()[1]})") == "T"
    game.wait("!eating()", 4000)
    assert game.server()["hunger"] == 8 + 10                                        # ...and the meal was not stopped for any of it
    game.press("f", 400)
    assert game.inv("stone") == 1                                                    # eaten: the hands are free
    game.press("x", 200)
    assert game.js("__asked") == ["eat", "dig", "pick_up", "dig"] and not game.errors   # (the first dig: the one asked past the page)


SETTLED = "!walking && !pred && (() => { const p = ents.get('agent' + myId); return !!p && p.e.x === Math.round(p.x) && p.e.y === Math.round(p.y); })()"   # (the walk over, and the world come to where you are)


def test_you_eat_while_you_walk(game):
    """Eating is done with the hands: E on the move doesn't stop you, the bites show on a walking you (to others
    too), and setting off doesn't end a meal begun standing. (You stood still for every bite.)"""
    game.clear_area(12)
    game.give(bread=3)
    game.rpc("dev_needs", hunger=8)
    game.hold_item("bread")
    x0 = game.pos()[0]
    game.start_recording()
    # (each step waits on what the game shows, not on the machine's time: sleeps of 250, 900, 600, 700 and 500 ms were
    # 3 runs in 23 red on frames of 67 and 100 ms, #47)
    game.page.keyboard.down("d")
    game.wait(f"walking !== null && myPos().x > {x0}", 3000)                                  # (set out: on the move)
    game.press("e", 0)
    game.wait("(() => { const e = ents.get('agent' + myId).e; return e.doing === 'walk' && e.eats === 'bread'; })()", 3000)   # as others are told (when the world has said it)
    assert game.js("walking !== null") and game.js("myAside && myAside.tool") == "eat"       # walking, and the bites showing
    game.wait("meObs.self.hunger === 18 && (meObs.self.inventory.bread || 0) === 2", 8000)   # (walking on till the bread is eaten)
    game.page.keyboard.up("d")
    rec = game.recording()
    game.wait(f"{SETTLED}", 8000)
    assert game.server()["hunger"] == 8 + 10 and game.inv("bread") == 2                 # the bread is eaten...
    stops, i0 = [], 0                                                                       # ...and you never stood still for it
    for i in range(1, len(rec)):
        if abs(rec[i][1] - rec[i0][1]) > 1e-6:
            if i - i0 > 1 and rec[i][0] - rec[i0][0] > 80 and rec[i0][0] > 300:   # (a frame drawn where the last one was: one frame apart is a slow machine's frame, 100 to 200 ms on a runner, not a stop)
                stops.append(round(rec[i][0] - rec[i0][0]))
            i0 = i
    # (and on at the eating pace at the least, the whole time it walked: by the frames' own time, the game's. It was 5 tiles
    # from where you set out: the key's time down holds a wait for the world's word, a runner's own time, and one walked 4)
    moving = [r for a, r in zip(rec, rec[1:]) if abs(r[1] - a[1]) > 1e-6]
    least = (moving[-1][0] - moving[0][0]) / 1000 * game.js("RULES.pace.walk / RULES.eat_pace") - 1 if moving else 1
    assert not stops and game.pos()[0] - x0 >= max(1, least), (stops, game.pos()[0] - x0, round(least, 2))     # (slower while you chew: EAT_PACE)
    game.rpc("dev_needs", hunger=8)
    game.press("e", 0)                                                                      # a meal begun standing...
    game.wait("myAside && myAside.tool === 'eat'")
    game.page.keyboard.down("a")
    game.wait("walking !== null && !!myAside && myAside.tool === 'eat'", 3000)               # ...goes on as you set off (asked at once: the meal is 0.9 s)
    game.wait("(meObs.self.inventory.bread || 0) === 1", 8000)                              # (walking on till it is eaten)
    game.page.keyboard.up("a")
    game.wait(f"{SETTLED}", 8000)
    assert game.inv("bread") == 1 and not game.errors


def test_hit_a_chicken_while_walking_and_it_runs(game):
    hen = game.spawn("chicken", 2, -1, still=10 ** 6)
    game.wait(f"ents.has('chicken{hen}')", 4000)
    x0, y0 = game.pos()
    game.page.keyboard.down("d")
    game.wait(f"walking !== null && ents.get('agent' + myId).x >= {x0 + .25}", 4000)   # (on the move: not 150 ms)
    game.press("x", 0)                                       # X on the hen: a punch, and no stopping
    game.wait(f"ents.get('chicken{hen}').e.hp < 10", 4000)  # (until it is hit: not 250 ms)
    still_walking = game.js("walking !== null")
    game.page.keyboard.up("d")
    assert still_walking
    # it was hit, and ran off: three tiles and more from where it stood. (It was "four from where you end up": it runs
    # from where it was hit, you walk on beside it for a moment, and on a busy machine that moment was a tile longer.
    # Then it was looked at after a second and a half: by itself, on a machine with nothing else to do, the hen was two
    # tiles off by then, every time; in the whole run, slower, three. It is waited for.)
    far = f"(() => {{ const q = ents.get('chicken{hen}'); return !!q && q.e.hp < 10 && Math.abs(q.tx - {x0 + 2}) + Math.abs(q.ty - {y0 - 1}) >= 3; }})()"
    try:
        game.wait(far, 6000)
    except Exception:
        raise AssertionError((game.js(f"(() => {{ const q = ents.get('chicken{hen}'); return q ? [q.tx, q.ty, q.e.hp] : null; }})()"), x0, y0))


def test_killing_leaves_a_poof_and_drops(game):
    game.lucky()
    game.give(sword=1)
    game.hold_item("sword")
    hen = game.spawn("chicken", 1, 0, still=10 ** 6)
    game.wait(f"ents.has('chicken{hen}')", 4000)
    game.face(1, 0)
    game.press("x", 300)
    game.settle(f"!ents.has('chicken{hen}')")
    assert game.js(f"!ents.has('chicken{hen}')") and game.js("puffs.length + dying.length > 0")
    game.until_world(lambda s: s["inventory"].get("meat", 0) >= 1)      # (dropped, then drawn into your bag: not 2 s)
    assert game.inv("meat") >= 1                              # meat (and an egg) dropped, then drawn into your bag


def test_dying_wakes_you_by_your_bed(game):
    game.give(bed=1)
    game.hold_item("bed")
    game.face(1, 0)
    game.press("e", 800)
    game.press("0", 100)
    game.press("e", 1600)                                # lie down: it becomes where you wake up
    assert game.server()["spawn"]
    bed = game.server()["spawn"]
    game.rpc("dev_teleport", x=bed[0] + 30, y=bed[1]); game.arrive()
    game.rpc("dev_damage", n=500)
    game.until_world(lambda s: s["deaths"] == 1)
    game.settle("$('death').style.display === 'block'")
    s = game.server()
    assert s["deaths"] == 1 and abs(s["x"] - bed[0]) + abs(s["y"] - bed[1]) <= 3
    assert game.js("$('death').style.display") == "block" and "bed" in game.js("$('deathwake').textContent")   # the death screen
    game.sleep(3000)                                         # it waits for you... (a window in which nothing must happen: so at any frame's length)
    assert game.js("$('death').style.display") == "block"
    game.press("q", 700)                                     # ...until a key
    assert game.js("$('death').style.display") == "none"


def test_fire_burns_to_ash_and_ash_grows_back(game):
    game.give(torch=1)
    game.stamp(1, 0, ["#"])
    game.hold_item("torch")
    game.face(1, 0)
    assert "Set on fire" in game.actions()
    game.press("e", 800)
    assert game.js("fireAt.length") >= 1
    game.rpc("dev_skip", seconds=20)
    x, y = game.pos()
    game.settle(f"gndAt({x + 1}, {y}) === \"'\"", timeout=8000)    # (until the page has the ash)
    assert game.js(f"gndAt({x + 1}, {y})") == "'"            # ash
    game.rpc("dev_skip", seconds=250)
    game.settle(f"gndAt({x + 1}, {y}) === '.'", timeout=8000)
    assert game.js(f"gndAt({x + 1}, {y})") == "."


def test_mining_ore_sends_orbs_and_fills_the_bar(game):
    game.give(pickaxe=1)
    game.stamp(1, 0, ["*"])
    game.hold_item("pickaxe")
    game.face(1, 0)
    game.press("x", 0)
    game.wait("orbs.length > 0", 6000)                        # orbs burst out of the rock...
    game.wait("orbs.length === 0", 6000)                      # ...and fly into you
    game.until_world(lambda s: s["xp"] == 4)
    game.settle("meObs.self.xp === 4")                       # (the bar drawn from the page's own word on you)
    assert game.server()["xp"] == 4
    w, fill = game.js("$('xpbar').dataset.sig").split(",")[:2]
    assert int(fill) / int(w) > .5                           # 4 of 7 to the first level


def test_loot_next_to_you_comes_to_you(game):
    game.lucky()                                              # (what a hen leaves is by chance: here, all of it. This test was missed when it became so, and failed four times in ten)
    game.rpc("dev_creatures", clear=6)
    hen = game.spawn("chicken", 1, 1, still=10 ** 6)
    game.give(sword=1)
    game.hold_item("sword")
    game.wait(f"ents.has('chicken{hen}')", 4000)
    x, y = game.pos()
    game.js(f"act('attack', {{target: {hen}, with: 'sword'}})")
    game.wait("magnets.length > 0", 4000)                     # the meat and egg slide over
    game.until_world(lambda s: s["inventory"].get("meat", 0) == 1)
    game.still()
    assert game.inv("meat") == 1 and game.pos() == (x, y)


def test_ten_hearts_and_ten_pieces_in_halves_and_no_sprint_when_hungry(game):
    """Health is 20 half hearts and food 20 half pieces (they were 0 to 100): the bar shows them a half at a time, a
    blow is said in hearts, and with three pieces of food or fewer the Shift key does not sprint."""
    assert game.js("[HP_MAX, FOOD_MAX, SPRINT_FOOD]") == [20, 20, 6]
    game.clear_area(12)                                     # (a meadow to run on: the walk ran into what lay east and ended, walking null)
    game.rpc("dev_needs", hp=13, hunger=7)
    game.settle("meObs.self.hp === 13 && meObs.self.hunger === 7")   # (the bars drawn from the page's word on you: not 900 ms)
    lit = """(id) => { const c = $(id), g = c.getContext('2d'), n = c.width / 99;        // each icon: 2 as the first (full), 0 as the last (empty), 1 neither
      const px = (i) => g.getImageData(i * 10 * n, 0, 9 * n, c.height).data.join(), full = px(0), none = px(9);
      return [...Array(10)].map((_, i) => px(i) === full ? 2 : px(i) === none ? 0 : 1); }"""
    assert game.js(lit, "hearts") == [2, 2, 2, 2, 2, 2, 1, 0, 0, 0]              # six hearts and a half
    assert game.js(lit, "foods") == [2, 2, 2, 1, 0, 0, 0, 0, 0, 0]               # three pieces and a half
    assert game.js("$('status').textContent") == ""
    game.page.keyboard.down("Shift")
    game.page.keyboard.down("d")
    game.settle("!!walking && walking.run === true")
    assert game.js("walking && walking.run") is True                             # fed enough: a sprint
    game.rpc("dev_needs", hunger=6)
    game.settle("!!walking && walking.run === false && $('status').textContent.includes('sprint')")
    assert game.js("walking && walking.run") is False and "sprint" in game.js("$('status').textContent")   # ...and no more, the keys still held
    game.page.keyboard.up("d")
    game.page.keyboard.up("Shift")
    game.rpc("dev_needs", hunger=0)
    game.settle("$('status').textContent.includes('Starving')")
    assert "Starving" in game.js("$('status').textContent")


def test_who_stands_far_over_you_is_not_on_your_tile(game):
    """"i shouldn't be able to select the tusker here !": he was in a tunnel, a tusker on the mountain twenty layers
    over it, and the tile he faced had it: "Punch tusker". Who is on a tile was asked of the map alone. It is who
    stands there near your own height, as far as a hand reaches up or down."""
    game.clear_area(8)
    x, y = game.pos()
    game.stamp(1, 0, ["."], levels=["9"])                     # a pillar nine layers high east of you, a hen on it
    game.spawn("chicken", 1, 0, still=600)
    game.wait(f"[...ents.values()].some((o) => o.e && o.e.kind === 'chicken' && o.tx === {x + 1} && o.ty === {y} && o.e.z === 9)", 8000)
    game.face(1, 0)
    assert game.js(f"[!!entityAt({{x: {x + 1}, y: {y}}}), JSON.stringify(facingIntent(true) || {{}}).includes('hicken')]") == [False, False]
    game.stamp(1, 0, ["."], levels=["2"])                     # two layers: within reach, it is there
    game.wait(f"[...ents.values()].some((o) => o.e && o.e.kind === 'chicken' && o.e.z === 2)", 8000)
    assert game.js(f"!!entityAt({{x: {x + 1}, y: {y}}})") is True
    assert not game.errors


def test_e_eats_what_you_hold_unless_what_you_face_takes_it(game):
    """No eat key: food in hand, E eats it, facing a tree all the same (the corner says "E Eat bread", nothing you
    face is marked for it); facing a cow with a carrot in hand, E feeds it; X chops the tree."""
    game.clear_area(6)
    x, y = game.pos()
    game.stamp(1, 0, ["T"])
    game.give(bread=1, carrot=1)
    game.rpc("dev_needs", hunger=8)
    game.face(1, 0)
    game.hold_item("bread")
    game.wait("$('actions').innerText.replace(/\\s+/g, ' ').includes('E Eat bread')", 3000)
    assert "E | Eat bread" in game.actions() and "Chop tree" in game.actions() and game.js("Target.cells().every((c) => c.key !== 'use')"), game.actions()   # (X's row: what X does to the tree, as ever)
    game.press("e", 0)
    game.wait("myAside && myAside.tool === 'eat'", 3000)
    game.wait("!eating()", 4000)
    assert game.inv("bread") == 0 and game.js(f"combAt({x + 1}, {y})") == "T"
    game.spawn("cow", 0, 1, still=10 ** 6)
    game.hold_item("carrot")
    game.face(0, 1)
    game.wait("facingNow(false) && facingNow(false).it.text === 'Feed cow'", 3000)
    game.press("e", 600)
    assert game.inv("carrot") == 0
    game.hold_item(None)
    game.face(1, 0)
    game.wait("facingNow(true) && facingNow(true).it.text.startsWith('Chop tree')", 3000)
    assert not game.errors
