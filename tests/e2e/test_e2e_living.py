"""Living: eating, fighting animals (on the move), deaths, beds, fire."""


def test_eating_takes_three_bites_and_stops_when_full(game):
    game.give(bread=2)
    game.rpc("dev_needs", hunger=8)
    hunger0 = game.server()["hunger"]
    game.hold_item("bread")
    game.press("e", 0)
    game.sleep(450)
    assert game.js("myAside && myAside.tool") == "eat" and game.js("biteIcon('bread', 1) !== null")
    game.sleep(900)
    assert game.server()["hunger"] == hunger0 + 10            # one bread: five pieces
    game.rpc("dev_needs", hunger=20)
    while game.server()["hunger"] < 20 and game.inv("bread"):
        game.press("e", 1300)
    if game.inv("bread"):
        game.press("e", 600)
        assert "full" in game.toast()


def test_eating_your_hands_are_full(game):
    """While you eat you can walk, nothing else: Space on a tree beside you asks for nothing and shows no swing, F
    picks nothing up, and the tree stands; once it is eaten the same keys work. (A player chopped and punched with
    the food at his mouth, and the meal stopped for it.)"""
    game.clear_area(6)
    game.stamp(1, 0, ["T"])
    game.give(bread=1, stone=1)
    game.rpc("dev_needs", hunger=8)
    game.act("drop", item="stone", n=1)                       # something to pick up, under you
    game.sleep(300)
    game.face(1, 0)
    game.hold_item("bread")
    game.js("(() => { window.__asked = []; const o = rpc; rpc = function (op, d) { if (op === 'act') __asked.push(d.tool); return o(op, d); }; return 1; })()")
    game.press("e", 0)
    game.wait("myAside && myAside.tool === 'eat'")
    game.press("Space", 150)
    game.press("f", 150)
    assert game.js("eating()") and game.js("__asked") == ["eat"]                     # nothing asked for but the meal
    assert game.js("!ents.get('agent' + myId).swing && !myAction")                   # no punch shown
    assert game.inv("stone") == 0 and game.js(f"combAt({game.pos()[0] + 1}, {game.pos()[1]})") == "T"
    assert game.rpc("act", tool="dig", args={"dir": "E"})["error"] == "hands_full"   # (the server's own rule, asked past the page)
    game.wait("!eating()", 4000)
    assert game.server()["hunger"] == 8 + 10                                        # ...and the meal was not stopped for any of it
    game.press("f", 400)
    assert game.inv("stone") == 1                                                    # eaten: the hands are free
    game.press("Space", 200)
    assert game.js("__asked") == ["eat", "dig", "pick_up", "dig"] and not game.errors   # (the first dig: the one asked past the page)


def test_you_eat_while_you_walk(game):
    """Eating is done with the hands: E on the move doesn't stop you, the bites show on a walking you (to others
    too), and setting off doesn't end a meal begun standing. (You stood still for every bite.)"""
    game.clear_area(12)
    game.give(bread=3)
    game.rpc("dev_needs", hunger=8)
    game.hold_item("bread")
    x0 = game.pos()[0]
    game.start_recording()
    game.page.keyboard.down("d")
    game.sleep(250)
    game.press("e", 0)
    game.sleep(450)
    assert game.js("walking !== null") and game.js("myAside && myAside.tool") == "eat"       # walking, and the bites showing
    assert game.js("(() => { const e = ents.get('agent' + myId).e; return [e.doing, e.eats]; })()") == ["walk", "bread"]   # as others are told
    game.sleep(900)
    game.page.keyboard.up("d")
    rec = game.recording()
    game.sleep(600)
    assert game.server()["hunger"] == 8 + 10 and game.inv("bread") == 2                 # the bread is eaten...
    stops, i0 = [], 0                                                                       # ...and you never stood still for it
    for i in range(1, len(rec)):
        if abs(rec[i][1] - rec[i0][1]) > 1e-6:
            if rec[i][0] - rec[i0][0] > 80 and rec[i0][0] > 300:
                stops.append(round(rec[i][0] - rec[i0][0]))
            i0 = i
    assert not stops and game.pos()[0] >= x0 + 7, (stops, game.pos()[0] - x0)
    game.rpc("dev_needs", hunger=8)
    game.press("e", 250)                                                                    # a meal begun standing...
    game.page.keyboard.down("a")
    game.sleep(500)
    assert game.js("walking !== null") and game.js("myAside && myAside.tool") == "eat"       # ...goes on as you set off
    game.sleep(700)
    game.page.keyboard.up("a")
    game.sleep(500)
    assert game.inv("bread") == 1 and not game.errors


def test_hit_a_chicken_while_walking_and_it_runs(game):
    hen = game.spawn("chicken", 2, -1, still=10 ** 6)
    game.sleep(400)
    game.page.keyboard.down("d")
    game.sleep(150)
    game.press(" ", 0)                                       # Space on the hen: a punch, and no stopping
    game.sleep(250)
    still_walking = game.js("walking !== null")
    game.page.keyboard.up("d")
    assert still_walking
    game.sleep(1500)
    x, y = game.pos()
    q = game.js(f"(() => {{ const q = ents.get('chicken{hen}'); return q ? [q.tx, q.ty, q.e.hp] : null; }})()")
    assert q and q[2] < 10                                   # it was hit...
    assert abs(q[0] - x) + abs(q[1] - y) >= 4                # ...and ran off


def test_killing_leaves_a_poof_and_drops(game):
    game.lucky()
    game.give(sword=1)
    game.hold_item("sword")
    hen = game.spawn("chicken", 1, 0, still=10 ** 6)
    game.sleep(400)
    game.face(1, 0)
    game.press("Space", 300)
    game.sleep(200)
    assert game.js(f"!ents.has('chicken{hen}')") and game.js("puffs.length + dying.length > 0")
    game.sleep(800)
    game.sleep(1200)
    assert game.inv("meat") >= 1                              # meat (and an egg) dropped, then drawn into your bag


def test_dying_wakes_you_by_your_bed(game):
    game.give(bed=1)
    game.hold_item("bed")
    game.face(1, 0)
    game.press("Space", 800)
    game.press("0", 100)
    game.press("Space", 1600)                                # lie down: it becomes where you wake up
    assert game.server()["spawn"]
    bed = game.server()["spawn"]
    game.rpc("dev_teleport", x=bed[0] + 30, y=bed[1])
    game.sleep(800)
    game.rpc("dev_damage", n=500)
    game.sleep(1500)
    s = game.server()
    assert s["deaths"] == 1 and abs(s["x"] - bed[0]) + abs(s["y"] - bed[1]) <= 3
    assert game.js("$('death').style.display") == "block" and "bed" in game.js("$('deathwake').textContent")   # the death screen
    game.sleep(3000)                                         # it waits for you...
    assert game.js("$('death').style.display") == "block"
    game.press("q", 700)                                     # ...until a key
    assert game.js("$('death').style.display") == "none"


def test_fire_burns_to_ash_and_ash_grows_back(game):
    game.give(torch=1)
    game.stamp(1, 0, ["#"])
    game.hold_item("torch")
    game.face(1, 0)
    assert "Set on fire" in game.actions()
    game.press("Space", 800)
    assert game.js("fireAt.length") >= 1
    game.rpc("dev_skip", seconds=20)
    game.sleep(800)
    x, y = game.pos()
    assert game.js(f"gndAt({x + 1}, {y})") == "'"            # ash
    game.rpc("dev_skip", seconds=250)
    game.sleep(800)
    assert game.js(f"gndAt({x + 1}, {y})") == "."


def test_mining_ore_sends_orbs_and_fills_the_bar(game):
    game.give(pickaxe=1)
    game.stamp(1, 0, ["*"])
    game.hold_item("pickaxe")
    game.face(1, 0)
    game.press("Space", 0)
    game.wait("orbs.length > 0", 6000)                        # orbs burst out of the rock...
    game.wait("orbs.length === 0", 6000)                      # ...and fly into you
    game.sleep(800)
    assert game.server()["xp"] == 4
    w, fill = game.js("$('xpbar').dataset.sig").split(",")[:2]
    assert int(fill) / int(w) > .5                           # 4 of 7 to the first level


def test_loot_next_to_you_comes_to_you(game):
    game.rpc("dev_creatures", clear=6)
    hen = game.spawn("chicken", 1, 1, still=10 ** 6)
    game.give(sword=1)
    game.hold_item("sword")
    game.sleep(400)
    x, y = game.pos()
    game.js(f"act('attack', {{target: {hen}, with: 'sword'}})")
    game.wait("magnets.length > 0", 4000)                     # the meat and egg slide over
    game.sleep(600)
    assert game.inv("meat") == 1 and game.pos() == (x, y)


def test_a_drop_shows_once_not_twice(game):
    """What a creature drops hops out, lands, and only then shows as the pile: never the pile and the hopping drop at
    once (the pile was matched by its sort position, not its tile, so both were drawn)."""
    game.lucky()
    game.give(sword=1)
    game.hold_item("sword")
    game.clear_area(5)
    game.spawn("chicken", 1, 0, still=10 ** 6)
    game.sleep(500)
    game.face(1, 0)
    game.js("""(() => {                                     // count the meat icons drawn, frame by frame
      window._meat = []; window._meatY = []; let n = 0, y = null; const icon = ghostIcon('meat');
      const d0 = ctx.drawImage; ctx.drawImage = function (img, ...r) { if (img === icon) { n++; y = r[r.length - 3]; } return d0.call(this, img, ...r); };
      (function f() { window._meat.push(n); window._meatY.push(y); n = 0; y = null; if (window._meat.length < 240) requestAnimationFrame(f); })(); })()""")
    game.press("Space", 300)
    game.sleep(2500)
    counts = game.js("window._meat")
    assert max(counts) >= 1 and max(counts) == 1, counts      # it shows, and never twice in one frame
    ys = [v for v in game.js("window._meatY") if v is not None]   # and from the hop to resting on the ground, no jump
    z = game.js("zoom")
    rest = next(i for i in range(len(ys) - 6) if len(set(ys[i:i + 6])) == 1 and i > 10)   # where it lies still (the pile)
    assert abs(ys[rest] - ys[rest - 1]) <= 1, ys[rest - 6:rest + 2]   # the hop hands over to the pile without a jump


def test_several_drops_land_together_without_blinking(game):
    """A cow drops meat and milk: each hops out and lands; none blinks out before the pile shows (they hand over to
    the pile together, all at rest where they landed)."""
    game.lucky()
    game.give(sword=1)
    game.hold_item("sword")
    game.clear_area(5)
    game.spawn("cow", 1, 0, still=10 ** 6)
    game.sleep(500)
    game.face(1, 0)
    game.js("""(() => {                                     // the meat and milk icons drawn, frame by frame: how many
      window._n = []; let n = 0; const icons = [ghostIcon('meat'), ghostIcon('milk')];
      const d0 = ctx.drawImage; ctx.drawImage = function (img, ...r) { if (icons.includes(img)) n++; return d0.call(this, img, ...r); };
      window._d = [];
      (function f() { window._n.push(n); window._d.push([n, loot.map(l => l.name + (l.done ? '*' : '')).join(','), JSON.stringify(groundItems.map(g => Object.keys(g[2])))]); n = 0; if (window._n.length < 360) requestAnimationFrame(f); })(); })()""")
    for _ in range(4):                                       # (a cow takes a few hits)
        game.press("Space", 700)
    game.sleep(2500)
    d = game.js("window._d")                                 # [icons drawn, drops in the air, piles on the ground]
    first = next(i for i, f in enumerate(d) if f[0] == 2)    # both out...
    on_ground = [f for f in d[first:] if f[1] or f[2] != "[]"]   # (until they fly to you: that's the pick-up, not the drop)
    assert on_ground and all(f[0] == 2 for f in on_ground), [f for f in on_ground if f[0] != 2][:5]   # ...both drawn, every frame


def test_ten_hearts_and_ten_pieces_in_halves_and_no_sprint_when_hungry(game):
    """Health is 20 half hearts and food 20 half pieces (they were 0 to 100): the bar shows them a half at a time, a
    blow is said in hearts, and with three pieces of food or fewer the Shift key does not sprint."""
    assert game.js("[HP_MAX, FOOD_MAX, SPRINT_FOOD]") == [20, 20, 6]
    game.rpc("dev_needs", hp=13, hunger=7)
    game.sleep(900)
    lit = """(id) => { const c = $(id), g = c.getContext('2d'), n = c.width / 99;        // each icon: 2 as the first (full), 0 as the last (empty), 1 neither
      const px = (i) => g.getImageData(i * 10 * n, 0, 9 * n, c.height).data.join(), full = px(0), none = px(9);
      return [...Array(10)].map((_, i) => px(i) === full ? 2 : px(i) === none ? 0 : 1); }"""
    assert game.js(lit, "hearts") == [2, 2, 2, 2, 2, 2, 1, 0, 0, 0]              # six hearts and a half
    assert game.js(lit, "foods") == [2, 2, 2, 1, 0, 0, 0, 0, 0, 0]               # three pieces and a half
    assert game.js("$('status').textContent") == ""
    game.page.keyboard.down("Shift")
    game.page.keyboard.down("d")
    game.sleep(400)
    assert game.js("walking && walking.run") is True                             # fed enough: a sprint
    game.rpc("dev_needs", hunger=6)
    game.sleep(1100)
    assert game.js("walking && walking.run") is False and "sprint" in game.js("$('status').textContent")   # ...and no more, the keys still held
    game.page.keyboard.up("d")
    game.page.keyboard.up("Shift")
    game.rpc("dev_needs", hunger=0)
    game.sleep(900)
    assert "Starving" in game.js("$('status').textContent")
