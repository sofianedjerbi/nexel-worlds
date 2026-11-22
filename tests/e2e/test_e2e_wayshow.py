"""The way out, as it is drawn (web/js/wayshow.js): behind land it is faint, and its key moves with you and the land."""

import pytest
from test_e2e_hd_phone import phone
from test_e2e_hd_sun import hd


def ridge(g):
    """A tunnel thirteen long under a hill of six, west to east, open at its east end, a ridge of nine three rows deep
    south of it (between the eye and the tunnel); you at its west end."""
    g.clear_area(20)                                                         # (the tunnel's mouth is past the meadow hd() clears)
    x, y = g.pos()
    g.stamp(-1, -1, ["." * 16] * 5, levels=["6" * 15 + "0", "6" + "0" * 15] + ["9" * 15 + "0"] * 3,
            roofs=["0" * 16, "0" + "6" * 13 + "000"] + ["0" * 16] * 3)
    g.rpc("dev_teleport", x=x + 1, y=y, z=0)
    g.arrive()
    g.rest()
    g.wait("WayShow.cur && !WayShow.busy && WayShow.dots > 0", 8000)
    g.rest()
    g.frames(3)


def test_behind_a_ridge_the_way_is_faint_and_through_the_window_it_is_whole(browser, server):
    """"Path rendering when hid by mountain": the dots were drawn over the land between the eye and the way. With
    the x-ray window open the tunnel is shown and its dots are whole; shut (as when you have walked out, or a hill
    stands between), the dots behind the ridge are two faint px each, and the arrow at the screen's edge stays."""
    g = hd(browser, server)
    ridge(g)
    n = g.js("[WayShow.hidden, WayShow.dots]")
    assert n[1] >= 20 and n[0] <= 3, n                                      # (the last tiles of the tunnel, past the window: behind the ridge)
    g.js("HdLook.nowin = true")
    g.wait("HdLook.win.a === 0", 4000)
    g.frames(3)
    n = g.js("[WayShow.hidden, WayShow.dots]")
    assert n[0] >= n[1] - 4, n                                              # (all but the last steps, out past the ridge's end)
    assert not g.errors


# each frame after the way's own painting: the key cap's place, and yours as your body is drawn (css px), an art px, your tile, the cap's words. The
# first two frames once you are off are slow (110 ms: a tile walked between two frames, as a phone's or a loaded machine's)
REC = """(() => { window.__rec = []; const f = WayShow.paint; WayShow.paint = function (...a) { const r = window.__rec, l = r[r.length - 1]; if (l && (l[3] !== r[0][3] || l[4] !== r[0][4]) && (window.__slow = (window.__slow || 0) + 1) <= 2) { const t = performance.now(); while (performance.now() - t < 110); }
  f.apply(this, a); const e = document.getElementById('waycap'), p = ents.get('agent' + myId);
  const m = /translate\\(([-\\d.]+)px, ([-\\d.]+)px\\)/.exec(e ? e.style.transform : ''), me = HdLook.screenOf(p.x + .5, p.y + .5, HdLook.level[2]);
  if (e && e.style.display === 'block' && m && me) window.__rec.push([+m[1] - me[0], +m[2] - me[1], a[2], p.x, p.y, e.innerHTML]); }; return 1; })()"""


def tunnel(g, north):
    g.clear_area(20)
    x, y = g.pos()
    if north:
        g.stamp(-1, -18, ["..."] * 20, levels=["000"] + ["404"] * 18 + ["444"], roofs=["000"] + ["040"] * 18 + ["000"])
        g.rpc("dev_teleport", x=x, y=y, z=0)
    else:
        g.stamp(-1, -1, ["." * 20] * 3, levels=["4" * 19 + "0", "4" + "0" * 19, "4" * 19 + "0"], roofs=["0" * 20, "0" + "4" * 17 + "00", "0" * 20])
        g.rpc("dev_teleport", x=x + 1, y=y, z=0)
    g.arrive()
    g.rest()
    g.wait("WayShow.cur && !WayShow.busy && document.getElementById('waycap') && document.getElementById('waycap').style.display === 'block'", 8000)


@pytest.mark.realtime
@pytest.mark.parametrize("north", [False, True])
@pytest.mark.parametrize("screen", ["desktop", "phone"])
def test_sprinting_along_the_way_its_key_moves_with_you_never_a_jump(browser, server, screen, north):
    """"Escape path render is buggy when sprinting: the key glitches up and down": the step's arrow was beside the
    next tile of the way, a tile on at each step (it ran back to you and leapt a tile ahead, ten times a second), and
    over and under that tile took turns as the keys' boxes came and went: 21 to 30 art px a frame. Now it is beside the
    tile a step ahead of you as you are drawn, its side kept: from one frame to the next it moves with you, within
    an art px, slow frames at its start too (the cap was placed against your body and name as the last frame drew them: it sat 30 px off, then leapt). A new
    way found as you set off is a new cap, its arrow turned: not a jump of the cap; nor is a block's key, that stays by its block, nor an arrow the
    other way (when the tunnel's end was no way out yet, the way shown was a stair cut south or a wall dug west: found again as you ran)."""
    ctx = None
    if screen == "phone":
        ctx, g = phone(browser, server)
    else:
        g = hd(browser, server)
    g.js("setOpt('names', true); setOpt('hints', true)")
    tunnel(g, north)
    g.js(REC)
    g.hold(["Shift", "ArrowUp" if north else "ArrowRight"], 1400)
    g.frames(2)
    rec = g.js("window.__rec")
    moved = abs(rec[-1][3] - rec[0][3]) + abs(rec[-1][4] - rec[0][4]) if rec else 0
    assert len(rec) > 20 and moved >= 8, (len(rec), moved)                 # (frames enough, and a sprint: tiles run)
    along = '<i class="%s go"></i>' % ("N" if north else "E")
    same = [(a, b) for a, b in zip(rec, rec[1:]) if a[5] == b[5] == along]      # (the step's arrow the way you run, from one frame to the next)
    assert len(same) > 15, [v[5] for v in rec]
    jump = max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) / a[2] - 1 / a[2] for a, b in same)      # (less the css px the cap's place is rounded to)
    assert jump <= 1, (jump, [[round(v[0] / v[2]), round(v[1] / v[2])] for v in rec[:16]])
    assert not g.errors
    if ctx:
        ctx.close()


# each frame: where you are, the finder busy, the way's first step and its blocks, what is shown (a block's key or a step's way), and
# whether the cell [x, y, z] is land (the tunnel's end)
FIRST = """([x, y, z]) => { window.__first = []; const rec = () => { const p = myPos(), r = WayShow.res, c = WayShow.cur;
  window.__first.push([p.x, p.y, !!WayShow.busy, r && r.path ? (r.path[1] || {}).d || null : null, r ? r.blocks : -1, c ? (c.now ? c.now.key : c.path[1].d) : null, solidAt(x, y, z)]); };
  const f0 = frame; frame = function (now) { f0(now); rec(); }; return 1; }"""


@pytest.mark.parametrize("sprint", [False, True])
def test_in_a_tunnel_open_at_its_end_the_way_out_is_along_it_from_the_first_frame(browser, server, sprint):
    """"In a tunnel whose open end leads out it offered a dig way (cut a stair south, dig the wall west) until you had
    run a tile or two": a way with blocks to break, found while the tunnel's end was shut, was kept while you stood on
    it (WayShow keeps a way that still holds), after the end was opened too. A way on foot always wins over one dug: a
    tunnel six long under a hill of four, its east end shut by a block, you at its west end, shown a way to dig (the
    hill west of you is one block thick); the end's block gone: from that frame the way goes east with no block to
    break, and so it is shown, standing and while you sprint."""
    g = hd(browser, server)
    g.js("setOpt('names', true); setOpt('hints', true)")
    g.clear_area(20)
    x, y = g.pos()
    rows, roofs = ["." * 20] * 3, ["0" * 20, "0" + "4" * 6 + "0" * 13, "0" * 20]
    g.stamp(-1, -1, rows, levels=["4" * 8 + "0" * 12, "4" + "0" * 6 + "4" + "0" * 12, "4" * 8 + "0" * 12], roofs=roofs)
    g.rpc("dev_teleport", x=x, y=y, z=0)
    g.arrive()
    g.wait("WayShow.cur && !WayShow.busy && WayShow.res.blocks > 0", 8000)        # (shut: a way to dig)
    assert g.js("WayShow.res.path[1].d") == "W"                                   # (the way to dig shown: the hill's end west of you is thinner)
    g.js(FIRST, [x + 6, y, 1])
    g.stamp(6, 0, ["."], levels=["0"], roofs=["0"])                              # (the end's block, gone)
    if sprint:
        g.hold(["Shift", "ArrowRight"], 700)
    else:
        g.frames(6)
    rec = [r for r in g.js("window.__first") if not r[6] and r[1] == y and x <= r[0] <= x + 5]      # (from the frame the end is open, in the tunnel)
    assert len(rec) >= 3, rec
    assert all(r[3] == "E" and r[4] == 0 and r[5] == "E" for r in rec), [r for r in rec if r[3] != "E" or r[4] or r[5] != "E"]            # (the way: east, along the tunnel, nothing to break; and so it is shown)
    assert not g.errors
