"""The world: houses and doors, wells, cooking, signs, animals and their structures, picnics."""

from conftest import SOUNDS

# (every step waits on what the game shows, not on the machine's time: sleeps and presses slept whole, of 300 to 2600 ms,
# were #47's audit, rank 4: a three-tile walk timed by a sleep, the server's answers timed by the press)
PLACED = "!(meObs.self.inventory['{}'] > 0) && !myAction"                          # (put down: gone from the pack)
AT = "(() => {{ const p = myPos(); return !!p && p.x === {} && p.y === {} && !myAction && !walking; }})()"


def test_a_house_shelters_you_and_doors_keep_animals_out(game):
    game.stamp(-2, -2, ["WWWWW", "W...W", "W...W", "W...W", "WW+WW"]); game.rest()
    game.settle("$('mode').innerText.includes('sheltered')")    # (the page asks the server how you are every 0.7 s: it slept 1.2 s)
    assert game.server()["sheltered"]
    assert "sheltered" in game.js("$('mode').innerText")
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y + 3}}})")       # people walk through the door
    game.wait(AT.format(x, y + 3), 8000)
    assert game.pos() == (x, y + 3)
    if SOUNDS:                                                  # (a new worktree has no sounds built: the house still shelters)
        game.wait("sounds.manifest", 20000)
        assert "gate" in game.js("Object.keys(sounds.lastAt)")    # the door was heard opening ("a door that open/close noise")...
    game.rpc("dev_teleport", x=x, y=y); game.arrive()
    if SOUNDS:
        game.settle("'door_close' in sounds.lastAt")                # (it shuts a moment after you left: it slept 0.8 s)
        assert "door_close" in game.js("Object.keys(sounds.lastAt)")   # ...and, nobody by it any more, closing
    hen = game.spawn("chicken", 0, 3)
    game.rpc("dev_skip", seconds=40)
    game.tick(2)                                                # (where the hen is now: the world's next word)
    q = game.js(f"(() => {{ const q = ents.get('chicken{hen}'); return q ? [q.tx - {x}, q.ty - {y}] : null; }})()")
    assert q is None or not (abs(q[0]) <= 1 and abs(q[1]) <= 1)   # it never came in


def test_refill_the_can_at_a_well(game):
    game.give(well=1, watering_can=1)
    game.hold_item("well")
    game.face(0, -1)
    game.press("e", 0)
    game.wait(PLACED.format("well"), 8000)
    game.hold_item("watering_can")
    game.face(0, -1)
    assert "Fill can" in game.actions()
    game.press("e", 0)
    game.wait("meObs.self.can === 12 && !myAction", 8000)
    assert game.server()["can"] == 12


def test_cooking_at_a_campfire(game):
    game.give(campfire=1, meat=1)
    game.hold_item("campfire")
    game.face(1, 0)
    game.press("e", 0)
    game.wait(PLACED.format("campfire"), 8000)
    r = game.act("craft", recipe="cooked_meat")
    game.wait("meObs.self.inventory.cooked_meat === 1", 8000)
    assert r["ok"] and game.inv("cooked_meat") == 1


def test_signs_say_what_you_wrote(game):
    game.give(sign=1)
    game.hold_item("sign")
    game.face(1, 0)
    game.press("e", 300)                               # a sign is written as it goes up (ask.js)
    game.wait("$('ask').style.display === 'block' && document.activeElement === $('asktext')")
    game.page.keyboard.type("Ben's farm")
    game.page.keyboard.press("Enter")
    x, y = game.pos()
    game.wait(f"combAt({x + 1}, {y}) === '?' && !myAction", timeout=8000)
    assert game.tile(1, 0) == "?"
    game.press("0", 100)
    game.face(1, 0)
    game.press("e", 0)
    game.wait("$('toast').style.display === 'block' && $('toastt').innerText.includes(\"Ben's farm\")", timeout=8000)
    assert "Ben's farm" in game.toast()


def test_a_coop_collects_the_eggs(game):
    game.give(coop=1)
    game.hold_item("coop")
    game.face(0, -1)
    game.press("e", 0)
    game.wait(PLACED.format("coop"), 8000)
    game.spawn("chicken", 3, 0, still=10 ** 6)               # a hen nearby: it lays at the coop's door
    game.rpc("dev_time", phase=.05)                          # all day ahead
    game.rpc("dev_skip", seconds=400)
    x, y = game.pos()
    game.wait(f"groundItems.some(([ix, iy, p]) => p.egg && ix === {x} && iy === {y}) || meObs.self.inventory.egg >= 1", timeout=8000)
    at_door = game.js(f"groundItems.some(([ix, iy, p]) => p.egg && ix === {x} && iy === {y})")
    assert at_door or game.inv("egg") >= 1                   # at the coop's door (where you stand: so it's yours)


def test_food_tastes_better_on_a_picnic_blanket(game):
    game.give(picnic_blanket=1, bread=2)
    game.rpc("dev_needs", hunger=4)
    game.hold_item("picnic_blanket")
    game.face(0, -1)
    game.press("e", 0)
    game.wait(PLACED.format("picnic_blanket"), 8000)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")
    game.wait(AT.format(x, y - 1), 8000)
    before = game.server()["hunger"]
    game.hold_item("bread")
    game.press("e", 0)
    game.wait(f"meObs.self.hunger === {before + 15} && !myAside", timeout=8000)
    assert game.server()["hunger"] - before == 15            # bread is 10, x1.5 on the blanket


def test_dig_down_and_climb_back_out(game):
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.clear_area(3)
    x, y = game.pos()
    game.face(1, 0)                                          # (nothing in front: X digs it down)
    assert "Dig down" in game.actions()
    game.press("x", 0)                                       # X: the block you face goes down a layer, not the one under you
    game.wait(f"floorAt({x + 1}, {y}) === -1 && !myAction", timeout=8000)
    assert game.js(f"floorAt({x + 1}, {y})") == -1 and game.js(f"floorAt({x}, {y})") == 0 and game.pos() == (x, y)
    game.act("dig_down", **{"with": "pickaxe"})
    game.wait(f"floorAt({x}, {y}) === -1 && !myAction", 8000)
    game.js("selectItem(null)")
    game.face(0, -1); game.press("Space", 0)                 # a jump up (Space), north, out of the pit
    game.wait(f"!Leap.on() && !walking && !pred && (() => {{ const p = ents.get('agent' + myId); return !!p && p.ty < {y} && p.e.x === p.tx && p.e.y === p.ty; }})()", timeout=8000)
    s = game.server()
    assert s["x"] == x and s["y"] < y and game.pos() == (s["x"], s["y"])
