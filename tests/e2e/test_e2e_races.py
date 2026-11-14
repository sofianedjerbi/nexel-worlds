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
      for (const r of Races.RACES) { const s = wornSheet('#a9cdf2', null, r.key); out[r.key] = [s.width, s.height, r.key === 'cat' || s.grids.length === 288]; }
      return out; })()""")
    assert all(v == [384, 1728, True] for v in sizes.values()), sizes      # (the sheet's 24 rows and the 12 of tool_art.js)
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


PIECES = """(() => {
  // per race: the frames that have more separate pieces than the cat's own frame (a head, an ear or a tool come loose)
  const pieces = (d) => { const seen = new Uint8Array(48 * 48); let n = 0;
    for (let i = 0; i < 48 * 48; i++) { if (!d[i * 4 + 3] || seen[i]) continue; n++; const st = [i]; seen[i] = 1;
      while (st.length) { const j = st.pop(), x = j % 48, y = (j - x) / 48;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const u = x + dx, v = y + dy, k = v * 48 + u;
          if (u >= 0 && v >= 0 && u < 48 && v < 48 && d[k * 4 + 3] && !seen[k]) { seen[k] = 1; st.push(k); } } } }
    return n; };
  const frames = (key) => { const s = raceSheet(key, "#f3f2c0"), c = document.createElement("canvas"); c.width = s.width; c.height = s.height;
    const g = c.getContext("2d"); g.drawImage(s, 0, 0); const out = [];
    for (let r = 0; r < s.height / 48; r++) for (let col = 0; col < 8; col++) out.push(pieces(g.getImageData(col * 48, r * 48, 48, 48).data));
    return out; };
  const cat = frames("cat"), bad = {};
  for (const r of Races.RACES) if (r.key !== "cat") { const f = frames(r.key); bad[r.key] = f.map((n, i) => n > cat[i] ? i : -1).filter((i) => i >= 0); }
  return bad;
})()"""


def test_no_race_comes_apart_on_any_frame(game):
    """Every race is the cat's frame with the head rebuilt. Measured on the whole frame, a raised axe or hoe was taken for
    the head: ears were put on the tool, the head came out as a slab, the hand that holds the tool went with the ears."""
    game.wait("IMG.character && IMG.character.complete && IMG.character.width > 0", 20000)
    assert game.js(PIECES) == {"bunny": [], "bear": [], "frog": [], "duck": []}


def test_a_bunnys_ear_faces_the_way_it_walks(game):
    """Side on, the pink inside of the near ear is on the side the bunny faces (it was on the other: "backwards")."""
    game.wait("IMG.character && IMG.character.complete && IMG.character.width > 0", 20000)
    side = game.js("""(() => { const s = raceSheet("bunny", "#f3f2c0"), c = document.createElement("canvas"); c.width = s.width; c.height = s.height;
      const g = c.getContext("2d"); g.drawImage(s, 0, 0); const out = {};
      for (const [name, row] of [["right", 6], ["left", 7]]) { const d = g.getImageData(0, row * 48, 48, 48).data; let pink = 0, np = 0, eye = 0, ne = 0, top = 48;
        for (let i = 0; i < 48 * 48; i++) if (d[i * 4 + 3]) top = Math.min(top, Math.floor(i / 48));
        for (let y = top; y < top + 8; y++) for (let x = 0; x < 48; x++) { const i = (y * 48 + x) * 4;       // the ear: its pink, and all of it
          if (!d[i + 3]) continue; eye += x; ne++; if (d[i] > 230 && d[i + 1] < 190 && d[i + 2] < 200) { pink += x; np++; } }
        out[name] = pink / np - eye / ne; }
      return out; })()""")
    assert side["right"] > 0 and side["left"] < 0, side          # the pink is ahead of the middle of the ear


def test_every_tool_has_its_own_swing(game):
    """The sheet draws an axe, a hoe and a watering can; a pickaxe, a sword and a spear were all swung as the axe.
    tool_art.js draws each on the axe's frames: every frame of each differs from the axe's and from the others'."""
    game.wait("IMG.character && IMG.character.complete && IMG.character.width > 0", 20000)
    assert game.js("[ANIM.pickaxe, ANIM.sword, ANIM.spear]") == [24, 28, 32]
    assert game.js("[SWING_ROW.pickaxe, SWING_ROW.sword, SWING_ROW.spear, SWING_ROW.axe]") == ["pickaxe", "sword", "spear", "axe"]
    same = game.js("""(() => { const c = document.createElement("canvas"); c.width = IMG.character.width; c.height = IMG.character.height;
      const g = c.getContext("2d"); g.drawImage(IMG.character, 0, 0); const rows = {axe: 16, pickaxe: 24, sword: 28, spear: 32}, out = [];
      const diff = (a, b, r, col) => { const p = g.getImageData(col * 48, (rows[a] + r) * 48, 48, 48).data, q = g.getImageData(col * 48, (rows[b] + r) * 48, 48, 48).data;
        let n = 0; for (let i = 0; i < p.length; i += 4) if (p[i] !== q[i] || p[i + 1] !== q[i + 1] || p[i + 2] !== q[i + 2] || p[i + 3] !== q[i + 3]) n++; return n; };
      for (const [a, b] of [["axe", "pickaxe"], ["axe", "sword"], ["axe", "spear"], ["pickaxe", "sword"], ["sword", "spear"], ["pickaxe", "spear"]])
        for (let r = 0; r < 4; r++) for (let col = 0; col < 8; col++) if (diff(a, b, r, col) < 4) out.push([a, b, r, col]);
      return out; })()""")
    assert same == [], same


SWINGS = os.environ.get("SWING_SHOTS")       # a folder to keep each frame of each attack in, as the game draws it


def test_a_sword_cuts_across_and_a_spear_is_thrust(game):
    """An attack with a sword or a spear was the sheet's chop, which reads as breaking a block. swing_art.js draws the
    weapon over the standing body: the sword crosses from one side of you to the other, the spear goes out and back."""
    game.clear_area(6)
    game.give(sword=1, spear=1)
    blade = """(kind, row, f) => { const d = SwingArt.frame(kind, row, f, [[1, 1, 1], [2, 2, 2], [3, 3, 3]]); let n = 0, sx = 0, sy = 0, far = 0;
      for (let i = 0; i < 48 * 48; i++) if (d[i * 4 + 3] && d[i * 4] > 100 && d[i * 4] < 240) { n++; sx += i % 48; sy += Math.floor(i / 48); far = Math.max(far, i % 48); }
      return [n, sx / n, sy / n, far]; }"""                     # the weapon's own px (not the hand, not the streak)
    sword = game.js(f"[0, 1, 2, 3, 4].map((f) => ({blade})('sword', 0, f))")
    assert all(n > 15 for n, *_ in sword), sword
    assert sword[1][1] < 16 and sword[4][1] > 32, sword        # facing us: from the left of the body to the right of it
    assert sword[2][2] > 34, sword                             # passing in front, below the feet
    spear = game.js(f"[0, 1, 2, 3, 4, 5, 6, 7].map((f) => ({blade})('spear', 2, f))")
    assert spear[3][3] - spear[1][3] >= 10 and spear[7][3] < spear[3][3] - 4, spear   # out, then back
    for kind in ("sword", "spear"):
        game.hold_item(kind)
        for way, (dx, dy) in {"down": (0, 1), "up": (0, -1), "right": (1, 0), "left": (-1, 0)}.items():
            game.face(dx, dy)
            for f in range(6):
                drawn = game.js(f"""new Promise((done) => {{ const p = ents.get('agent' + myId), d0 = ctx.drawImage, out = [];
                  p.fx = {dx}; p.fy = {dy}; p.swing = {{t0: performance.now() - {f * 50 + 20}, with: '{kind}'}};
                  ctx.drawImage = function (img, ...r) {{ if (r.length === 8 && r[2] === 48 && r[3] === 48 && (img.height === 192 || img.height > 1000)) out.push([img.height, r[0] / 48, r[1] / 48]); return d0.call(this, img, ...r); }};
                  requestAnimationFrame(() => requestAnimationFrame(() => {{ ctx.drawImage = d0; window._hold = setInterval(() => {{ p.swing.t0 = performance.now() - {f * 50 + 20}; }}, 5); done(out); }})); }})""")
                row = {"down": 0, "up": 1, "right": 2, "left": 3}[way]
                assert [192, f, row] in drawn, (kind, way, f, drawn)                   # the weapon's frame, for the way faced
                assert any(h > 1000 and r == row for h, c, r in drawn), drawn          # over the standing body, not the chop
                if SWINGS:
                    game.sleep(60)
                    v = game.page.viewport_size; x, y = v["width"] / 2, v["height"] / 2    # (you are in the middle of the screen)
                    game.page.screenshot(path=f"{SWINGS}/{kind}_{way}_{f}.png", clip={"x": x - 110, "y": y - 110, "width": 220, "height": 220})
                game.js("clearInterval(window._hold)")
    assert not game.errors
