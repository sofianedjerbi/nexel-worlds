"""Wild enemies in Chrome: they are drawn, they warn before they hurt, and stepping aside works."""

import os

SHOT = os.environ.get("WILD_SHOTS")          # a folder to keep screenshots of each scene in


def kind(game, k):
    return game.js(f"(() => {{ const c = [...ents.values()].find((q) => q.e && q.e.kind === '{k}'); return c ? c.e : null; }})()")


def shot(game, name):
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/{name}.png")


def test_the_tusker_warns_charges_and_hurts_if_you_stay(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=100, hunger=100)
    game.spawn("tusker", 4, 0)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'tusker' && q.e.act === 'windup')", 3000)
    e = kind(game, "tusker")
    assert e["dir"] == [-1, 0]                                 # pawing the ground, facing us
    shot(game, "tusker_windup")
    game.sleep(2200)
    assert game.server()["hp"] < 100                           # we stood in its line
    shot(game, "tusker_after")
    assert not game.errors


def test_the_pincer_and_the_strawman_are_drawn_in_every_direction(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=100, hunger=100)
    game.spawn("pincer", 3, 1, still=10 ** 6)
    game.spawn("strawman", -3, 0, still=10 ** 6)
    game.spawn("tusker", 0, -6, still=10 ** 6)
    game.sleep(700)
    assert kind(game, "pincer") and kind(game, "strawman") and kind(game, "tusker")
    drawn = game.js("""(() => {                       // every row of every sheet has pixels in its first frame
      const out = {};
      for (const k of Object.keys(WILD)) {
        const A = WILD[k], c = document.createElement('canvas'); c.width = A.cw; c.height = A.ch * 4;
        const g = c.getContext('2d'); g.drawImage(IMG[k], 0, 0, A.cw, A.ch * 4, 0, 0, A.cw, A.ch * 4);
        out[k] = [0, 1, 2, 3].map((r) => g.getImageData(0, r * A.ch, A.cw, A.ch).data.some((v, i) => i % 4 === 3 && v > 0));
      }
      return out; })()""")
    assert all(all(rows) for rows in drawn.values()), drawn
    shot(game, "three")
    assert not game.errors


def test_the_wisp_and_the_wyrm_are_in_the_game(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=100, hunger=100)
    game.stamp(2, -2, ["=====", "=====", "=====", "=====", "====="])      # a pool of deep water to the east
    game.spawn("wyrm", 4, 0)
    game.spawn("wisp", -3, -2, still=10 ** 6)
    game.sleep(900)
    assert kind(game, "wyrm") and kind(game, "wisp")
    shot(game, "wisp_wyrm")
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'wyrm' && q.e.act === 'windup')", 8000)   # it lines up on us and rears
    game.sleep(1500)
    assert game.server()["hp"] < 100                           # we stood on the shore, on its line
    shot(game, "wyrm_lunge")
    assert not game.errors


def test_a_creature_comes_up_a_step_as_you_do(game):
    """Creatures stand on the land as people do (sim/bodies.py): one hops up a layer, the screen shows it at its
    height (they kept to the level they were on: you on a step, a tusker rammed the step)."""
    game.clear_area(10)
    game.stamp(-1, -1, ["..."] * 3, levels=["111"] * 3)          # you, on ground a layer up
    game.sleep(500)
    game.rpc("dev_needs", hp=100, hunger=100)
    boar = game.spawn("tusker", 4, 0)                            # (it sees four tiles)
    game.wait(f"[...ents.values()].some((q) => q.e && q.e.id === {boar} && q.e.z === 1)", 6000)   # it charged, up the step
    assert game.js(f"(() => {{ const q = ents.get('tusker{boar}'); return liftOf(q) > 0; }})()")        # ...and is drawn up there
    game.sleep(600)
    assert game.server()["hp"] < 100
    assert not game.errors


def test_everybody_stands_three_px_up_in_their_tile(game):
    """A body's sheet puts its feet 2 px over the bottom of its tile (its shadow on the line between two tiles, off the
    brink of a ledge). People and creatures alike are drawn STAND px higher (relief.js bodyY), and what goes with
    where they stand follows: pointing at the lower half of the tile above someone means them."""
    game.clear_area(8)
    cow = game.spawn("cow", 2, 0, still=200)
    game.sleep(500)
    x, y = game.pos()
    assert game.js("STAND") == 3
    drawn = game.js(f"""(() => {{ const S = TS(), [ox, oy] = screenOrigin(S), sy = (yy, xx) => oy + yy * S - (xx === undefined ? 0 : liftOf({{x: xx, y: yy}})), tops = {{}};
      const d = ctx.drawImage; ctx.drawImage = function (img, ...a) {{ if (window.__who && a.length === 8) (tops[__who] = tops[__who] || []).push((a[5] - sy({y})) / zoom); return d.call(ctx, img, ...a); }};
      for (const [k, p] of ents) if (p.e && (p.e.id === myId || p.e.id === {cow})) {{ window.__who = p.e.kind; drawEntity(p, (v) => ox + v * S, sy, S, 0, performance.now()); }}
      window.__who = null; ctx.drawImage = d; return {{agent: Math.min(...tops.agent), cow: Math.min(...tops.cow)}}; }})()""")
    assert drawn["agent"] == -18 - 3 and drawn["cow"] == -16 - 3, drawn     # (art px from the top of the tile to the top of the sheet's cell: 3 higher)
    S, ox, oy = game.js("TS()"), *game.js("screenOrigin()")
    aim = lambda fy: game.js(f"(() => {{ const p = aimAt(tileAtScreen({ox + (x + 2) * S + S / 2}, {oy + (y - 1) * S} + {fy} * {S}), false); return [p.x, p.y]; }})()")
    assert aim(.8) == [x + 2, y] and aim(.2) == [x + 2, y - 1]       # its head and shoulders, over the tile above it; the ground further up
    assert not game.errors


def test_a_named_animal_carries_its_name(game):
    """/name in the chat line: the animal beside you is yours (it never goes away: sim/spawning.py). Its name is
    drawn over it, as a player's is, the chat says so, and the list of who is near has it by name."""
    hen = game.spawn("chicken", 1, 0, still=10 ** 6)
    game.sleep(400)
    page = game.page
    page.keyboard.press("/")
    page.keyboard.type(f"name target={hen} text=Daisy")
    page.keyboard.press("Enter")
    game.wait(f"[...ents.values()].some((p) => p.e && p.e.id === {hen} && p.e.name === 'Daisy')", 5000)
    drawn = game.js("""() => new Promise((ok) => { const o = window.outlined, seen = []; window.outlined = function (t, ...a) { seen.push(t); return o(t, ...a); };
      requestAnimationFrame(() => requestAnimationFrame(() => { window.outlined = o; ok(seen); })); })""")
    assert "Daisy" in drawn and game.name in drawn
    assert "named a chicken Daisy" in game.js("document.querySelector('#chatlog').innerText")
    page.keyboard.press("/")
    page.keyboard.type("feed target=")
    game.sleep(300)
    assert any("Daisy" in row for row in game.js("[...$('sayhelp').children].map((d) => d.textContent)"))
    page.keyboard.press("Escape")
