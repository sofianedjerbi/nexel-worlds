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
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.spawn("tusker", 4, 0)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'tusker' && q.e.act === 'windup')", 3000)
    e = kind(game, "tusker")
    assert e["dir"] == [-1, 0]                                 # pawing the ground, facing us
    shot(game, "tusker_windup")
    game.sleep(2200)
    assert game.server()["hp"] < 20                           # we stood in its line
    shot(game, "tusker_after")
    assert not game.errors


def test_the_pincer_and_the_strawman_are_drawn_in_every_direction(game):
    game.clear_area(8)
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
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
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    game.stamp(2, -2, ["=====", "=====", "=====", "=====", "====="])      # a pool of deep water to the east
    game.spawn("wyrm", 4, 0)
    game.spawn("wisp", -3, -2, still=10 ** 6)
    game.sleep(900)
    assert kind(game, "wyrm") and kind(game, "wisp")
    shot(game, "wisp_wyrm")
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'wyrm' && q.e.act === 'windup')", 8000)   # it lines up on us and rears
    game.sleep(1500)
    assert game.server()["hp"] < 20                           # we stood on the shore, on its line
    shot(game, "wyrm_lunge")
    assert not game.errors


def test_a_creature_comes_up_a_step_as_you_do(game):
    """Creatures stand on the land as people do (sim/bodies.py): one hops up a layer, the screen shows it at its
    height (they kept to the level they were on: you on a step, a tusker rammed the step)."""
    game.clear_area(10)
    game.stamp(-1, -1, ["..."] * 3, levels=["111"] * 3); game.rest()          # you, on ground a layer up
    game.rpc("dev_needs", hp=20, hunger=17)                    # (whole, and not healing by itself: 18 and more)
    boar = game.spawn("tusker", 4, 0)                            # (it sees four tiles)
    game.wait(f"[...ents.values()].some((q) => q.e && q.e.id === {boar} && q.e.z === 1)", 6000)   # it charged, up the step
    assert game.js(f"(() => {{ const q = ents.get('tusker{boar}'); return liftOf(q) > 0; }})()")        # ...and is drawn up there
    game.sleep(600)
    assert game.server()["hp"] < 20
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
    game.sleep(300)
    assert any("Daisy" in row for row in game.js("[...$('sayhelp').children].map((d) => d.textContent)"))
    page.keyboard.press("Escape")


def test_a_tusker_that_is_hit_shows_it_is_angry(game):
    """Hit, a tusker is angry (sim/wild.py): it stamps, a red mark beats by its head, and it comes for you."""
    game.rpc("dev_needs", hp=20, hunger=17)
    boar = game.spawn("tusker", 3, 0, still=10 ** 6)
    game.sleep(400)
    assert game.js(f"ents.get('tusker{boar}').e.angry") is None                 # calm: no mark
    game.js(f"act('attack', {{target: {boar}}})")
    game.wait(f"ents.get('tusker{boar}') && ents.get('tusker{boar}').e.angry === true", 5000)
    red = game.js("""() => new Promise((ok) => requestAnimationFrame(() => { const p = [...ents.values()].find((q) => q.e.kind === 'tusker'), S = TS(), [ox, oy] = screenOrigin(S);
      const d = cv.getContext('2d').getImageData(Math.round((ox + p.x * S - S) * DPR), Math.round((oy + p.y * S - 2 * S) * DPR), Math.round(3 * S * DPR), Math.round(2 * S * DPR)).data; let n = 0;
      for (let o = 0; o < d.length; o += 4) if (d[o] === 240 && d[o + 1] === 80 && d[o + 2] === 63) n++; ok(n / (zoom * DPR) ** 2); }))""")
    assert 12 <= red < 16, red                                                   # the mark: twelve px of its red (and a spark of the same red, some frames)
    game.sleep(2500)
    assert game.server()["hp"] < 20                                              # ...and it came


def test_a_tusker_is_where_it_is_when_it_paws_charges_and_stands_dazed(game):
    """"boar is kinda buggy it glitches a few pixels somewhat teleporting near to its location when doing key moves":
    trotting into line and at the end of a charge the world moved it faster than it was drawn ambling, so it began to
    paw the ground, or stood dazed, most of a tile from its place and slid there meanwhile. Now it keeps the world's
    pace: a quarter of a second into a warning or a daze it is on its tile, and its drawn place never jumps."""
    game.rpc("dev_needs", hp=20, hunger=17)
    game.spawn("tusker", -3, -2)                               # off its line: it trots into line, paws, charges, hits, is dazed
    seen = game.js("""() => new Promise((ok) => {
      const out = {acts: [], worst: 0, late: 0, t0: performance.now()}; let last = null, act = '', since = 0;
      const tick = (now) => {
        const p = [...ents.values()].find((q) => q.e && q.e.kind === 'tusker');
        if (p) {
          const a = p.e.act || '';
          if (a !== act) { act = a; since = now; out.acts.push(a); }
          if (last) out.worst = Math.max(out.worst, Math.hypot(p.x - last.x, p.y - last.y));
          if ((a === 'windup' || a === 'stun') && now - since > 250) out.late = Math.max(out.late, Math.hypot(p.tx - p.x, p.ty - p.y));
          last = {x: p.x, y: p.y};
        }
        if (performance.now() - out.t0 < 7000) requestAnimationFrame(tick); else ok(out);
      };
      requestAnimationFrame(tick);
    })""")
    assert {"windup", "charge", "stun"} <= set(seen["acts"]), seen
    assert seen["worst"] < 0.6 and seen["late"] < 0.02, seen    # (no jump; in its place while it paws and while it is dazed)


def test_a_blow_is_said_in_hearts_whoever_takes_it(game):
    """"heart and demi heart should be the universal health unit... default player hit damage should be 0.5 not 5
    hearts": bare hands take half a heart from a cow (three hearts: six blows), and the number over it is in hearts,
    with a small heart beside it, as over a player."""
    cow = game.spawn("cow", 1, 0, still=10 ** 6)
    game.sleep(400)
    game.hold_item(None)
    game.face(1, 0)
    game.press("Space", 500)
    hp = game.js(f"[...ents.values()].find((p) => p.e && p.e.id === {cow}).e.hp")
    last = game.js("floats.filter((f) => f.heart).map((f) => f.text).pop()")
    assert hp == 5 and last == "-0.5", (hp, last)             # six half hearts, one gone
