"""Swimming in Chrome: you walk into shallow water and swim, with a wake behind; deep water still stops you."""

import os

SHOT = os.environ.get("WILD_SHOTS")


def mine(game, js):
    return game.js(f"(() => {{ const p = ents.get('agent' + myId); return {js}; }})()")


def test_you_swim_across_a_pond_and_leave_a_wake(game):
    game.clear_area(8)
    s = game.server()
    game.rpc("dev_stamp", x=s["x"] + 2, y=s["y"] - 2, rows=["~~~~~=", "~~~~~=", "~~~~~=", "~~~~~=", "~~~~~="])
    game.rpc("dev_give", items={"straw_hat": 1, "flame_charm": 1})
    game.rpc("dev_race", race="bunny")
    game.act("wear", item="straw_hat"); game.sleep(600)
    game.sleep(500)
    assert not mine(game, "swimsAt(p, p.e)")
    game.hold(["d"], 900)                                      # into the pond
    assert mine(game, "swimsAt(p, p.e)") and game.server()["swimming"]
    assert mine(game, "p.wake.length") >= 2                    # a wake behind us
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/swim_side.png")
    game.hold(["d"], 1500)                                     # on to the deep water: it stops us
    assert game.server()["x"] == s["x"] + 6 and game.server()["swimming"]
    game.hold(["s"], 500)
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/swim_down.png")
    game.hold(["a"], 2200)                                     # and back out
    assert not game.server()["swimming"] and not mine(game, "swimsAt(p, p.e)")
    assert not game.errors
