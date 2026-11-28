"""Wild enemies in Chrome: they are drawn, they warn before they hurt, and stepping aside works."""

import pytest
import os

from nexel_worlds.sim.constants import TICK_HZ

SHOT = os.environ.get("WILD_SHOTS")          # a folder to keep screenshots of each scene in


def kind(game, k):
    return game.js(f"(() => {{ const c = [...ents.values()].find((q) => q.e && q.e.kind === '{k}'); return c ? c.e : null; }})()")


def shot(game, name):
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/{name}.png")


def test_the_tusker_warns_charges_and_hurts_if_you_stay(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.spawn("tusker", 4, 0)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'tusker' && q.e.act === 'windup')", 3000)
    e = kind(game, "tusker")
    assert e["dir"] == [-1, 0]                                 # pawing the ground, facing us
    shot(game, "tusker_windup")
    game.until("meObs.self.hp < 20")                     # (the blow, as the page is told it: waited for, not timed)
    assert game.server()["hp"] < 20                           # we stood in its line
    shot(game, "tusker_after")
    assert not game.errors


def test_the_pincer_and_the_strawman_are_drawn_in_every_direction(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.spawn("pincer", 3, 1, still=10 ** 6)
    game.spawn("strawman", -3, 0, still=10 ** 6)
    game.spawn("tusker", 0, -6, still=10 ** 6)
    game.until("['pincer', 'strawman', 'tusker'].every((k) => [...ents.values()].some((q) => q.e && q.e.kind === k))")
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
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.stamp(2, -2, ["=====", "=====", "=====", "=====", "====="])      # a pool of deep water to the east
    game.spawn("wyrm", 4, 0)
    game.spawn("wisp", -3, -2, still=10 ** 6)
    game.until("['wyrm', 'wisp'].every((k) => [...ents.values()].some((q) => q.e && q.e.kind === k))")
    assert kind(game, "wyrm") and kind(game, "wisp")
    shot(game, "wisp_wyrm")
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'wyrm' && q.e.act === 'windup')", 8000)   # it lines up on us and rears
    game.until("meObs.self.hp < 20")                     # (the blow, as the page is told it: waited for, not timed)
    assert game.server()["hp"] < 20                           # we stood on the shore, on its line
    shot(game, "wyrm_lunge")
    assert not game.errors


def test_the_gustling_spins_up_and_snatches_what_is_in_your_hand(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.give(wood=10)
    game.hold_item("wood")
    game.spawn("gustling", 1, 0)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'gustling' && q.e.act === 'windup')", 4000)
    shot(game, "gustling_spin")                                # the warning: it draws up thin and spins
    game.until("(meObs.self.inventory.wood || 0) === 5")  # (what it took, as the page is told it)
    assert game.inv("wood") == 5                               # we stood there: it took five of what we held
    e = kind(game, "gustling")
    assert e and e["act"] == "flee"                            # ...and runs off with it
    shot(game, "gustling_off")
    assert game.server()["hp"] == 20 and not game.errors       # it never hurts anyone


def test_a_creature_comes_up_a_step_as_you_do(game):
    """Creatures stand on the land as people do (sim/bodies.py): one hops up a layer, the screen shows it at its
    height (they kept to the level they were on: you on a step, a tusker rammed the step)."""
    game.clear_area(10)
    game.stamp(-1, -1, ["..."] * 3, levels=["111"] * 3); game.rest()          # you, on ground a layer up
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    boar = game.spawn("tusker", 4, 0)                            # (it sees four tiles)
    game.wait(f"[...ents.values()].some((q) => q.e && q.e.id === {boar} && q.e.z === 1)", 6000)   # it charged, up the step
    # ...and is drawn up there (from the next frames: the server's z comes with a tick, the body is drawn by the frame
    # after it; read at the very instant the tick came, it was not drawn yet, at a load of 8)
    game.wait(f"(() => {{ const q = ents.get('tusker{boar}'); return !!q && liftOf(q) > 0; }})()", 2000)
    game.until("meObs.self.hp < 20")                     # (the blow, as the page is told it: waited for, not timed)
    assert game.server()["hp"] < 20
    assert not game.errors


def test_a_named_animal_carries_its_name(game):
    """Named (here by the action typed in full; in play with a name tag in hand: test_e2e_ask.py), the animal beside
    you is yours (it never goes away: sim/spawning.py). Its name is drawn over it, as a player's is, the chat says
    so, and the list of who is near has it by name."""
    hen = game.spawn("chicken", 1, 0, still=10 ** 6)
    game.give(name_tag=1)                                      # (a name takes a name tag)
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
    game.until("[...$('sayhelp').children].some((d) => d.textContent.includes('Daisy'))")
    assert any("Daisy" in row for row in game.js("[...$('sayhelp').children].map((d) => d.textContent)"))
    page.keyboard.press("Escape")


def test_a_tusker_that_is_hit_shows_it_is_angry(game):
    """Hit, a tusker is angry (sim/wild.py): it stamps, a red mark beats by its head (characters.js), and it comes for you."""
    game.rpc("dev_needs", hp=20, hunger=17)
    boar = game.spawn("tusker", 3, 0, still=10 ** 6)
    game.until(f"ents.has('tusker{boar}')")
    assert game.js(f"ents.get('tusker{boar}').e.angry") is None                 # calm: no mark
    game.js(f"act('attack', {{target: {boar}}})")
    game.wait(f"ents.get('tusker{boar}') && ents.get('tusker{boar}').e.angry === true", 5000)
    game.until("meObs.self.hp < 20")                     # (the blow, as the page is told it: waited for, not timed)
    assert game.server()["hp"] < 20                                              # ...and it came


def test_a_tusker_is_where_it_is_when_it_paws_charges_and_stands_dazed(game):
    """"boar is kinda buggy it glitches a few pixels somewhat teleporting near to its location when doing key moves":
    trotting into line and at the end of a charge the world moved it faster than it was drawn ambling, so it began to
    paw the ground, or stood dazed, most of a tile from its place and slid there meanwhile. Now it keeps the world's
    pace: a quarter of a second into a warning or a daze it is on its tile, and its drawn place never jumps."""
    game.rpc("dev_needs", hp=20, hunger=17)
    boar = game.spawn("tusker", -3, -2)                        # off its line: it trots into line, paws, charges, hits, is dazed
    # (a jump: further in a frame than a charge, a tile a tick, goes in that frame's time. It was further than 0.6 of a
    # tile in a frame, which a charge goes in a frame of 60 ms: on the runners, frames of 70 to 110 ms, it "jumped" 0.7 and 1.1)
    # (this one, by its id: the page is told of the far land's creatures too (#387), an earlier test's tusker among them)
    seen = game.js("""([hz, id]) => new Promise((ok) => {
      const out = {acts: [], worst: 0, late: 0, t0: performance.now()}; let last = null, act = '', since = 0;
      const tick = (now) => {
        const p = ents.get('tusker' + id);
        if (p && p.e) {
          const a = p.e.act || '';
          if (a !== act) { act = a; since = now; out.acts.push(a); }
          if (last) out.worst = Math.max(out.worst, Math.hypot(p.x - last.x, p.y - last.y) - hz * (now - last.t) / 1000);
          if ((a === 'windup' || a === 'stun') && now - since > 250) out.late = Math.max(out.late, Math.hypot(p.tx - p.x, p.ty - p.y));
          last = {x: p.x, y: p.y, t: now};
        }
        if (performance.now() - out.t0 < 7000) requestAnimationFrame(tick); else ok(out);
      };
      requestAnimationFrame(tick);
    })""", [TICK_HZ, boar])
    assert {"windup", "charge", "stun"} <= set(seen["acts"]), seen
    assert seen["worst"] < 0.3 and seen["late"] < 0.02, seen    # (no jump; in its place while it paws and while it is dazed)


def test_a_blow_is_said_in_hearts_whoever_takes_it(game):
    """"heart and demi heart should be the universal health unit... default player hit damage should be 0.5 not 5
    hearts": bare hands take half a heart from a cow (three hearts: six blows), and the number over it is in hearts,
    with a small heart beside it, as over a player."""
    cow = game.spawn("cow", 1, 0, still=10 ** 6)
    game.until(f"ents.has('cow{cow}')")
    game.hold_item(None)
    game.face(1, 0)
    game.press("x", 500)
    hp = game.js(f"[...ents.values()].find((p) => p.e && p.e.id === {cow}).e.hp")
    last = game.js("floats.filter((f) => f.heart).map((f) => f.text).pop()")
    assert hp == 5 and last == "-0.5", (hp, last)             # six half hearts, one gone
