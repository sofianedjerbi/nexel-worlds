"""A thing held in the paw has no white border (#408, the owner: "some items in hands have weird white borders"). The
pack's item icons are stickers, a light rim round each for the bag's slots; the paw's 8 px picture of one (characters.js
biteIcon) kept that rim: wood, berries, a fruit held showed a white ring round them, at every zoom."""

import pytest

pytestmark = pytest.mark.e2e

# things held as their icon (not a tool gripped, not a block's cube), each a sticker in the pack's sheet
ITEMS = ["wood", "berries", "fruit", "fiber", "mushroom", "meat"]

# you drawn at zoom z (characters.js drawEntity, as the game draws you, on a canvas of your own: the frame drawn at once,
# no frame's timing in it), standing, facing us, with empty hands and holding `item`: the px `item` changes, [r, g, b]
PAW = """([item, z]) => { const p = ents.get('agent' + myId); p.fx = 0; p.fy = 1; p.moved = -1e9; p.swing = null; Target.aim = null; p.aimT = 0;
  p.lookD = null; p.lookT = -1e9; p.turnT = -1e9; const now = 140 * (8 * 9000 - (p.e.id * 3) % 8) + 1;   // (the idle breathing at its frame 0)
  const T = 16 * z, w = Math.round(64 * z), h = Math.round(96 * z), base = h - 24 * z;
  const sx = (x) => w / 2 - T / 2 + (x - p.x) * T, sy = Object.assign((y) => base + (y - p.y) * T, {up: (y) => base + (y - p.y) * T, apart: true});
  const shot = (sel) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); g.imageSmoothingEnabled = false;
    const keep = ctx, kz = zoom, ks = selected; ctx = g; zoom = z; selected = sel; myAction = null; try { drawEntity(p, sx, sy, T, now / 1000, now); } finally { ctx = keep; zoom = kz; selected = ks; }
    return g.getImageData(0, 0, w, h).data; };
  const a = shot(null), b = shot(item), px = [];
  for (let i = 0; i < a.length; i += 4) if (b[i + 3] > 128 && Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) + Math.abs(a[i + 3] - b[i + 3]) > 30) px.push([b[i], b[i + 1], b[i + 2]]);
  return px; }"""


@pytest.mark.parametrize("zoom", [2, 2.5, 3])
def test_a_thing_held_in_the_paw_has_no_white_border_at_any_zoom(game, zoom):
    """At zoom 2, 2.5 and 3, each sticker item held: it is drawn in your paw (px of it), and none of its px is the
    sticker's light rim (every channel over 225; what is light inside a thing, an egg's shell, is not on its edge)."""
    for item in ITEMS:
        px = game.js(PAW, [item, zoom])
        white = [p for p in px if min(p) > 225]
        assert len(px) > 10, f"{item} at zoom {zoom}: not in the paw ({len(px)} px of it)"
        assert not white, f"{item} at zoom {zoom}: {len(white)} of its {len(px)} px are the sticker's white rim: {white[:6]}"
