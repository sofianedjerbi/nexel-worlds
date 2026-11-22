"""What is in your hand: a block in the pack is a cube (cube_icons.js), the slot in hand stands out (ui.js), and the
selected thing is in your paw, for the others too (held.js; the server's `hold`)."""

# the mean light of a region of an icon's px (x0, y0, x1, y1 inclusive), its ink left out
LIGHT = """([name, regions]) => { const d = fullIcon(name).getContext('2d').getImageData(0, 0, 16, 16).data;
  return regions.map(([x0, y0, x1, y1]) => { let s = 0, n = 0; for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const o = (y * 16 + x) * 4; if (d[o + 3] < 128) continue; s += d[o] * .3 + d[o + 1] * .59 + d[o + 2] * .11; n++; } return n ? s / n : -1; }); }"""


def test_a_block_in_the_pack_is_a_cube_lit_on_top_and_shaded_on_its_right(game):
    """Earth, stone, planks, path: three faces, each its own tone: the top lightest, the right side darkest; inked round."""
    for name in ("dirt", "stone_block", "plank", "path"):
        top, front, right = game.js(LIGHT, [name, [[5, 3, 9, 4], [3, 7, 8, 12], [11, 6, 12, 9]]])
        assert top > front > right > 0, (name, top, front, right)
        assert game.js("(n) => { const d = fullIcon(n).getContext('2d').getImageData(0, 0, 16, 16).data; return [d[(8 * 16 + 2) * 4], d[(8 * 16 + 2) * 4 + 1], d[(8 * 16 + 2) * 4 + 2]]; }", name) == [117, 76, 96]   # (its west edge: the ink)
    # as big as the other things in a 16 px cell (a 15 px block filled the pack's cell where a log is 12): 12 px, in the middle
    box = "(n) => { const d = fullIcon(n).getContext('2d').getImageData(0, 0, 16, 16).data; let b = [99, 99, -1, -1]; for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) if (d[(y * 16 + x) * 4 + 3] > 128) b = [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)]; return b; }"
    assert game.js(box, "dirt") == [2, 2, 13, 13]
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
PAW = """(face) => { const p = ents.get('agent' + myId); p.fx = face[0]; p.fy = face[1]; p.moved = -1e9; myAction = null; Target.aim = null; p.aimT = 0;   // (standing, aiming at nothing: test_e2e_aim.py has the aim's paw)
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
    game.hold_item("bread") if game.inv("bread") else game.js("(() => { selectItem(null); return 1; })()")
    game.wait("!ents.get('agent' + myId).e.held", 4000)


# Your body walking south, drawn at each of the walk's 8 frames (as PAW), without and with a block in hand: -> [[the body's top, the block's top]] a frame
WALK = """() => { const p = ents.get('agent' + myId); p.fx = 0; p.fy = 1; myAction = null; const T = 16, w = 64, h = 96, base = h - 24, run = sprinting();
  const sx = (x) => w / 2 - T / 2 + (x - p.x) * T, sy = Object.assign((y) => base + (y - p.y) * T, {up: (y) => base + (y - p.y) * T, apart: true});
  const shot = (sel, now) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); g.imageSmoothingEnabled = false;
    const keep = ctx, kz = zoom, ks = selected; ctx = g; zoom = 1; selected = sel; p.walking = true; p.moved = now; try { drawEntity(p, sx, sy, T, now / 1000, now); } finally { ctx = keep; zoom = kz; selected = ks; p.walking = false; }
    return g.getImageData(0, 0, w, h).data; };
  const out = []; for (let f = 0; f < 8; f++) { const now = (1000 + f) * 85 + 40, a = shot(null, now), b = shot('dirt', now); let bt = 1e9, it = 1e9;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const o = (y * w + x) * 4; if (a[o + 3] > 128) bt = Math.min(bt, y); if (Math.abs(a[o] - b[o]) + Math.abs(a[o + 1] - b[o + 1]) + Math.abs(a[o + 2] - b[o + 2]) + Math.abs(a[o + 3] - b[o + 3]) > 30) it = Math.min(it, y); }
    out.push([bt, it]); } return out; }"""


def test_the_block_in_hand_goes_up_and_down_with_the_body_as_it_walks(game):
    """The walk's frames lift the body a px and set it down; the block in the paw stood still under it, sliding up and
    down the fur. It goes with the body: a frame's lift is the block's, whole art px."""
    game.give(dirt=3)
    game.hold_item("dirt")
    game.wait("wornReady(agentTint(me), ents.get('agent' + myId).e.worn, ents.get('agent' + myId).e.race, ents.get('agent' + myId).e.bot)")
    r = game.js(WALK)
    assert len({b for b, _ in r}) > 1, r                                                # (the walk bobs: else there is nothing to follow)
    assert len({i - b for b, i in r}) == 1, r                                           # the block keeps its place on the body
    assert not game.errors


def test_the_hand_is_a_slot_even_an_empty_one(game):
    """Like Minecraft: always one slot in hand, drawn so even when it is empty ("always keep an item selected in the
    inventory, even empty hands"); what runs out leaves the slot in hand and the hands empty, the server told; Q goes
    round all ten; ` the first empty one; the slot is kept for the next visit."""
    game.give(wood=1, bread=1)
    game.js("selectItem('wood')")
    empty = game.js("slots.slice(0, 10).lastIndexOf(null)")
    game.press(str((empty + 1) % 10), 100)                                       # its number key
    assert game.js("[handSlot, selected]") == [empty, None]
    assert game.js("[...document.querySelectorAll('#hotbar .slot')].findIndex((e) => e.classList.contains('sel'))") == empty
    assert game.js("document.querySelectorAll('#hotbar .slot.sel').length") == 1 and not game.js("document.querySelector('#hotbar .slot.sel canvas')")
    game.js("selectItem('bread')")
    b = game.js("handSlot")
    game.wait("ents.get('agent' + myId).e.held === 'bread'")
    game.act("drop", item="bread", n=1)
    game.wait("!meObs.self.inventory.bread")
    game.frames(2)
    assert game.js("[handSlot, selected]") == [b, None]                       # gone: the slot stays, the hands are empty
    game.wait("!ents.get('agent' + myId).e.held", 4000)                         # (and the others see empty paws)
    game.give(stone=1)
    assert game.js("[handSlot, selected, slots[handSlot]]") == [b, None, None]  # a new thing: another free slot, not the hand
    for _ in range(10):
        game.press("q", 60)
    assert game.js("handSlot") == b                                             # round all ten, empty ones too
    game.press("`", 100)
    assert game.js("selected") is None and game.js("slots[handSlot]") is None
    game.js("selectSlot(3)")
    assert game.js("localStorage.getItem('megastructure-hand')") == "3"
    assert not game.errors
