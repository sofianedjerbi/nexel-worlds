"""Nyxwing in Chrome: it comes through a rift that tears open beside you (its entrance: 32 beats, to its song's drop, #270),
warns and strikes, and dies into stars, leaving its Eclipse Core. Nothing calls it by itself: the test summons it."""

from conftest import open_game
from test_e2e_wild import SHOT, kind, shot

NYX = "ents.get('nyxwing{}')"       # (a test's own, by its id: on a full run's server another one may be about, mid-fight)
ATTACKS = "['breath', 'storm', 'sweep', 'dive', 'rush', 'sky']"


def later(game, ms, name):
    """A picture of a moment `ms` on, only when pictures are kept (WILD_SHOTS): nothing is checked by waiting for it."""
    if SHOT:
        game.sleep(ms)
        shot(game, name)


BEAT = 60 / 156
# the screen at the rift's middle (86 art px over its tile): of 81 px, how many are its night (blue over green, dark), not the meadow
NIGHT = """([x, y]) => { const a = HdLook.screenOf(x + .5, y + .5, levelAt(x, y)), u = HdLook.art().u, k = devicePixelRatio;
  const d = HdLook.read(Math.round((a[0] - 4) * k), Math.round((a[1] - 86 * u - 4) * k), Math.round(9 * k), Math.round(9 * k)).data; let n = 0;
  for (let i = 0; i < d.length; i += 4) if (d[i + 2] > d[i + 1] + 20 && d[i] + d[i + 1] + d[i + 2] < 360) n++; return n / (d.length / 4); }"""


def test_nyxwing_comes_through_a_rift_fights_and_breaks_into_stars(game):
    game.clear_area(12)
    game.rpc("dev_needs", hp=20, hunger=17)
    cid = game.spawn("nyxwing", 6, 0)
    nyx = NYX.format(cid)
    game.wait(f"(() => {{ const q = {nyx}; return q && q.e.act === 'arrive'; }})()", 25000)
    assert game.js("IMG.nyxwing.width % WILD.nyxwing.cw === 0 && IMG.nyxwing.height === 4 * WILD.nyxwing.ch")   # its sheet, at the table's size
    boss = kind(game, "nyxwing")
    assert game.rpc("dev_hit", creature=boss["id"], n=50)["hp"] == boss["hp"]      # coming through, nothing touches it
    # the rift: torn open wide beside you (nyxwing_sky.js WIDE), drawn as the server's time says, its night on the screen
    game.wait(f"(() => {{ const r = Nyx.rift({cid}); return r && r.open > .99 && performance.now() - r.at < 1000; }})()", 20000)
    # (its beat when drawn, carried on to now: s of its entrance, as this page has it, against the server's `came`)
    t, line, came, act = game.js(f"(() => {{ const r = Nyx.rift({cid}), q = {nyx}; return [r.u * {BEAT} + (performance.now() - r.at) / 1000, r.line, q.e.came, q.e.act]; }})()")
    assert act == "arrive" and line == 1 and abs(t - came) < .6, (t, line, came, act)
    nx, ny = game.js(f"[{nyx}.x, {nyx}.y].map(Math.round)")
    assert game.js(NIGHT, [nx, ny]) > .5, game.js(NIGHT, [nx, ny])
    later(game, 3000, "nyxwing_coming")                          # its eyes in the rift, then it, nearer each beat
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'nyxwing' && q.e.act !== 'arrive')", 30000)
    shot(game, "nyxwing_landed")
    # and the rift shut behind it: not drawn past its last beats (32-37)
    game.wait(f"(() => {{ const r = Nyx.rift({cid}); return r && r.u >= 32; }})()", 10000)
    game.sleep(2500)                                             # (5 beats: 1.9 s; the rift is no longer painted)
    assert game.js(f"Nyx.rift({cid}).u") < 37.5, game.js(f"Nyx.rift({cid})")
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



def test_a_player_who_comes_late_sees_its_entrance_where_it_is(game, browser, server):
    """(#88) Someone walks in while it is coming through: their page timed its entrance, and its song, from when it first
    saw it, so it showed them the start of it and played the song from its start, out of step with the fight. Now the
    server says how long ago it came (views.py `came`): the late page's entrance began that long ago, its rift already
    torn open (beat 10 and more: from 0 it was not there yet)."""
    x, y = game.pos()
    # (the late page joined first, 300 tiles off, out of sight and hearing (a boss carries VIEW_R): joined after the wait, a
    # runner's join took the rest of the entrance, and it first saw it landed: came 12.3, the whole of ARRIVE, act '')
    late = open_game(browser, server)
    try:
        late.rpc("dev_teleport", x=x + 300, y=y); late.arrive()
        game.clear_area(12)
        cid = game.spawn("nyxwing", 6, 0)
        nyx = NYX.format(cid)
        game.wait(f"(() => {{ const q = {nyx}; return q && q.e.act === 'arrive' && q.e.came >= 4; }})()", 30000)
        late.rpc("dev_teleport", x=x, y=y + 1)
        late.wait(f"(() => {{ const q = {nyx}; return q && Nyx.began(q.e) !== undefined; }})()", 15000)
        ago, came, act = late.js(f"(() => {{ const q = {nyx}; return [(performance.now() - Nyx.began(q.e)) / 1000, q.e.came, q.e.act]; }})()")
        assert came >= 4 and abs(ago - came) < .6, (ago, came, act)     # (it was the time since this page first saw it: about 0)
        late.wait(f"(() => {{ const r = Nyx.rift({cid}); return r && performance.now() - r.at < 500; }})()", 10000)
        r = late.js(f"(() => {{ const r = Nyx.rift({cid}); return {{...r, t: r.u * {BEAT} + (performance.now() - r.at) / 1000, came: {nyx}.e.came}}; }})()")
        assert r["line"] == 1 and r["open"] > 0 and abs(r["t"] - r["came"]) < .6, r   # (its tear already parting)
        assert not late.errors, late.errors
    finally:
        late.page.close()
