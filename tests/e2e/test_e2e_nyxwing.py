"""Nyxwing in Chrome: it comes down out of the night sky (its entrance: 32 beats, to its song's drop), warns and
strikes, and dies into stars, leaving its Eclipse Core. Nothing calls it down by itself: the test summons it."""

from test_e2e_wild import kind, shot

ATTACKS = "['breath', 'storm', 'sweep', 'dive', 'rush', 'sky']"


def test_nyxwing_comes_down_fights_and_breaks_into_stars(game):
    game.clear_area(12)
    game.rpc("dev_needs", hp=20, hunger=17)
    game.spawn("nyxwing", 6, 0)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && q.e.act === 'arrive')", 25000)
    assert game.js("IMG.nyxwing.width % WILD.nyxwing.cw === 0 && IMG.nyxwing.height === 4 * WILD.nyxwing.ch")   # its sheet, at the table's size
    boss = kind(game, "nyxwing")
    assert game.rpc("dev_hit", id=boss["id"], n=50)["hp"] == boss["hp"]      # coming down, nothing touches it
    game.sleep(7000)
    shot(game, "nyxwing_coming")                                # a speck out of the eclipse, nearer each beat
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && q.e.act !== 'arrive')", 12000)
    shot(game, "nyxwing_landed")
    game.wait(f"[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && {ATTACKS}.includes(q.e.act))", 10000)
    shot(game, "nyxwing_warning")
    game.sleep(2500)
    shot(game, "nyxwing_after")
    game.wait(f"[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && !{ATTACKS}.includes(q.e.act))", 10000)
    boss = kind(game, "nyxwing")
    assert game.rpc("dev_hit", id=boss["id"], n=boss["hp"])["hp"] == 0
    game.sleep(1200)
    shot(game, "nyxwing_dying")                                 # its body shaking, the eclipse opening over it
    game.sleep(1800)
    shot(game, "nyxwing_stars")                                 # its pixels leaving it for the sky
    assert not kind(game, "nyxwing")
    assert not game.errors
