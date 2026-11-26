"""Nyxwing in Chrome: it comes down out of the night sky (its entrance: 32 beats, to its song's drop), warns and
strikes, and dies into stars, leaving its Eclipse Core. Nothing calls it down by itself: the test summons it."""

from conftest import open_game
from test_e2e_wild import SHOT, kind, shot

ATTACKS = "['breath', 'storm', 'sweep', 'dive', 'rush', 'sky']"


def later(game, ms, name):
    """A picture of a moment `ms` on, only when pictures are kept (WILD_SHOTS): nothing is checked by waiting for it."""
    if SHOT:
        game.sleep(ms)
        shot(game, name)


def test_nyxwing_comes_down_fights_and_breaks_into_stars(game):
    game.clear_area(12)
    game.rpc("dev_needs", hp=20, hunger=17)
    game.spawn("nyxwing", 6, 0)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && q.e.act === 'arrive')", 25000)
    assert game.js("IMG.nyxwing.width % WILD.nyxwing.cw === 0 && IMG.nyxwing.height === 4 * WILD.nyxwing.ch")   # its sheet, at the table's size
    boss = kind(game, "nyxwing")
    assert game.rpc("dev_hit", creature=boss["id"], n=50)["hp"] == boss["hp"]      # coming down, nothing touches it
    later(game, 7000, "nyxwing_coming")                         # a speck out of the eclipse, nearer each beat
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && q.e.act !== 'arrive')", 30000)
    shot(game, "nyxwing_landed")
    game.wait(f"[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && {ATTACKS}.includes(q.e.act))", 20000)
    shot(game, "nyxwing_warning")
    later(game, 2500, "nyxwing_after")
    game.wait(f"[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && !{ATTACKS}.includes(q.e.act))", 20000)
    boss = kind(game, "nyxwing")
    assert game.rpc("dev_hit", creature=boss["id"], n=boss["hp"])["hp"] == 0
    game.wait("![...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing')", 10000)   # gone from the world
    later(game, 1200, "nyxwing_dying")                          # its body shaking, the eclipse opening over it
    later(game, 1800, "nyxwing_stars")                          # its pixels leaving it for the sky
    assert not game.errors


NYX = "ents.get('nyxwing{}')"       # (this test's own, by its id: on a full run's server another one may be about, mid-fight)


def test_a_player_who_comes_late_sees_its_entrance_where_it_is(game, browser, server):
    """(#88) Someone walks in while it is coming down: their page timed its entrance, and its song, from when it first
    saw it, so it showed them the start of the descent and played the song from its start, out of step with the fight.
    Now the server says how long ago it came (views.py `came`): the late page's entrance began that long ago."""
    game.clear_area(12)
    cid = game.spawn("nyxwing", 6, 0)
    nyx = NYX.format(cid)
    game.wait(f"(() => {{ const q = {nyx}; return q && q.e.act === 'arrive' && q.e.came >= 4; }})()", 30000)
    x, y = game.pos()
    late = open_game(browser, server)
    try:
        late.rpc("dev_teleport", x=x, y=y + 1)
        late.wait(f"(() => {{ const q = {nyx}; return q && Nyx.began(q.e) !== undefined; }})()", 15000)
        ago, came, act = late.js(f"(() => {{ const q = {nyx}; return [(performance.now() - Nyx.began(q.e)) / 1000, q.e.came, q.e.act]; }})()")
        assert came >= 4 and abs(ago - came) < .6, (ago, came, act)     # (it was the time since this page first saw it: about 0)
        assert not late.errors, late.errors
    finally:
        late.page.close()
