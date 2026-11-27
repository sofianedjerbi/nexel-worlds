"""Clothes and armor in Chrome: items have icons, E puts one on, the player is drawn dressed, a click takes it off."""

from test_e2e_wild import shot
from waits import QUIET


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
    # (and the panel drawn from it: wear_items.js draws #wearing from meObs.self.wearing on its own 250 ms round, not with the
    # tick that told ents: read the frame after, it had 4 of the 5 (#47, job 140391628734))
    game.until(f"Object.keys((meObs && meObs.self.wearing) || {{}}).length === {len(outfit)} && document.querySelectorAll('#wearing .slot').length === {len(outfit)}")
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


# The rims round the hearts (ui.js drawArmor), read off #armor: per heart 2 (a whole rim), 1 (half: its left side), 0.
RIMS = """(() => { const c = $('armor'), g = c.getContext('2d'), n = c.width / 103;
  const any = (x, w) => { const d = g.getImageData(x * n, 0, w * n, c.height).data; for (let i = 3; i < d.length; i += 4) if (d[i]) return 1; return 0; };
  return [...Array(10)].map((_, i) => { const l = any(2 + i * 10 + 1, 4), r = any(2 + i * 10 + 5, 3); return l && r ? 2 : l ? 1 : r ? -1 : 0; }); })()"""


def test_armor_rims_count_what_you_wear_not_your_hits(game):
    game.clear_area(6)
    pieces = ["iron_helmet", "leather_boots", "gold_chestplate"]            # 10 + 5 + 8: 23%, four rims and a half
    game.rpc("dev_give", items={n: 1 for n in pieces})
    game.until(f"{pieces!r}.every((n) => (meObs.self.inventory[n] || 0) >= 1)")
    assert game.js(RIMS) == [0] * 10, game.js("$('armor').dataset.sig")       # nothing worn: no rim
    for item in pieces:
        game.act("wear", item=item)
        game.until(f"({QUIET})()")
    game.until("meObs.self.armor === 23 && $('armor').dataset.sig.startsWith('4.5,')")     # (the server's armor, and drawn)
    state = lambda: f"rims {game.js(RIMS)}, armor {game.js('meObs.self.armor')}, sig {game.js('$(\"armor\").dataset.sig')}, hp {game.js('meObs.self.hp')}"
    assert game.js(RIMS) == [2, 2, 2, 2, 1, 0, 0, 0, 0, 0], state()
    # a blow: the hearts go down, the rims stay as they were, to the pixel
    before, hp, hearts = game.js("$('armor').toDataURL()"), game.js("meObs.self.hp"), game.js("$('hearts').dataset.sig")
    game.rpc("dev_damage", n=6)
    game.until(f"meObs.self.hp < {hp} && $('hearts').dataset.sig !== {hearts!r}")         # (the page has the hit, drawn)
    assert game.js("$('armor').toDataURL()") == before, state()
    assert game.js(RIMS) == [2, 2, 2, 2, 1, 0, 0, 0, 0, 0], state()
    # a piece off: the rims follow (13%: two and a half)
    game.js("document.querySelector('#wearing .slot[data-slot=head]').click()")
    game.until(f"({QUIET})()")
    game.until("meObs.self.armor === 13 && $('armor').dataset.sig.startsWith('2.5,')")
    assert game.js(RIMS) == [2, 2, 1, 0, 0, 0, 0, 0, 0, 0], state()
    assert not game.errors
