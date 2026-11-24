"""The grumblestump, the snapbloom and the hob in Chrome: drawn, warning before they hurt, and the hob on your side."""

from test_e2e_wild import kind, shot

WINDUP = "[...ents.values()].some((q) => q.e && q.e.kind === '{}' && q.e.act === 'windup')"


def test_the_grumblestump_is_a_stump_by_day_and_slams_at_night(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself)
    game.rpc("dev_time", phase=.3)
    game.spawn("grumblestump", 3, 0)
    game.sleep(900)
    assert kind(game, "grumblestump")["act"] == "sleep"       # by day: eyes shut, a stump
    assert game.server()["hp"] == 20
    game.rpc("dev_time", phase=.85)
    game.wait(WINDUP.format("grumblestump"), 8000)             # night: it came, and its arms are going up
    shot(game, "stump_arms_up")
    game.sleep(1300)
    assert game.server()["hp"] < 20                           # we stood in the ring when they came down
    shot(game, "stump_slam")
    assert not game.errors


def test_the_snapbloom_rears_back_then_bites(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)
    game.rpc("dev_time", phase=.3)
    game.spawn("snapbloom", 1, 0)
    game.wait(WINDUP.format("snapbloom"), 4000)
    shot(game, "bloom_rears")
    assert game.server()["hp"] == 20                           # the warning hurts nobody
    game.sleep(1300)
    assert game.server()["hp"] < 20
    assert not game.errors


def test_a_hob_set_down_burns_a_grumblestump_and_it_runs(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)
    game.rpc("dev_time", phase=.85)
    game.give(hob=1)
    game.hold_item("hob")
    game.face(1, 0)
    assert "Light the hob" in game.actions()
    game.press("e", wait=1200)
    hob = kind(game, "hob")
    assert hob and game.inv("hob") == 0                        # lit: a creature now, beside us
    game.spawn("grumblestump", 3, 0)
    game.wait(WINDUP.format("hob"), 4000)                     # it saw it: it hunches, its fire draws in
    shot(game, "hob_hunch")
    game.sleep(500)
    shot(game, "hob_burst")
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'grumblestump' && q.e.hp < 14)", 3000)
    assert not game.errors
