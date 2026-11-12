"""Player races in Chrome: the join box offers five, each is drawn from its own sheet, and clothes fit them all."""

import os

SHOT = os.environ.get("WILD_SHOTS")


def me(game):
    return game.js("(() => { const q = [...ents.values()].find((q) => q.e && q.e.kind === 'agent' && q.e.id === myId); return q ? q.e : null; })()")


def test_every_race_is_drawn_and_dressed(game):
    game.clear_area(6)
    assert game.js("[...document.querySelectorAll('#racepick button')].map((b) => b.dataset.race)") == ["cat", "bunny", "bear", "frog", "duck"]
    outfit = ["iron_helmet", "overalls", "denim", "leather_boots", "frost_charm"]
    game.rpc("dev_give", items={n: 1 for n in outfit} | {"straw_hat": 1})
    for race in ("bunny", "bear", "frog", "duck", "cat"):
        game.rpc("dev_race", race=race)
        game.sleep(600)
        assert (me(game).get("race") or "cat") == race
        if SHOT:
            game.page.screenshot(path=f"{SHOT}/race_{race}.png", clip={"x": 520, "y": 300, "width": 160, "height": 150})
    sizes = game.js("""(() => { const out = {};
      for (const r of Races.RACES) { const s = wornSheet('#a9cdf2', null, r.key); out[r.key] = [s.width, s.height, r.key === 'cat' || s.grids.length === 192]; }
      return out; })()""")
    assert all(v == [384, 1152, True] for v in sizes.values()), sizes
    for item in outfit:
        game.act("wear", item=item)
        game.sleep(600)
    for race in ("bunny", "bear", "frog", "duck", "cat"):
        game.rpc("dev_race", race=race)
        game.sleep(600)
        if SHOT:
            game.page.screenshot(path=f"{SHOT}/dressed_{race}.png", clip={"x": 520, "y": 300, "width": 160, "height": 150})
        if race == "bunny":                                    # a hat too: the ears stand above it
            game.act("wear", item="straw_hat"); game.sleep(700)
            if SHOT:
                game.page.screenshot(path=f"{SHOT}/hat_bunny.png", clip={"x": 520, "y": 300, "width": 160, "height": 150})
            game.act("wear", item="iron_helmet"); game.sleep(700)
    assert not game.errors
