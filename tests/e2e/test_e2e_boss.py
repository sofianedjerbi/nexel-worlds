"""Old Mossback in Chrome: asleep it is a hill, a blow wakes it, it attacks with a warning, its sporelings fall."""

from test_e2e_wild import kind, shot


def test_old_mossback_sleeps_wakes_and_fights(game):
    game.clear_area(10)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.spawn("mossback", 4, 0)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'mossback' && q.e.act === 'sleep')", 25000)   # (its first step may be a while coming: it lives once the land round it is loaded, a chunk every other tick)
    boss = kind(game, "mossback")
    assert boss and boss["act"] == "sleep"                     # a hill with a tree on it
    drawn = game.js("""(() => { const out = {};        // both sheets loaded, at the size the table says
      for (const k of ['mossback', 'sporeling']) out[k] = IMG[k].width % WILD[k].cw === 0 && IMG[k].height === 4 * WILD[k].ch;
      return out; })()""")
    assert drawn == {"mossback": True, "sporeling": True}
    shot(game, "boss_asleep")
    assert game.server()["hp"] == 20                          # asleep, it hurts nobody
    game.act("attack", target=boss["id"])
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'mossback' && q.e.act !== 'sleep')", 10000)
    shot(game, "boss_awake")
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'mossback' && ['stomp', 'snap', 'shake'].includes(q.e.act))", 8000)
    shot(game, "boss_warning")
    # we stood there: it hit us, or shook its brood loose (whichever it chose, on its warning's end)
    game.wait("meObs.self.hp < 20 || [...ents.values()].some((q) => q.e && q.e.kind === 'sporeling')", 10000)
    shot(game, "boss_after")
    assert not game.errors
