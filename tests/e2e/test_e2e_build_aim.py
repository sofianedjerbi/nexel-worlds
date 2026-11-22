"""Build mode by mouse: the cursor is the block under the pointer, and its box is drawn round the pointer, whatever the
eye's pitch (36 degrees in the open, steeper with land south over your head, up to 58 in a dip) and the land's height."""

import json

import pytest

from game import Game, new_name

pytestmark = pytest.mark.e2e

# For a grid of pointer places round you: the pointer moved there (the game's own mousemove), two frames drawn; then
# the build cursor's cell, and the boxes drawn this frame. -> the places where the cursor's box is not round the pointer
AIM = r"""async ([dx0, dx1, dy0, dy1, step]) => {
  const raf = () => new Promise((r) => requestAnimationFrame(r)), s = myPos(), z = myZ(s.x, s.y), me = HdLook.screenOf(s.x + .5, s.y + .5, z);
  const t0 = HdLook.screenOf(s.x, s.y, z), t1 = HdLook.screenOf(s.x + 1, s.y, z), W = t1[0] - t0[0], bad = [], P = HdLook.art(), B = P && P.body;
  let n = 0;
  for (let dy = dy0; dy <= dy1; dy += step) for (let dx = dx0; dx <= dx1; dx += step) {
    const mx = me[0] + dx * W, my = me[1] + dy * W;
    if (B && mx >= B.x - 4 && mx <= B.x + B.w + 4 && my >= B.y - 4 && my <= B.y + B.h + 4) continue;   // (your own body: nothing is boxed on it)
    cv.dispatchEvent(new MouseEvent('mousemove', {clientX: mx, clientY: my, bubbles: true}));
    Target.drew = null; for (let i = 0; i < 60 && !(Target.drew && Target.drew.length); i++) await raf(); await raf();
    const a = Build.S.at, d = (Target.drew || []).filter((c) => c.x === a.x && c.y === a.y && c.r), u = P.u;
    n++;
    if (!d.length || !d.some((c) => c.line > 0 && mx >= c.r.x - u && mx <= c.r.x + c.r.w + u && my >= c.r.y - u && my <= c.r.y + c.r.h + u))
      bad.push({m: [Math.round(dx * 10) / 10, Math.round(dy * 10) / 10], at: [a.x - s.x, a.y - s.y, Build.level()], drew: (Target.drew || []).map((c) => [c.x - s.x, c.y - s.y, c.z, c.line, c.r && [c.r.x, c.r.y, c.r.w, c.r.h].map(Math.round)]), mouse: [Math.round(mx), Math.round(my)]});
  }
  return {n, bad: bad.slice(0, 6), nbad: bad.length, pitch: HdLook.cam.pitch};
}"""

# terraces east of you, one level a step, past a flat floor at your own height (land a level over you on more sides is a dip: the eye from above)
TERRACE = ["0000000012345"] * 9


LV = "0123456789ABC"                         # (a level as dev_stamp has it)


@pytest.mark.parametrize("scene, base, phone", [("open", 4, False), ("open", 0, True), ("cliff", 4, False), ("dip", 4, False), ("dip", 11, False), ("dip", 4, True)])
def test_the_build_cursor_is_the_block_under_the_pointer_and_boxed_there_at_any_pitch(browser, server, scene, base, phone):
    """The owner, in build mode on a plateau, standing in a dip one level deep: "what the hell am I selecting? I am
    selecting 2-3 blocks in front of me but nothing is highlighted". Its box was folded onto the dip's rim by your feet
    (hd_level.js `wall`: a cell of the land south of you over your feet was drawn on the wall between the eye and you,
    however far past that wall it was); and on terraces, by a cliff, the pointer on a block's side picked a block two
    tiles off (each tile's top at the cursor's height, no sides). The cursor is the first block the pointer's ray meets
    (mouse.js rayHit), and its box is round the pointer, at 36 degrees, 54 (land south over your head), 58 (a dip: hd.js STEEP)."""
    view = {"width": 390, "height": 844} if phone else {"width": 1440, "height": 900}
    g = Game(browser.new_page(viewport=view, device_scale_factor=3 if phone else 1), server)
    g.join(new_name(), 3)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    g.clear_area(12)
    lv = [[base + int(c) for c in row] for row in (TERRACE if scene == "open" or (scene == "dip" and base < 6) else ["0" * 13] * 9)]
    if scene == "dip":                      # a plateau a level over you all round (the owner's): the eye looks from above
        lv = [[c + 1 for c in row] for row in lv]
        lv[4][6] = base
    g.stamp(-6, -4, ["." * 13] * 9, levels=["".join(LV[c] for c in r) for r in lv])
    if scene == "cliff":                    # land 3 levels over you 3 tiles south, a step up to it: the eye looks down steeper to see you
        g.stamp(-3, 2, ["." * 7] * 3, levels=[LV[base] * 3 + LV[base + 1] + LV[base] * 3, LV[base + 3] * 7, LV[base + 3] * 7])
    g.rest()
    g.press("z")
    g.wait("Build.on")
    g.rest()
    pitch = g.js("HdLook.cam.pitch")
    want = {"open": (45, 53) if phone else (35, 37), "cliff": (45, 58.1), "dip": (57.9, 58.1)}[scene]
    assert want[0] <= pitch <= want[1], (scene, pitch)
    r = g.js(AIM, [-3, 3, -2, 3, 0.45] if phone else [-4, 4, -2, 3, 0.45])
    assert r["n"] > 50 and r["nbad"] == 0, (scene, json.dumps(r))
    assert not g.errors
