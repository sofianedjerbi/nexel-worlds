"""Water in Chrome: it has depth and is drawn as a see-through layer; you swim on any of it, with a wake behind."""

import os

SHOT = os.environ.get("WILD_SHOTS")


def mine(game, js):
    return game.js(f"(() => {{ const p = ents.get('agent' + myId); return {js}; }})()")


def test_you_swim_across_water_of_every_depth_and_leave_a_wake(game):
    game.clear_area(8)
    s = game.server()
    rows = ["~~((==))", "~~((==))", "~~((==))", "~~((==))", "~~(==)))", "~~((==))", "~~~((==)"]
    game.rpc("dev_stamp", x=s["x"] + 2, y=s["y"] - 3, rows=rows)
    game.rpc("dev_give", items={"straw_hat": 1})
    game.rpc("dev_race", race="bunny")
    game.act("wear", item="straw_hat"); game.sleep(900)
    assert not mine(game, "swimsAt(p, p.e)")
    layer = game.js("(() => { const b = [...blocks.values()].find((b) => b.water && b.water.any && b.water.foam.length > 0); return b ? [b.water.canvas.width, true] : null; })()")   # (the block the pond is in, not any block with water)
    assert layer == [512, True]                                # the water layer is built, with foam along the shore
    assert game.js("[depthAt(%d, %d), depthAt(%d, %d), depthAt(%d, %d)]" % (s["x"] + 2, s["y"], s["x"] + 5, s["y"], s["x"] + 9, s["y"])) == [1, 2, 4]
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/water.png")
    game.hold(["d"], 900)                                      # into the shallows
    assert mine(game, "swimsAt(p, p.e)") and game.server()["swimming"]
    assert mine(game, "p.wake.length") >= 2                    # a wake behind us
    game.hold(["d"], 500)                                      # and on over the deep
    assert game.server()["swimming"] and game.server()["x"] >= s["x"] + 5
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/water_swim.png")
    game.hold(["a"], 2600)                                     # and back out
    assert not game.server()["swimming"] and not mine(game, "swimsAt(p, p.e)")
    assert not game.errors


def test_a_page_older_than_the_servers_code_reloads_itself(game):
    stamp = game.js("webStamp")
    assert stamp > 0                                           # the server said when its client code last changed
    game.js("spec.onmessage({data: JSON.stringify({type: 'hello', web: webStamp})})")
    game.sleep(300)
    assert game.js("myId") is not None                         # the same code: nothing happens
    with game.page.expect_navigation():                        # newer code after a reconnect: the page loads it
        game.js("spec.onmessage({data: JSON.stringify({type: 'hello', web: webStamp + 1})})")


def test_swimming_sounds_like_swimming_not_like_walking(game):
    game.clear_area(8)
    s = game.server()
    game.rpc("dev_stamp", x=s["x"] + 1, y=s["y"] - 2, rows=["~~((==))"] * 5)
    game.sleep(600)
    game.wait("sounds.manifest && Object.values(sounds.manifest.sounds).flatMap((s) => s.files).every((f) => sounds.buffers.get(f) instanceof AudioBuffer)", 20000)
    game.hold(["d"], 400)                                      # in: one splash
    game.js("sounds.lastAt = {}")
    game.hold(["d"], 800)                                      # swimming on
    heard = set(game.js("Object.keys(sounds.lastAt)"))
    assert "swim" in heard and not heard & {"step", "wade", "water"}, sorted(heard)
    game.sleep(600)                                            # (the stroke that carries you onto the tile you were entering)
    game.js("sounds.lastAt = {}")
    game.sleep(1200)                                           # treading water: nothing
    assert not set(game.js("Object.keys(sounds.lastAt)")) & {"swim", "step", "wade", "water"}
    assert not game.errors


def test_a_sprint_in_the_water_is_twice_as_fast_and_leaves_a_longer_wake(game):
    """Shift in the water did nothing (nobody sprinted there). Now it is a sprint as on land, ten tiles a second, with
    its own look: strokes twice as often, and a wake of marks twice as close that last longer."""
    game.clear_area(8)
    s = game.server()
    game.rpc("dev_needs", hp=20, hunger=20)
    game.rpc("dev_stamp", x=s["x"] + 1, y=s["y"] - 4, rows=["(" * 40] * 9)
    game.sleep(600)
    game.hold(["d"], 600)                                      # in, and swimming
    assert mine(game, "swimsAt(p, p.e)") and game.js("SWIM_SPRINT") is True
    x0 = game.server()["x"]
    game.hold(["d"], 1000)
    swum, slow = game.server()["x"] - x0, mine(game, "p.wake.filter((w) => !w.dash).length")
    game.page.keyboard.down("Shift")
    x0 = game.server()["x"]
    game.hold(["d"], 1000)
    dashed, marks = game.server()["x"] - x0, mine(game, "p.wake.filter((w) => w.dash).length")
    game.page.keyboard.up("Shift")
    assert 4 <= swum <= 6 and 8 <= dashed <= 11, (swum, dashed)          # five tiles a second, then ten
    assert marks >= 18 and 8 <= slow <= 13 and mine(game, "p.running") is True, (slow, marks)   # (its wake: a mark every 45 ms, not every 110)
    assert game.server()["swimming"] and not game.errors
