"""The world: houses and doors, glooms at night, wells, cooking, signs, animals and their structures, picnics."""


def test_a_house_shelters_you_and_doors_keep_animals_out(game):
    game.stamp(-2, -2, ["WWWWW", "W...W", "W...W", "W...W", "WW+WW"])
    game.sleep(1200)
    assert game.server()["sheltered"]
    assert "sheltered" in game.js("$('mode').innerText")
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y + 3}}})")       # people walk through the door
    game.sleep(1200)
    assert game.pos() == (x, y + 3)
    game.rpc("dev_teleport", x=x, y=y)
    game.sleep(800)
    hen = game.spawn("chicken", 0, 3)
    game.rpc("dev_skip", seconds=40)
    game.sleep(600)
    q = game.js(f"(() => {{ const q = ents.get('chicken{hen}'); return q ? [q.tx - {x}, q.ty - {y}] : null; }})()")
    assert q is None or not (abs(q[0]) <= 1 and abs(q[1]) <= 1)   # it never came in


def test_glooms_bite_at_night(game):
    game.rpc("dev_time", phase=.85)
    game.spawn("gloom", 1, 0)
    game.sleep(4000)
    assert game.server()["hp"] < 100
    game.rpc("dev_time", phase=.3)


def test_refill_the_can_at_a_well(game):
    game.give(well=1, watering_can=1)
    game.hold_item("well")
    game.face(0, -1)
    game.press("Space", 900)
    game.server()
    game.hold_item("watering_can")
    game.face(0, -1)
    assert "Fill the watering can" in game.actions()
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
    game.press("Space", 900)
    x, y = game.pos()
    assert game.act("write_sign", x=x + 1, y=y, text="Ben's farm")["ok"]
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
    game.rpc("dev_time", phase=.05)                          # all day ahead: no glooms to eat the hen
    game.rpc("dev_skip", seconds=400)
    game.sleep(800)
    x, y = game.pos()
    at_door = game.js(f"groundItems.some(([ix, iy, p]) => p.egg && ix === {x} && iy === {y})")
    assert at_door or game.inv("egg") >= 1                   # at the coop's door (where you stand: so it's yours)


def test_food_tastes_better_on_a_picnic_blanket(game):
    game.give(picnic_blanket=1, bread=2)
    game.rpc("dev_needs", hunger=30)
    game.hold_item("picnic_blanket")
    game.face(0, -1)
    game.press("Space", 900)
    x, y = game.pos()
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")
    game.sleep(800)
    before = game.server()["hunger"]
    game.hold_item("bread")
    game.press("e", 1400)
    assert game.server()["hunger"] - before > 50             # bread is 50, x1.5 on the blanket


def test_a_cave_mouth_you_walk_down_and_back_up(game):
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    x, y = game.pos()
    game.face(1, 0)                                          # (nothing in front: X digs down)
    assert "Dig down" in game.actions()
    game.press("x", 3800)                                    # X: a cave mouth from where you stand, sloping south
    assert game.js(f"combAt({x}, {y})") == "O" and game.js(f"combAt({x}, {y + 1})") == "O"
    game.js("selectItem(null)")
    game.hold(["s"], 450)                                    # walk down it: the cave shows around you, then you're below
    game.sleep(800)
    s = game.server()
    assert s["depth"] == 1 and game.js("depthOf(cam.x)") == 1 and game.pos() == (s["x"], s["y"])
    game.js(f"act('move_to', {{x: {s['x']}, y: {y + 1}}})")    # to the ramp's foot...
    game.sleep(900)
    game.hold(["w"], 260)                                    # ...and up it, out into the daylight
    game.sleep(900)
    s = game.server()
    assert s["depth"] == 0 and s["x"] == x and s["y"] <= y and game.pos() == (s["x"], s["y"])
