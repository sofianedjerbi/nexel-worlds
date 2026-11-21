"""The world: houses and doors, wells, cooking, signs, animals and their structures, picnics."""


def test_a_house_shelters_you_and_doors_keep_animals_out(game):
    game.stamp(-2, -2, ["WWWWW", "W...W", "W...W", "W...W", "WW+WW"]); game.rest()
    game.settle("$('mode').innerText.includes('sheltered')")    # (the page asks the server how you are every 0.7 s: it slept 1.2 s)
    assert game.server()["sheltered"]
    assert "sheltered" in game.js("$('mode').innerText")
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y + 3}}})")       # people walk through the door
    game.sleep(1200)
    assert game.pos() == (x, y + 3)
    game.wait("sounds.manifest", 20000)
    assert "gate" in game.js("Object.keys(sounds.lastAt)")    # the door was heard opening ("a door that open/close noise")...
    game.rpc("dev_teleport", x=x, y=y); game.arrive()
    game.settle("'door_close' in sounds.lastAt")                # (it shuts a moment after you left: it slept 0.8 s)
    assert "door_close" in game.js("Object.keys(sounds.lastAt)")   # ...and, nobody by it any more, closing
    hen = game.spawn("chicken", 0, 3)
    game.rpc("dev_skip", seconds=40)
    game.sleep(600)
    q = game.js(f"(() => {{ const q = ents.get('chicken{hen}'); return q ? [q.tx - {x}, q.ty - {y}] : null; }})()")
    assert q is None or not (abs(q[0]) <= 1 and abs(q[1]) <= 1)   # it never came in


def test_refill_the_can_at_a_well(game):
    game.give(well=1, watering_can=1)
    game.hold_item("well")
    game.face(0, -1)
    game.press("Space", 900)
    game.server()
    game.hold_item("watering_can")
    game.face(0, -1)
    assert "Fill can" in game.actions()
    game.press("Space", 1200)
    assert game.server()["can"] == 12


def test_cooking_at_a_campfire(game):
    game.give(campfire=1, meat=1)
    game.hold_item("campfire")
    game.face(1, 0)
    game.press("Space", 900)
    r = game.act("craft", recipe="cooked_meat")
    game.sleep(300)
    assert r["ok"] and game.inv("cooked_meat") == 1


def test_signs_say_what_you_wrote(game):
    game.give(sign=1)
    game.hold_item("sign")
    game.face(1, 0)
    game.press("Space", 300)                               # a sign is written as it goes up (ask.js)
    game.wait("$('ask').style.display === 'block' && document.activeElement === $('asktext')")
    game.page.keyboard.type("Ben's farm")
    game.page.keyboard.press("Enter")
    game.sleep(900)
    assert game.tile(1, 0) == "?"
    game.press("0", 100)
    game.face(1, 0)
    game.press("Space", 800)
    assert "Ben's farm" in game.toast()


def test_cows_give_milk_and_fed_hens_lay(game):
    cow = game.spawn("cow", 2, 0, still=10 ** 6)
    hen = game.spawn("chicken", -2, 0, still=10 ** 6)
    game.give(berries=1)
    game.sleep(500)
    assert game.act("milk", target=cow)["ok"] and game.inv("milk") == 1
    assert game.act("feed", target=hen, item="berries")["ok"]
    game.rpc("dev_skip", seconds=5)
    game.sleep(800)
    assert game.js("groundItems.some(([x, y, p]) => p.egg)")


def test_a_coop_collects_the_eggs(game):
    game.give(coop=1)
    game.hold_item("coop")
    game.face(0, -1)
    game.press("Space", 900)
    game.spawn("chicken", 3, 0, still=10 ** 6)               # a hen nearby: it lays at the coop's door
    game.rpc("dev_time", phase=.05)                          # all day ahead
    game.rpc("dev_skip", seconds=400)
    game.sleep(800)
    x, y = game.pos()
    at_door = game.js(f"groundItems.some(([ix, iy, p]) => p.egg && ix === {x} && iy === {y})")
    assert at_door or game.inv("egg") >= 1                   # at the coop's door (where you stand: so it's yours)


def test_food_tastes_better_on_a_picnic_blanket(game):
    game.give(picnic_blanket=1, bread=2)
    game.rpc("dev_needs", hunger=4)
    game.hold_item("picnic_blanket")
    game.face(0, -1)
    game.press("Space", 900)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")
    game.sleep(800)
    before = game.server()["hunger"]
    game.hold_item("bread")
    game.press("e", 1400)
    assert game.server()["hunger"] - before == 15            # bread is 10, x1.5 on the blanket


def test_dig_down_and_climb_back_out(game):
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.clear_area(3)
    x, y = game.pos()
    game.face(1, 0)                                          # (nothing in front: X digs down)
    assert "Dig down" in game.actions()
    game.press("x", 2600)                                    # X: the ground goes down a layer, you with it
    assert game.js(f"floorAt({x}, {y})") == -1 and game.pos() == (x, y)
    game.js("selectItem(null)")
    game.face(0, -1); game.press("j", 0)                     # a jump up (J), north, out of the pit
    game.sleep(900)
    s = game.server()
    assert s["x"] == x and s["y"] < y and game.pos() == (s["x"], s["y"])
