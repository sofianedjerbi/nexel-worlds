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
