"""An item's pixels are the game's pixels: on the ground an art pixel of it is a pixel of the land, in the HUD a whole
number of screen pixels, the same as the frame it sits in. Nothing is squeezed to a size in between."""

import random

import pytest
from game import Game

# every draw of an item's icon (and of a picked fruit) on the game's canvas: [source w, h, drawn w, h]
WATCH = """() => { window.__it = []; const o = ctx.drawImage;
  ctx.drawImage = function (img, ...r) {
    const icon = [...ghosts.values()].includes(img), fruit = img === IMG.trees && r.length === 8 && r[2] === 16 && r[3] === 16 && flyers.length;
    if (icon || fruit) __it.push(r.length === 8 ? [r[2], r[3], r[6], r[7]] : [img.width, img.height, r[2], r[3]]);
    return o.call(this, img, ...r); };
  return 1; }"""


# a small icon's px against its icon's: how many are there, half there, of a colour the icon has not, near white
SMALL = """(name) => { const px = (c) => c.getContext('2d').getImageData(0, 0, c.width, c.height).data, d = px(ghostIcon(name)), src = px(iconCanvas(name));
  const own = new Set(), out = {solid: 0, soft: 0, alien: 0, white: 0};
  for (let i = 0; i < src.length; i += 4) if (src[i + 3] >= 128) own.add(src[i] << 16 | src[i + 1] << 8 | src[i + 2]);
  for (let i = 0; i < d.length; i += 4) { if (!d[i + 3]) continue; out.solid++;
    if (d[i + 3] !== 255) out.soft++; else if (!own.has(d[i] << 16 | d[i + 1] << 8 | d[i + 2])) out.alien++;
    if (ICONS[name][0] === 'items' && Math.min(d[i], d[i + 1], d[i + 2]) > 225) out.white++; }
  return out; }"""


@pytest.mark.parametrize("zoom", [2, 3])
def test_a_thing_on_the_ground_is_drawn_at_the_lands_own_pixel_size(game, zoom):
    """A pile, what hops out of a creature and what flies up into your hands are small icons of 11 art px, made from
    the 16 px ones by whole pixels, and a picked berry is its 16; all drawn at the zoom, whatever they do (the 16 px
    icon was drawn 10 px across, and smaller still as it was caught: pixels of 1.9 screen px beside the land's 3).
    A small icon is made of its icon's own colours, without the white sticker edge."""
    game.js(f"zoom = {zoom}")
    game.give(wood=2, stone=2, axe=1, boat=1)
    game.js(WATCH)
    for item in ("wood", "boat", "axe"):
        game.act("drop", item=item, n=1)
    game.sleep(700)                                              # the pile, lying under you
    x, y = game.pos()
    game.js(f"dropLoot({x + 2}, {y}, {{stone: 1, wood: 1, axe: 1}}, performance.now())")
    game.sleep(900)                                              # ...loot hopping out, landing (a pixel lower for a moment)
    game.js(f"picked({x - 2}, {y}, 'b', me, performance.now())")
    game.press("f", 1200)                                        # ...the pile into your hands, and a berry
    draws = game.js("__it")
    assert game.inv("boat") == 1 and game.inv("wood") == 2       # (picked up: it flew)
    assert len(draws) > 60 and game.js("!magnets.length && !flyers.length")
    assert {(w, h) for w, h, _, _ in draws} == {(11, 11), (11, 10), (16, 16)}, {(w, h) for w, h, _, _ in draws}   # (10: landing, a row in the ground)
    off = [d for d in draws if d[2] != d[0] * zoom or d[3] != d[1] * zoom]
    assert not off, off[:5]
    for name in ("wood", "axe", "torch", "pickaxe", "stone"):   # (not an egg: its glint is white)
        m = game.js(SMALL, name)
        assert m["solid"] > 8 and m["soft"] == 0 and m["alien"] == 0 and m["white"] == 0, (name, m)
    assert not game.errors


# every item icon in the HUD and its slot's frame: screen pixels to an art pixel, and whether anything scales it
HUD = """() => { const d = devicePixelRatio, out = {};
  const px = (sel, art) => [...document.querySelectorAll(sel)].filter((e) => e.offsetWidth).map((e) => { const r = e.getBoundingClientRect(); return [r.width * d / art, r.height * d / art]; }).flat();
  out.icons = px('#hotbar .slot canvas, #bagitems .slot canvas, #recipes .slot canvas, .ctab canvas, .cneed canvas', 11);
  out.art = [...new Set([...document.querySelectorAll('#hotbar .slot canvas, #bagitems .slot canvas, #recipes .slot canvas')].map((c) => c.width + 'x' + c.height))].join();
  out.frames = px('#hotbar .slot, #bagitems .slot, #recipes .slot', 30);
  out.big = [...px('#craftdetail .slot.big canvas', 16), ...px('#craftdetail .slot.big', 30)];
  out.vitals = [$('hearts').getBoundingClientRect().width * d / 99];         // (ten hearts: 99 art px)
  out.moved = ['hud', 'bag', 'craft'].map((id) => getComputedStyle($(id)).transform).join();
  out.fits = $('hud').getBoundingClientRect().left >= 0 && $('hud').getBoundingClientRect().right <= innerWidth;
  return out; }"""


@pytest.mark.parametrize("w,h,dpr,touch,land", [(1280, 760, 1, False, 3), (1280, 760, 2, False, 6), (1100, 700, 1.5, False, 0),
                                              (840, 384, 2.625, True, 5), (390, 844, 3, True, 0), (560, 700, 2, False, 0)])
def test_an_item_in_the_hud_is_whole_screen_pixels_and_the_lands_own(browser, server, w, h, dpr, touch, land):
    """In the bar, the inventory and the crafting an item is the small picture it is on the ground (11 art px), and
    an art pixel of it is a whole number of screen pixels: the land's own at the zoom the game starts with (3 CSS px,
    2 on a small phone), `land` here, where the slot has room for it. A slot's frame is whole screen pixels too. (The
    bar's icons were 1.84 CSS px a pixel on a desktop and 1.5 on a phone, in frames at 2, and on a phone the whole
    HUD was scaled to fit.) Where ten slots do not fit across, the frame's pixel is smaller by whole screen pixels;
    nothing is scaled, and nothing is moved by half its size onto a half pixel."""
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr, has_touch=touch, is_mobile=touch)
    try:
        g = Game(ctx.new_page(), server)
        g.join(f"px{random.randint(1000, 9999)}", 3)
        g.give(wood=5, stone=3, boat=1, bed=1, coop=1, plank=2, fiber=2, seed=1, egg=1, bread=1, torch=1, rope=1)
        goals = g.js("[...document.querySelectorAll('.goal .gi')].map((e) => e.getBoundingClientRect().width * devicePixelRatio / 11)")
        g.js("(() => { openCraft(); $('bag').style.display = 'block'; return 1; })()")
        g.sleep(900)                                             # (a phone fits its HUD every fifth of a second)
        m = g.js(HUD)
        whole = lambda v: abs(v - round(v)) < .02 and round(v) >= 1          # noqa: E731
        assert len(m["icons"]) > 60 and len(m["frames"]) > 60 and len(m["big"]) == 4
        assert all(whole(v) for v in m["icons"] + m["frames"] + m["big"] + m["vitals"]), m
        item, frame = {round(v) for v in m["icons"]}, {round(v) for v in m["frames"]}
        assert len(item) == 1 and len(frame) == 1 and m["art"] == "11x11", m
        assert item == {land} if land else max(item) * 11 <= max(frame) * 17.6, (item, frame)   # (no more than the frame's hole takes)
        assert len({round(v) for v in m["big"]}) == 1
        assert goals and all(abs(v - round(v)) < .05 and round(v) >= 1 for v in goals), goals   # (a phone's goals are a smaller panel)
        assert m["moved"] == "none,none,none" and m["fits"], m
        assert not g.errors
    finally:
        ctx.close()


# an icon's px, and the px of the sprite it is made from
ICON = """(name) => { const c = iconCanvas(name), d = c.getContext('2d').getImageData(0, 0, 16, 16).data, [img, x, y, w = 16, h = 16] = ICONS[name];
  const s = document.createElement('canvas'); s.width = w; s.height = h; const g = s.getContext('2d'); g.drawImage(IMG[img], x, y, w, h, 0, 0, w, h);
  const src = g.getImageData(0, 0, w, h).data, own = new Set(), out = {solid: 0, soft: 0, alien: 0, w, h};
  for (let i = 0; i < src.length; i += 4) if (src[i + 3] >= 128) own.add(src[i] << 16 | src[i + 1] << 8 | src[i + 2]);
  for (let i = 0; i < d.length; i += 4) { if (!d[i + 3]) continue; out.solid++;
    if (d[i + 3] !== 255) out.soft++; else if (!own.has(d[i] << 16 | d[i + 1] << 8 | d[i + 2])) out.alien++; }
  return out; }"""


def test_a_big_things_icon_is_made_smaller_by_whole_pixels(game):
    """A boat, a bed, a well, a coop are bigger than an icon: each n x n block of the sprite becomes one pixel, of a
    colour the sprite has, fully there or not at all (squeezed into 16 px, they were a blur of colours in between).
    A mailbox, 8 px of its cell, is its own pixels."""
    for name in ("boat", "bed", "plant", "well", "coop", "picnic_blanket", "mailbox"):
        m = game.js(ICON, name)
        assert m["solid"] > 40 and m["soft"] == 0 and m["alien"] == 0, (name, m)
    same = game.js("""(() => { const d = iconCanvas('mailbox').getContext('2d').getImageData(0, 0, 16, 16).data, [img, x, y, w, h] = ICONS.mailbox;
      const s = document.createElement('canvas'); s.width = w; s.height = h; const g = s.getContext('2d'); g.drawImage(IMG[img], x, y, w, h, 0, 0, w, h);
      const src = g.getImageData(0, 0, w, h).data; let n = 0, m = 0;
      for (let i = 0; i < src.length; i += 4) if (src[i + 3] >= 128) n++;
      for (let i = 0; i < d.length; i += 4) if (d[i + 3]) m++;
      return [n, m]; })()""")
    assert same[0] == same[1] and same[0] > 60, same


# every smooth round shape drawn on the game's canvas, and every row a pixel oval is filled with
ROUND = """() => { window.__round = 0; window.__rows = []; window.__in = 0;
  for (const f of ['arc', 'ellipse']) { const o = ctx[f]; ctx[f] = function (...a) { __round++; return o.apply(this, a); }; }
  const po = pixelOval; pixelOval = function (...a) { __in++; try { return po(...a); } finally { __in--; } };
  const fr = ctx.fillRect; ctx.fillRect = function (x, y, w, h) { if (__in) __rows.push([x, y, w, h]); return fr.call(this, x, y, w, h); };
  return 1; }"""


@pytest.mark.parametrize("zoom", [2, 3])
def test_smoke_shadows_and_glows_are_round_in_the_lands_pixels(game, zoom):
    """A creature's poof, a little dust, an orb's glow, the shadow under you and the one under a pile are rows of whole
    art pixels, on whole screen pixels: never a smooth circle or ellipse (they all were, among pixel art). A shadow
    is an oval, not a bar: its middle row is the widest."""
    game.js(f"zoom = {zoom}")
    game.give(wood=1)
    game.act("drop", item="wood", n=1)
    game.sleep(400)
    game.js(ROUND)
    x, y = game.pos()
    game.js(f"(() => {{ smoke({x + 2}, {y}, 8); smoke({x - 2}, {y}, 4, .4); return 1; }})()")
    game.sleep(700)
    game.js("drawOrb(120, 120, ORB, false)")
    rows = game.js("__rows")
    assert game.js("__round") == 0 and len(rows) > 400
    off = [r for r in rows if r[3] != zoom or r[2] % zoom or r[2] <= 0 or any(v != int(v) for v in r)]
    assert not off, off[:5]
    game.js("(() => { __rows.length = 0; ctx.fillStyle = '#000'; pixelOval(200, 200, 6, 2.5, 0, .5); return 1; })()")   # (the shadow under you)
    assert [r[2] // zoom for r in game.js("__rows")] == [8, 10, 12, 10, 8]
    assert not game.errors
