"""The HD look's sheet of paints (vox_style_glsl.js AW, vox_style.js slot): sprinting about, every face is drawn with
its own paint, on a desk's big screen and on the small sheet of a small screen or a phone. The owner, sprinting up the
spawn hill on a desk: "all textures are fucked up": grass tops drawn as stone, stone fronts as grass, rows of the same
tuft. The land asked for more than the sheet's paints: the sheet was emptied and made again from none over and over
(spills), a paint was put in a place the land shown still named (overs), and faces were drawn with other paints. None
of that, on any sheet: and the land made again from none is the land as it was, px for px."""

import base64
import os
from pathlib import Path

import pytest

from conftest import Game, new_name

# the share of the land's px that differ between the picture as it is and as it was (window.__was), from the lower of the two
# pictures' sky lines down (window.__line, canvas px): the land, not the sky over it (the land made again from none put the far
# land's edge, and the sky's line with it, a few px elsewhere: 1.1 to 1.8 % of a desk's px, three in four of them the sky's blue)
LINE = "(() => Math.ceil(HdLook.sky(0).line * cv.width / innerWidth))()"
DIFF = """(() => { const a = window.__was, b = HdLook.read(0, 0, cv.width, cv.height).data, y0 = Math.max(window.__line, Math.ceil(HdLook.sky(0).line * cv.width / innerWidth)) + 2; let n = 0;
  for (let i = y0 * cv.width * 4; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 24) n++; return n / (a.length / 4 - y0 * cv.width); })()"""
# where they are, when they are too many: the share of each eighth of the screen from the top, and of them how many were blue (water)
WHERE = """(() => { const a = window.__was, b = HdLook.read(0, 0, cv.width, cv.height).data, W = cv.width, H = cv.height, band = new Array(8).fill(0); let blue = 0, n = 0;
  for (let i = 0; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 24) { n++; band[Math.min(7, Math.floor((i / 4 / W) / H * 8))]++; if (a[i + 2] > a[i] + 20) blue++; }
  return {bands: band.map((v) => +(v / (W * H / 8)).toFixed(4)), blue: n ? +(blue / n).toFixed(2) : 0}; })()"""

# the pictures, before, after and where they differ (red), saved to E2E_SHOTS when the bound is broken: what changed shows in the run's artifact (#111)
# the eye as a picture is taken (#111: once the picture before was sky down to 7/8 of the screen, no land in it, and every wait held):
# the camera (pitch, want), the sky's line and the land's edge (canvas px), the eye's level, the screen's height
EYE = "(() => { const s = HdLook.sky(0); return {cam: {...HdLook.cam}, line: s.line, edge: s.edge, level: HdLook.level, h: cv.height}; })()"
PNG = """(which) => { const W = cv.width, H = cv.height, now = HdLook.read(0, 0, W, H).data, was = window.__was, c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d'), im = x.createImageData(W, H), d = im.data;
  for (let i = 0; i < d.length; i += 4) { const diff = Math.abs(was[i] - now[i]) + Math.abs(was[i + 1] - now[i + 1]) + Math.abs(was[i + 2] - now[i + 2]) > 24;
    const s = which === 'was' ? was : now; if (which === 'diff') { d[i] = diff ? 255 : s[i] / 3; d[i + 1] = diff ? 0 : s[i + 1] / 3; d[i + 2] = diff ? 0 : s[i + 2] / 3; } else { d[i] = s[i]; d[i + 1] = s[i + 1]; d[i + 2] = s[i + 2]; } d[i + 3] = 255; }
  x.putImageData(im, 0, 0); return c.toDataURL('image/png'); }"""

DESK, SMALL = {"viewport": {"width": 1920, "height": 1080}}, {"viewport": {"width": 960, "height": 540}}
PHONE = {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 3, "is_mobile": True, "has_touch": True}
# (the sheet as the game has it, 16384 paints, and one of 4096 forced (SHEET_AW), too small for the land: then it is emptied and the land
#  made again from none, and narrower if it must (vox_style_land.js), but no face is ever drawn with a paint that is not its own)
SCREENS = {"desk": (DESK, None), "small": (SMALL, None), "phone": (PHONE, None), "small_tiny_sheet": (SMALL, 1024), "phone_tiny_sheet": (PHONE, 1024)}


@pytest.mark.parametrize("screen", list(SCREENS))
def test_sprinting_about_every_face_keeps_its_own_paint(browser, server, screen):
    kw, aw = SCREENS[screen]
    page = browser.new_page(**kw)
    if aw:
        page.add_init_script(f"window.SHEET_AW = {aw}")
    g = Game(page, server)
    g.join(new_name(), 3)
    g.js("setOpt('names', false); setOpt('hints', false); setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    # (the picture's density held as it is: on a slow runner, state.js slowFrame dropped the phone's from 2 to 1 between the two
    # pictures, and a picture of 1688 rows was read against one of 844, the sky magnified over the land: #111)
    g.js("(() => { slowFrame = () => {}; return 1; })()")
    assert g.js("VoxStyleGLSL.AW") == (aw or 2048)
    g.rpc("dev_creatures", clear=60)
    g.hour(.3, still=True)
    g.rest()
    for key in ("d", "w", "a", "s"):                              # (a run each way: new land comes in at every step)
        g.hold(["Shift", key], 2500)
        g.rest()
    w = g.js("HdLook.work")
    assert aw or (w["overs"] == 0 and w["spills"] == 0 and w["wipes"] == 0), w    # (the game's sheet: never full; one too small is emptied and the land made again, and a paint asked for with the sheet shown full takes a place of its own, vox_style.js CAP: never drawn wrong)
    assert g.js("HdLook.raw()") == 0                               # (no px from an empty paint)
    g.rpc("dev_creatures", clear=60)
    g.rest()
    g.until("!HdLook.busy && HdLook.bare() === 0")
    # (the land alone, HdLook.landOnly: nothing that stands or walks. A tree's sway, your own idle frame and their shadows were not the same
    #  frame in the two pictures: 1 to 5 % of a phone's px, one run in twenty-five, more on a busy machine: every px of land the same)
    g.js("(() => { HdLook.landOnly = true; return 1; })()")
    g.frames(3)
    g.js(f"(() => {{ window.__was = HdLook.read(0, 0, cv.width, cv.height).data; window.__wh = [cv.width, cv.height]; window.__line = {LINE}; return 1; }})()")
    box0 = g.js(f"[HdLook.box, HdLook.work, {EYE}]")
    g.js("HdLook.forget()")                                        # the land made again, its paints from none
    g.rest()
    g.until("!HdLook.busy && HdLook.bare() === 0")
    g.frames(3)
    assert g.js("window.__wh") == g.js("[cv.width, cv.height]"), ("the picture changed size between the two", g.js("window.__wh"), g.js("[cv.width, cv.height]"))
    d = g.js(DIFF)
    if d >= .01 and os.environ.get("E2E_SHOTS"):
        out = Path(os.environ["E2E_SHOTS"]) / f"sheet_{screen}"
        out.mkdir(parents=True, exist_ok=True)
        for which in ("was", "now", "diff"):
            (out / f"{which}.png").write_bytes(base64.b64decode(g.js(PNG, which).split(",", 1)[1]))
        (out / "info.txt").write_text(repr((d, g.js(WHERE), box0, g.js(f"[HdLook.box, HdLook.work, myPos(), HdLook.hid, HdLook.why, {EYE}]"))))
    assert d < .01, (d, g.js(WHERE), box0, g.js(f"[HdLook.box, HdLook.work, {EYE}]"))                                             # the same land, px for px (a face drawn with another paint: a tile's worth of px each)
    assert not g.errors
