"""Living: eating, fighting animals (on the move), deaths, beds, fire, and glooms by day."""


def test_eating_takes_three_bites_and_stops_when_full(game):
    game.give(bread=2)
    game.rpc("dev_needs", hunger=40)
    hunger0 = game.server()["hunger"]
    game.hold_item("bread")
    game.press("e", 0)
    game.sleep(450)
    assert game.js("myAction && myAction.tool") == "eat" and game.js("biteIcon('bread', 1) !== null")
    game.sleep(900)
    assert game.server()["hunger"] == hunger0 + 50            # one bread
    game.rpc("dev_needs", hunger=100)
    while game.server()["hunger"] < 100 and game.inv("bread"):
        game.press("e", 1300)
    if game.inv("bread"):
        game.press("e", 600)
        assert "full" in game.toast()


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


def test_glooms_vanish_by_day(game):
    gloom = game.spawn("gloom", 2, 0)
    game.sleep(300)
    game.rpc("dev_skip", seconds=8)
    game.sleep(600)
    assert game.js(f"!ents.has('gloom{gloom}')")
    assert game.server()["hp"] == 100


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
