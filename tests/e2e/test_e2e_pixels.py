"""An item's pixels are the game's pixels: on the ground an art pixel of it is a pixel of the land, in the HUD a whole
number of screen pixels, the same as the frame it sits in. Nothing is squeezed to a size in between."""


import pytest
from game import Game, new_name

# a small icon's px against its icon's: how many are there, half there, of a colour the icon has not, near white
SMALL = """(name) => { const px = (c) => c.getContext('2d').getImageData(0, 0, c.width, c.height).data, d = px(ghostIcon(name)), src = px(iconCanvas(name));
  const own = new Set(), out = {solid: 0, soft: 0, alien: 0, white: 0};
  for (let i = 0; i < src.length; i += 4) if (src[i + 3] >= 128) own.add(src[i] << 16 | src[i + 1] << 8 | src[i + 2]);
  for (let i = 0; i < d.length; i += 4) { if (!d[i + 3]) continue; out.solid++;
    if (d[i + 3] !== 255) out.soft++; else if (!own.has(d[i] << 16 | d[i + 1] << 8 | d[i + 2])) out.alien++;
    if ((ICONS[name][0] === 'items' || name === 'pickaxe') && Math.min(d[i], d[i + 1], d[i + 2]) > 225) out.white++; }
  return out; }"""


def test_a_small_icon_is_made_of_its_icons_own_colours_by_whole_pixels(game):
    """A pile, what hops out of a creature and what flies up into your hands are small icons of 11 art px, made from
    the 16 px ones by whole pixels (the HD look lays them on the land a px a px: hd.js). A small icon is made of its
    icon's own colours, without the white sticker edge."""
    for name in ("wood", "axe", "torch", "pickaxe", "stone", "spear"):   # (not an egg: its glint is white)
        m = game.js(SMALL, name)
        assert m["solid"] > 8 and m["soft"] == 0 and m["alien"] == 0 and m["white"] == 0, (name, m)
    assert [game.js(f"[ghostIcon('{n}').width, ghostIcon('{n}').height]") for n in ("wood", "axe")] == [[11, 11], [11, 11]]
    assert not game.errors


# every item icon in the HUD and its slot's frame: screen pixels to an art pixel, and whether anything scales it
HUD = """() => { const d = devicePixelRatio, out = {};
  const px = (sel, art) => [...document.querySelectorAll(sel)].filter((e) => e.offsetWidth).map((e) => { const r = e.getBoundingClientRect(); return [r.width * d / art, r.height * d / art]; }).flat();
  out.icons = px('#hotbar .slot:not(.sel) canvas', 11); out.selicon = px('#hotbar .slot.sel canvas', 11);   // (the slot in hand: 34 art px, lifted, its icon maybe a screen px bigger an art px: ui.js)
  out.art = [...new Set([...document.querySelectorAll('#hotbar .slot canvas')].map((c) => c.width + 'x' + c.height))].join();
  out.frames = px('#hotbar .slot:not(.sel)', 30); out.selframe = px('#hotbar .slot.sel', 34);
  const sel = document.querySelector('#hotbar .slot.sel'); out.lift = sel ? parseFloat(getComputedStyle(sel).transform.split(',')[5]) * d : 0;
  out.bag = [...px('#bag canvas', 16), ...px('#bag .cell', 18), parseFloat(getComputedStyle($('bag')).fontSize) * d / 9];           // (the inventory: the same, at its own)
  out.card = [...px('#goals .gi', 11), ...px('#goals .gc', 13), parseFloat(getComputedStyle($('goals')).fontSize) * d / 6];         // (the goals' card)
  out.big = [...px('#craft canvas', 16), ...px('#craft .cell', 18), parseFloat(getComputedStyle($('craft')).fontSize) * d / 9];   // (the recipe book: icons, cells and the font, at its one pixel)
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
        g.join(new_name("px"), 3)
        g.give(wood=5, stone=3, boat=1, bed=1, coop=1, plank=2, fiber=2, seed=1, egg=1, bread=1, torch=1, rope=1)
        g.js("toggleGoals()")                                    # (the goals' card is away unless asked for: G)
        m0 = g.js(HUD)                                           # (...measured before the book covers it)
        g.js("(() => { openCraft(); toggleBag(); return 1; })()")
        g.sleep(900)                                             # (a phone fits its HUD every fifth of a second)
        m = g.js(HUD)
        whole = lambda v: abs(v - round(v)) < .02 and round(v) >= 1          # noqa: E731
        assert len(m["icons"]) >= 14 and len(m["frames"]) >= 18 and len(m["selicon"]) in (0, 2) and len(m["selframe"]) == 2 and m["lift"] < 0 and len(m["big"]) >= 30 and len(m["bag"]) > 100 and len(m0["card"]) >= 12
        assert all(whole(v) for v in m["icons"] + m["frames"] + m["selicon"] + m["selframe"] + [-m["lift"]] + m["big"] + m["vitals"] + m["bag"] + m0["card"]), (m, m0["card"])
        assert len({round(v) for v in m["bag"]}) == 1 and len({round(v) for v in m0["card"]}) == 1          # (each in one pixel size)
        item, frame = {round(v) for v in m["icons"]}, {round(v) for v in m["frames"]}
        assert len(item) == 1 and len(frame) == 1 and m["art"] == "11x11", m
        assert {round(v) for v in m["selframe"]} == frame and {round(v) for v in m["selicon"]} <= {max(item), max(item) + 1}, m   # (the slot in hand: the same frame pixel, 2 art px more each side; its icon no smaller)
        assert max(m["selicon"], default=0) * 11 <= max(frame) * 24, m                                          # (...in its frame's hole)
        assert item == {land} if land else max(item) * 11 <= max(frame) * 17.6, (item, frame)   # (no more than the frame's hole takes)
        assert len({round(v) for v in m["big"]}) == 1 and (not land or {round(v) for v in m["big"]} == {land + (1 if touch else 0)})   # (one pixel: the land's)
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


def test_the_tools_have_no_white_edge(game):
    """The pack's icons have a white ring round them, a sticker's (and the pickaxe was drawn with one). The tools
    are shown without it, as the sword and the spear always were: in the bar, the book and the inventory no px of a
    tool is near white, and the tool is still there (the wood keeps its ring: only the tools were asked for)."""
    count = """(n) => { const d = iconCanvas(n).getContext('2d').getImageData(0, 0, 16, 16).data; let white = 0, solid = 0;
      for (let o = 0; o < d.length; o += 4) if (d[o + 3] >= 128) { solid++; if (Math.min(d[o], d[o + 1], d[o + 2]) > 225) white++; }
      return [white, solid]; }"""
    for tool in ("axe", "pickaxe", "hoe", "watering_can", "sword", "spear"):
        white, solid = game.js(count, tool)
        assert white == 0 and solid >= 20, tool
    assert game.js(count, "wood")[0] > 20
    game.give(axe=1)
    slot = game.js("""(() => { const i = slots.indexOf('axe'), c = i >= 0 && [...document.querySelectorAll('#hotbar .slot')][i].querySelector('canvas'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let white = 0;
      for (let o = 0; o < d.length; o += 4) if (d[o + 3] >= 128 && Math.min(d[o], d[o + 1], d[o + 2]) > 225) white++; return [slots[i], white]; })()""")
    assert slot == ["axe", 0]                    # (in whichever slot it landed: the empty hand's is kept for last, ui.js)
