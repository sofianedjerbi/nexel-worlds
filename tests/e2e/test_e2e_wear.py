"""Clothes and armor in Chrome: items have icons, E puts one on, the player is drawn dressed, a click takes it off."""

from test_e2e_wild import shot


def me(game):
    return game.js("(() => { const q = [...ents.values()].find((q) => q.e && q.e.kind === 'agent' && q.e.id === myId); return q ? q.e : null; })()")


def test_dressing_up(game):
    game.clear_area(6)
    outfit = ["straw_hat", "overalls", "denim", "leather_boots", "flame_charm"]
    game.rpc("dev_give", items={n: 1 for n in outfit})
    game.until(f"{outfit!r}.every((n) => (meObs.self.inventory[n] || 0) >= 1)")   # (the page has them)
    drawn = game.js("""(() => { const out = {};            // every wearable has its own icon, not the grey square
      for (const n of Object.keys(RULES.wear)) { const d = iconCanvas(n).getContext('2d').getImageData(0, 0, 16, 16).data; let px = 0, grey = 0;
        for (let i = 0; i < d.length; i += 4) if (d[i + 3]) { px++; if (d[i] === 138 && d[i + 1] === 106) grey++; }
        if (px < 12 || grey === px) out[n] = px; }
      return out; })()""")
    assert drawn == {}, drawn
    assert game.js("craftGroups().find(([t]) => t === 'Wear')[2].length") == 19 + 15 + 9      # (clothes, armor, charms: one bookmark of the recipe book)
    for item in outfit:
        game.act("wear", item=item)
        game.until(f"({QUIET})()")                        # (worn: the server has answered)
    game.until(f"(() => {{ const q = [...ents.values()].find((q) => q.e && q.e.kind === 'agent' && q.e.id === myId); return q && q.e.worn && Object.keys(q.e.worn).length === {len(outfit)}; }})()")   # (and the next tick told the page)
    worn = me(game)["worn"]
    assert worn == {"head": "straw_hat", "top": "overalls", "pants": "denim", "shoes": "leather_boots", "effect": "flame_charm"}
    assert game.js("document.querySelectorAll('#wearing .slot').length") == 5
    sheet = game.js("(() => { const s = wornSheet(agentTint(me), [...ents.values()].find((q) => q.e && q.e.id === myId).e.worn); return [s.width, s.height, s.edges.length]; })()")
    assert sheet == [384, 2112, 352]                          # every frame of the sheet dressed
    shot(game, "dressed")
    game.hold(["d"], 500)
    shot(game, "dressed_walking")
    game.js("document.querySelector('#wearing .slot[data-slot=head]').click()")
    game.until(f"({QUIET})()")
    game.until("(() => { const q = [...ents.values()].find((q) => q.e && q.e.kind === 'agent' && q.e.id === myId); return q && q.e.worn && !q.e.worn.head; })()")
    assert "head" not in me(game)["worn"] and game.server()["inventory"].get("straw_hat") == 1
    assert not game.errors
