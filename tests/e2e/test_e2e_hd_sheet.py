"""The HD look's sheet of paints (vox_style_glsl.js AW, vox_style.js slot): sprinting about, every face is drawn with
its own paint, on a desk's big screen and on the small sheet of a small screen or a phone. The owner, sprinting up the
spawn hill on a desk: "all textures are fucked up": grass tops drawn as stone, stone fronts as grass, rows of the same
tuft. The land asked for more than the sheet's paints: the sheet was emptied and made again from none over and over
(spills), a paint was put in a place the land shown still named (overs), and faces were drawn with other paints. None
of that, on any sheet: and the land made again from none is the land as it was, px for px."""

import pytest

from conftest import Game, new_name

# the share of the land's px that differ between the picture as it is and as it was (window.__was)
DIFF = """(() => { const a = window.__was, b = HdLook.read(0, 0, cv.width, cv.height).data; let n = 0;
  for (let i = 0; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 24) n++; return n / (a.length / 4); })()"""

DESK, SMALL = {"viewport": {"width": 1920, "height": 1080}}, {"viewport": {"width": 960, "height": 540}}
PHONE = {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 3, "is_mobile": True, "has_touch": True}
# (the sheet as the game has it, 16384 paints, and one of 4096 forced (SHEET_AW), too small for the land: then it is emptied and the land
#  made again from none, and narrower if it must (vox_style_land.js), but no face is ever drawn with a paint that is not its own)
SCREENS = {"desk": (DESK, None), "small": (SMALL, None), "phone": (PHONE, None), "small_tiny_sheet": (SMALL, 1024), "phone_tiny_sheet": (PHONE, 1024)}


@pytest.mark.realtime
@pytest.mark.parametrize("screen", list(SCREENS))
def test_sprinting_about_every_face_keeps_its_own_paint(browser, server, screen):
    kw, aw = SCREENS[screen]
    page = browser.new_page(**kw)
    if aw:
        page.add_init_script(f"window.SHEET_AW = {aw}")
    g = Game(page, server)
    g.join(new_name(), 3)
    g.js("setOpt('names', false); setOpt('hints', false); setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
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
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    # (the land alone, HdLook.landOnly: nothing that stands or walks. A tree's sway, your own idle frame and their shadows were not the same
    #  frame in the two pictures: 1 to 5 % of a phone's px, one run in twenty-five, more on a busy machine: every px of land the same)
    g.js("(() => { HdLook.landOnly = true; return 1; })()")
    g.frames(3)
    g.js("(() => { window.__was = HdLook.read(0, 0, cv.width, cv.height).data; return 1; })()")
    box0 = g.js("[HdLook.box, HdLook.work]")
    g.js("HdLook.forget()")                                        # the land made again, its paints from none
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    g.frames(3)
    d = g.js(DIFF)
    assert d < .01, (d, box0, g.js("[HdLook.box, HdLook.work]"))                                             # the same land, px for px (a face drawn with another paint: a tile's worth of px each)
    assert not g.errors
