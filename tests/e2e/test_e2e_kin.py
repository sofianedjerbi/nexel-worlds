"""The grumblestump, the snapbloom and the hob in Chrome: drawn, warning before they hurt, and the hob on your side."""

from test_e2e_wild import kind, shot

WINDUP = "[...ents.values()].some((q) => q.e && q.e.kind === '{}' && q.e.act === 'windup')"


def test_the_grumblestump_is_a_stump_by_day_and_slams_at_night(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself)
    game.rpc("dev_time", phase=.3)
    game.spawn("grumblestump", 3, 0)
    game.tick(9)
    assert kind(game, "grumblestump")["act"] == "sleep"       # by day: eyes shut, a stump
    assert game.server()["hp"] == 20
    game.rpc("dev_time", phase=.85)
    game.wait(WINDUP.format("grumblestump"), 8000)             # night: it came, and its arms are going up
    shot(game, "stump_arms_up")
    game.wait("meObs.self.hp < 20", 15000)                     # we stood in the ring when they came down
    shot(game, "stump_slam")
    assert not game.errors


def test_the_snapbloom_rears_back_then_bites(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)
    game.rpc("dev_time", phase=.3)
    game.spawn("snapbloom", 1, 0)
    game.wait(WINDUP.format("snapbloom"), 10000)
    shot(game, "bloom_rears")
    # (that the warning itself hurts nobody is the sim's: tests/test_stump.py. Read here, the page saw the windup after the bite on a slow runner)
    game.wait("meObs.self.hp < 20", 15000)                     # and then it bites
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
    game.wait(WINDUP.format("hob"), 10000)                     # it saw it: it hunches, its fire draws in
    shot(game, "hob_hunch")
    game.tick(5)
    shot(game, "hob_burst")
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'grumblestump' && q.e.hp < 14)", 15000)
    assert not game.errors


HEAR = "(() => { window.__heard = []; const play = sfx; sfx = (n, ...a) => { window.__heard.push(n); return play(n, ...a); }; })()"


def test_each_creature_makes_its_own_sounds(game):
    """Picked by ear (music/sfx.py "Creatures"): a warning, a blow and a cry of its own, never the bare-hands punch."""
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)
    game.rpc("dev_time", phase=.3)
    game.js(HEAR)
    game.spawn("tusker", 4, 0)
    game.wait("window.__heard.includes('tusker_ram')", 15000)   # it warns, then charges us down
    game.spawn("snapbloom", 0, 1)
    game.wait("window.__heard.includes('snapbloom_bite')", 15000)
    heard = game.js("window.__heard")
    assert {"tusker_warn", "tusker_ram", "snapbloom_warn", "snapbloom_bite"} <= set(heard), heard
    assert "punch" not in heard
    # (the tusker and the snapbloom sent away: the tusker still about set the hob off from three tiles, out of its burst's two)
    game.rpc("dev_creatures", clear=40)
    game.rpc("dev_time", phase=.85)
    game.give(hob=1)
    game.hold_item("hob")
    game.face(-1, 0)
    game.press("e", wait=1200)
    game.spawn("grumblestump", -3, 0)
    game.wait("window.__heard.includes('grumblestump_hurt')", 20000)      # what it burnt cried out (with the burst: world_decor.js)
    heard = game.js("window.__heard")
    assert {"hob_lit", "hob_warn", "hob_burst"} <= set(heard), heard
    assert not game.errors
