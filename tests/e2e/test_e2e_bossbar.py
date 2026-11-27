"""The boss bar (#384, bossbar.js): a boss's name and life across the top while it is about, its phase at half, gone
after its death, and the buttons at the top stepping down under it while it is there."""

import json

BAR = """(() => { const c = $('bossbar'), d = c.dataset, g = $('goalhint').getBoundingClientRect();
  return JSON.stringify({state: d.state || 'none', boss: d.boss || null, hp: +d.hp, max: +d.max, phase: +d.phase, fill: +d.fill, iw: +d.iw,
    shown: c.style.display, band: getComputedStyle(document.documentElement).getPropertyValue('--bossband').trim(), goals: Math.round(g.top)}); })()"""


def bar(game):
    return game.js(BAR)                                 # (a string: a red prints all of it)


def test_the_boss_bar_follows_a_boss_from_its_waking_to_its_death(game):
    game.clear_area(10)
    game.rpc("dev_needs", hp=20)
    cid = game.spawn("mossback", 0, -4, still=3000)     # (still: it strikes nobody while the test reads its bar)
    key = f"mossback{cid}"
    game.until(f"ents.has({key!r}) && ents.get({key!r}).e.act === 'sleep'")
    goals = game.js("Math.round($('goalhint').getBoundingClientRect().top)")
    assert game.js("$('bossbar').dataset.state || 'none'") == "none", bar(game)          # asleep, a hill: no bar

    # woken: the bar comes, slams its name in, fills to its life; the goals step down under it
    hp = game.rpc("dev_hit", creature=cid, n=8)["hp"]
    game.until(f"$('bossbar').dataset.state === 'fight' && +$('bossbar').dataset.hp === {hp} && ents.get({key!r}).e.hp === {hp}")
    game.until(f"$('goalhint').getBoundingClientRect().top >= {goals} + parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bossband')) - 1")
    s = bar(game)
    d = json.loads(s)
    assert d["boss"] == "mossback" and d["max"] == 60 and d["phase"] == 1 and d["shown"] == "block", s
    assert d["fill"] == int(d["iw"] * hp / 60 + .5) and float(d["band"][:-2]) > 0 and d["goals"] > goals, s

    # under half: its phase
    while hp * 2 > 60:
        hp = game.rpc("dev_hit", creature=cid, n=100)["hp"]
    assert hp > 0
    game.until(f"+$('bossbar').dataset.hp === {hp} && $('bossbar').dataset.phase === '2'")
    s = bar(game)
    d = json.loads(s)
    assert d["state"] == "fight" and d["fill"] == int(d["iw"] * hp / 60 + .5), s

    # its death: the bar shatters, then is gone, and the goals come back up
    while hp > 0:
        hp = game.rpc("dev_hit", creature=cid, n=100)["hp"]
    game.until("$('bossbar').dataset.state === 'dead'")
    game.until("$('bossbar').dataset.state === 'none' && $('bossbar').style.display === 'none'")
    game.until(f"Math.round($('goalhint').getBoundingClientRect().top) === {goals}")
    d = json.loads(bar(game))
    assert d["band"] == "0px" and d["boss"] is None, bar(game)
    assert not game.errors
