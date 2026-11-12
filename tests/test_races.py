"""Player races: chosen at login, kept, sent to who watches; the AI players are not all cats."""

from megastructure.tiles import RACES


def test_a_race_is_chosen_at_login_kept_and_can_be_changed(world):
    sim, a = world
    assert a.race == "cat" and sim.observe(a)["self"]["race"] == "cat"
    b = sim.login("Bryn", "tok2", "human", "bunny")
    assert b.race == "bunny" and b.to_json()["race"] == "bunny"
    sim.logout(b)
    assert sim.login("Bryn", "tok2").race == "bunny"                 # coming back without saying: still a bunny
    assert sim.login("Bryn", "tok2", "human", "duck").race == "duck"  # or pick again
    assert sim.login("Bryn", "tok2", "human", "dragon").race == "duck"  # an unknown race changes nothing


def test_the_ai_players_come_in_every_race(world):
    sim, _ = world
    seen = {sim.login(f"agent{i}", "t", "a quiet builder").race for i in range(40)}
    assert seen == set(RACES)


def test_the_client_knows_the_same_races():
    import re
    from pathlib import Path
    js = (Path(__file__).parent.parent / "src/megastructure/web/js/races.js").read_text()
    assert tuple(re.findall(r'\{key: "(\w+)", name:', js)) == RACES
