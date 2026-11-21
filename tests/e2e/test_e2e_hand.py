"""What is in your hand: a block in the pack is a cube (cube_icons.js), the slot in hand stands out (ui.js), and the
selected thing is in your paw, for the others too (held.js; the server's `hold`)."""

# the mean light of a region of an icon's px (x0, y0, x1, y1 inclusive), its ink left out
LIGHT = """([name, regions]) => { const d = fullIcon(name).getContext('2d').getImageData(0, 0, 16, 16).data;
  return regions.map(([x0, y0, x1, y1]) => { let s = 0, n = 0; for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const o = (y * 16 + x) * 4; if (d[o + 3] < 128) continue; s += d[o] * .3 + d[o + 1] * .59 + d[o + 2] * .11; n++; } return n ? s / n : -1; }); }"""


def test_a_block_in_the_pack_is_a_cube_lit_on_top_and_shaded_on_its_right(game):
    """Earth, stone, planks, path: three faces, each its own tone: the top lightest, the right side darkest; inked round."""
    for name in ("dirt", "stone_block", "plank", "path"):
        top, front, right = game.js(LIGHT, [name, [[3, 2, 9, 4], [2, 8, 8, 13], [11, 6, 13, 10]]])
        assert top > front > right > 0, (name, top, front, right)
        assert game.js("(n) => { const d = fullIcon(n).getContext('2d').getImageData(0, 0, 16, 16).data; return [d[(8 * 16) * 4], d[(8 * 16) * 4 + 1], d[(8 * 16) * 4 + 2]]; }", name) == [117, 76, 96]   # (its west edge: the ink)
    assert game.js("CubeIcon.is('bread') || CubeIcon.is('axe')") is False


def test_the_slot_in_hand_is_bigger_and_says_its_name(game):
    game.give(dirt=3, bread=2)
    game.hold_item("dirt")
    game.wait("document.querySelector('#hotbar .slot.sel')")
    big, small = game.js("""(() => { const s = [...document.querySelectorAll('#hotbar .slot')], sel = s.find((e) => e.classList.contains('sel')), o = s.find((e) => !e.classList.contains('sel'));
      const r = (e) => e.getBoundingClientRect(); return [[r(sel).width, r(sel.querySelector('canvas')).width, r(sel).top], [r(o).width, r(o.querySelector('canvas') || o).width, r(o).top]]; })()""")
    assert big[0] > small[0] and big[2] < small[2]                                  # bigger, lifted
    assert game.js("(() => { const c = document.querySelector('#hotbar .slot.sel canvas').getBoundingClientRect().width, o = document.querySelector('#hotbar .slot:not(.sel) canvas').getBoundingClientRect().width; return c >= o; })()")
    game.hold_item("bread")
    game.wait("$('heldname').classList.contains('on') && $('heldname').textContent === label('bread')")


# Your body drawn as the HD look draws it (hd.js ent: zoom 1, a 64 px wide canvas), without and with a block in hand:
# -> {box: [x0, y0, x1, y1] of the px that differ, body: the same of what is drawn without, cell: its 48 px cell's left, at: Held.at}
PAW = """(face) => { const p = ents.get('agent' + myId); p.fx = face[0]; p.fy = face[1]; p.moved = -1e9; myAction = null;
  const T = 16, w = 64, h = 96, base = h - 24, now = performance.now();
  const sx = (x) => w / 2 - T / 2 + (x - p.x) * T, sy = Object.assign((y) => base + (y - p.y) * T, {up: (y) => base + (y - p.y) * T, apart: true});
  const shot = (sel) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); g.imageSmoothingEnabled = false;
    const keep = ctx, kz = zoom, ks = selected; ctx = g; zoom = 1; selected = sel; try { drawEntity(p, sx, sy, T, now / 1000, now); } finally { ctx = keep; zoom = kz; selected = ks; }
    return g.getImageData(0, 0, w, h).data; };
  let n = 0, solid = 0; { const c = Held.art('dirt'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; for (let i = 3; i < d.length; i += 4) if (d[i] > 128) solid++; }
  const a = shot(null), b = shot('dirt'), box = [1e9, 1e9, -1, -1], body = [1e9, 1e9, -1, -1], add = (r, x, y) => { r[0] = Math.min(r[0], x); r[1] = Math.min(r[1], y); r[2] = Math.max(r[2], x); r[3] = Math.max(r[3], y); };
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const o = (y * w + x) * 4; if (a[o + 3] > 128) add(body, x, y); if (Math.abs(a[o] - b[o]) + Math.abs(a[o + 1] - b[o + 1]) + Math.abs(a[o + 2] - b[o + 2]) + Math.abs(a[o + 3] - b[o + 3]) > 30) { add(box, x, y); n++; } }
  return {box, body, n, solid, cell: Math.round(sx(p.x)) - 16, at: Held.at(p)}; }"""


def test_the_block_in_hand_is_at_the_paw_whichever_way_you_face_and_the_others_see_it(game):
    game.give(dirt=3)
    game.hold_item("dirt")
    game.wait("wornReady(agentTint(me), ents.get('agent' + myId).e.worn, ents.get('agent' + myId).e.race, ents.get('agent' + myId).e.bot)")
    for face in ([0, 1], [1, 0], [-1, 0], [0, -1]):
        r = game.js(PAW, face)
        x0, y0, x1, y1 = r["box"]
        assert x1 >= 0, (face, r)                                                      # something is drawn for it
        ax = r["cell"] + r["at"][0]
        assert ax <= x0 and x1 <= ax + 6, (face, r)                                    # in its 7 px at the paw...
        assert r["body"][1] + 4 <= y0 and y1 <= r["body"][3], (face, r)               # ...low on the body, not over the head
        if face == [0, -1]:
            assert 0 < r["n"] < r["solid"] * .7, (face, r)                          # facing away: behind the body, a part of it shows
        else:
            assert r["n"] >= r["solid"] * .8, (face, r)                              # in front of it: all of it
    game.wait("ents.get('agent' + myId).e.held === 'dirt'")                            # the server has it, and sends it to who watches
    game.hold_item("bread") if game.inv("bread") else game.js("(() => { selected = null; $('hotbar').dataset.sig = ''; drawHotbar(meObs.self.inventory); return 1; })()")
    game.wait("!ents.get('agent' + myId).e.held", 4000)
