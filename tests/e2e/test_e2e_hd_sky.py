"""The HD look's sky (hd.js `eyeLine`, hd_view.js `skyOf`): fixed to the eye. Its horizon is where level ground at the
eye's own level meets it (or the lowest land ahead, if lower: from a hill top): the pitch and the screen, and how high the
eye is over that land. Land, however tall, covers it; it never moves with the land in front of you.
(The owner: "if a big mountain is behind the player, the skybox bumps up in an unnatural way": the sky came down to the
lowest of the land's skylines north of you, eased: walking to a ridge the whole sky, sun, clouds and far hills, slid up
58 art px, a px or two a frame, and down again walking along it.)"""

import pytest

from game import Game, new_name

# each frame: the sky's line (art px from the picture's top), the eye's pitch, where you are
REC = """() => { window.__sk = []; window.__on = true; const f = () => { __sk.push([HdLook.sky(0).line / zoom, HdLook.cam.pitch, myPos().x, myPos().y]);
  if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def ridge(g, cx, cy, z0, r=8, rx=30, step=4):
    """A stepped ridge 61 tiles across and 17 deep, 36 levels high at its crest."""
    by = {}
    for j in range(-r, r + 1):
        for i in range(-rx, rx + 1):
            by.setdefault(z0 + max(1, (r + 1 - max(-(-abs(i) * r // rx), abs(j))) * step), []).append([cx + i, cy + j])
    for h, t in by.items():
        g.rpc("dev_col", tiles=t, col=[h])


@pytest.mark.realtime
def test_walking_past_a_tall_mountain_the_sky_does_not_move(browser, server):
    g = Game(browser.new_page(viewport={"width": 1440, "height": 900}), server)
    g.join(new_name("sky"), 3)
    g.js("setOpt('names', false); setOpt('hints', false)")
    g.rpc("dev_creatures", clear=60)
    x, y = g.pos()
    z0 = g.js(f"topAt({x}, {y})")
    # (all the land the sky's line looks at made one meadow: the lowest land ahead (hd.js lowAhead) is read 6 to 64 tiles
    #  north of you, 24 east and west. Only 34 north were laid out, by dev_col, which leaves what stands: a pond, a pit
    #  another test dug, out there lowered the line a px as you walked, every run after the x-ray tests; and a tree at
    #  (x + 23, y) stopped the walk west, two runs in eight; and the eye looks down more steeply over land south of you
    #  taller than you (hd.js clear, out to 24 rows): another test's plateau south of the walk tilted it, the line with it)
    g.stamp(-60, -72, ["." * 121] * 106)
    g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-72, 34) for i in range(-60, 61)], col=[z0])
    ridge(g, x, y - 18, z0)
    g.rest()
    flat = g.js("HdLook.sky(0).line / zoom")
    for sx, sy, key, ms in ((x, y + 8, "ArrowUp", 2400), (x + 24, y, "ArrowLeft", 4000)):   # to the ridge's foot; along it, its columns' heights coming and going north of you
        g.rpc("dev_teleport", x=sx, y=sy, z=z0); g.arrive(); g.rest()
        g.js(REC)
        g.page.keyboard.down(key)
        g.page.wait_for_timeout(ms)
        g.page.keyboard.up(key); g.rest()
        rec = g.js("(() => { __on = false; return __sk; })()")
        moved = abs(rec[-1][2] - sx) + abs(rec[-1][3] - sy)
        assert moved >= 8, (key, moved)
        steps = [(abs(b[0] - a[0]), a, b) for a, b in zip(rec, rec[1:]) if a[1] == b[1]]     # (frames with the same pitch)
        assert len(steps) > 30 and max(s[0] for s in steps) < 1, (key, max(steps))
        assert {r[0] for r in rec} == {flat}, (key, sorted({r[0] for r in rec}), flat)    # (the meadow's, before the ridge was there)
    # a hill top: the land round it is lower, and drops away past the bend lower on the screen: the sky's line comes
    # down to where that land meets it (hd.js lowAhead). It stayed where ground at your level would meet it, and the
    # band between was the backdrop's flat colours ("that blue mass behind": test_e2e_hd_horizon.py)
    g.rpc("dev_col", tiles=[[x + 20 + i, y + 2 + j] for j in range(-2, 3) for i in range(-2, 3)], col=[z0 + 12])
    g.rpc("dev_teleport", x=x + 20, y=y + 2, z=z0 + 12); g.arrive(); g.rest()
    g.wait(f"HdLook.low === {z0} && Math.abs(HdLook.sky(0).line / zoom - HdLook.line[1] - 2) < 1", 5000)   # (eased down as the eye goes up)
    assert g.js("HdLook.sky(0).line / zoom") > flat
