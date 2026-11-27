"""Every setting of the Picture page changes the picture (menu.js MENU_PAGES "Picture"): each is set one way and the
other on the same scene and the screen read twice each way. The two settings' pictures differ by more than each
differs from itself a moment later (clouds, water), or the setting changes how much the picture moves (the water's
shimmer). A setting that does nothing in the HD look fails here. (The owner: "curved world option does almost nothing":
it only took the sky away, the land stayed bent. Shake on a hard fall moved a camera the HD look does not use.)"""

import base64
import os

import pytest

from test_e2e_hd_sun import hd

SHOTS = os.environ.get("PICTURE_SHOTS")      # (a folder: each setting's pictures are kept there, to be looked at)
# share of the px of two screenshots that differ (any channel by more than T; in r, CSS px [x0, y0, x1, y1], or all): both PNGs read by the page itself
DIFF = """async ([a, b, r, T]) => { const im = async (s) => { const i = new Image(); i.src = 'data:image/png;base64,' + s; await i.decode(); const c = document.createElement('canvas'); c.width = i.width; c.height = i.height; const g = c.getContext('2d'); g.drawImage(i, 0, 0); return g.getImageData(0, 0, c.width, c.height).data; };
  const A = await im(a), B = await im(b), W = innerWidth, H = A.length / 4 / W, [x0, y0, x1, y1] = r ? r.map(Math.round) : [0, 0, W, H]; let n = 0;
  for (let y = Math.max(0, y0); y < Math.min(H, y1); y++) for (let x = Math.max(0, x0); x < Math.min(W, x1); x++) { const i = (y * W + x) * 4; if (Math.abs(A[i] - B[i]) > T || Math.abs(A[i + 1] - B[i + 1]) > T || Math.abs(A[i + 2] - B[i + 2]) > T) n++; }
  return n / Math.max(1, (Math.min(H, y1) - Math.max(0, y0)) * (Math.min(W, x1) - Math.max(0, x0))); }"""
# where tiles dx0..dx1, dy0..dy1 from you are on the screen, CSS px [x0, y0, x1, y1] (a setting that acts on a small part of it is read there)
ROI = """([dx0, dy0, dx1, dy1]) => { const p = myPos(), xs = [], ys = []; for (const [dx, dy] of [[dx0, dy0], [dx1, dy0], [dx0, dy1], [dx1, dy1]]) { const a = HdLook.screenOf(p.x + dx, p.y + dy, topAt(p.x + dx, p.y + dy)); xs.push(a[0]); ys.push(a[1]); }
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; }"""
# the picture only: the land's canvas and the game's (names, hearts, marks), none of the page's panels (the welcome fades out meanwhile)
BARE = "(() => { const s = document.createElement('style'); s.textContent = 'body > :not(#c):not(#hd) { visibility: hidden !important; }'; document.head.appendChild(s); return 1; })()"
FX = "(() => { const p = myPos(); burst(p.x + 3, p.y - 1, 'hit', 30); smoke(p.x + 4, p.y - 1, 12); return 1; })()"
# (words held a third of a second into their rise: they last 1.4 s, and a slow machine's frames and screenshot took longer)
FLOAT = "(() => { const p = myPos(), f = {x: p.x, y: p.y, text: '+5 wood', color: '#fff1a8'}; Object.defineProperty(f, 't', {get: () => performance.now() / 1000 - .3}); floats.push(f); return 1; })()"
QUAKE = "(() => { window.__fs = window.__fs || FALL.shake[1]; FALL.shake[1] = 60; fallQuake = opt('shake') ? {t0: performance.now() - 100, amp: 40} : null; return 1; })()"   # (a shake held a minute: on the picture whenever it is read)
# (the glide held half way: it is the canvas's own animation, 140 ms of the browser's clock, over before a slow
#  machine's frames come; held, it is on the picture whenever it is read, as the shake and the words are)
ZOOMING = "(() => { zoomBy(1); for (const a of [cv, HdView.el].filter(Boolean).flatMap((e) => e.getAnimations())) { a.pause(); a.currentTime = ZOOM.ms / 2; } return 1; })()"
UNGLIDE = "(() => { for (const a of [cv, HdView.el].filter(Boolean).flatMap((e) => e.getAnimations())) a.finish(); return 1; })()"   # (let go: the zoom goes on to its end)
# each setting: [its key, one value, the other, what is done before each picture (js), the hour, where it is read (tiles from you; None: all of it),
# by how much a px differs (a channel, 0..255: the water's moving light is faint by design, 6)].
# The hour: .3 morning (long shadows), .9 night. POND: the pond's tiles; SPOT: where the particles fly, east of you; HEAD: where the words rise over you (not you: you breathe); WALLS: the walls and stones and their shadows
POND, SPOT, HEAD, WALLS = [2, -6, 10, -2], [2, -4, 6, 1], [-1, -5, 2, -1], [-9, -4, 0, 2]
CASES = [
    ["night", 0, 100, None, .9, None],
    ["particles", "all", "none", FX, .3, SPOT],
    ["view", 9, 37, None, .3, None],
    ["curve", True, False, None, .3, None],
    ["depth", True, False, None, .3, WALLS],
    ["clearwater", True, False, None, .3, POND],
    ["shimmer", True, False, None, .3, POND, 6],
    ["shake", True, False, QUAKE, .3, None],
    ["glide", True, False, ZOOMING, .3, None],
    ["floats", True, False, FLOAT, .3, HEAD],
    ["shadows", 100, 0, None, .3, WALLS],
    ["shadowlen", 100, 200, None, .3, WALLS],
]


@pytest.mark.animated                                  # (the Smooth zoom setting: its glide is what changes the picture: not with less motion, pages.py)
def test_every_picture_setting_changes_the_picture(browser, server):
    """Each setting of the Picture page (Zoom is the zoom: the other tests'), on a scene with all they act on: walls
    and stones (shadows, depth), a pond with a bed (clear water, shimmer), the land north (view distance, curved world),
    what flies (particles), what is written over you (floats), a fall's shake, a zoom's glide, the night (light at night)."""
    g = hd(browser, server)
    g.stamp(-6, -2, ["W.M..W", "......", ".W..M."])                         # walls and stones west of you: shadows, and nothing that sways (trees do: a picture apart from itself)
    g.stamp(2, -6, ["~" * 8] * 4)                                           # a pond north-east, its bed two deep
    g.rest()
    g.js(BARE)
    listed = g.js("MENU_PAGES.find((p) => p[0] === 'Picture')[1].filter((r) => r.name !== 'Zoom').map((r) => r.key)")
    assert sorted(listed) == sorted(c[0] for c in CASES), listed          # (a setting added to the page is added here)
    out = {}
    try:
        for key, a, b, before, hour, roi, *tol in CASES:
            g.rpc("dev_time", phase=hour)
            pics = []
            for v in (a, a, b, b):
                g.js(f"(() => {{ setOpt('{key}', {js(v)}); zoom = ZOOM.to = 3; return 1; }})()")
                g.rest()
                if before:
                    g.js(before)
                    g.rest(frames=4)
                pics.append(g.page.screenshot())
                if before == ZOOMING:
                    g.js(UNGLIDE)
            if SHOTS:
                for i, p in enumerate(pics):
                    open(os.path.join(SHOTS, f"{key}_{['a', 'a2', 'b', 'b2'][i]}.png"), "wb").write(p)
            e = [base64.b64encode(p).decode() for p in pics]
            r = g.js(ROI, roi) if roi else None
            ab, na, nb = (round(g.js(DIFF, q + [r, tol[0] if tol else 24]), 4) for q in ([e[0], e[2]], [e[0], e[1]], [e[2], e[3]]))
            out[key] = [ab, na, nb] + ([[round(v) for v in r]] if r else [])
            g.js(f"setOpt('{key}', OPT_DEFAULT['{key}'])")
    finally:
        g.js("(() => { for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); setOpt('names', false); setOpt('hints', false); zoom = ZOOM.to = 3; if (window.__fs) FALL.shake[1] = window.__fs; fallQuake = null; floats = []; return 1; })()")
    if SHOTS:
        open(os.path.join(SHOTS, "diffs.txt"), "w").write(repr(out))
    # (the two pictures apart by over twice the most either moves by itself and 0.2 % more (of the screen, or of where
    #  it is read); or the setting changes how much the picture moves by 0.4 %)
    dead = {k: v for k, v in out.items() if not (v[0] > 2 * max(v[1], v[2]) + .002 or abs(v[1] - v[2]) > .004)}
    assert not dead, (dead, out)
    assert not g.errors, g.errors


def js(v):
    return "true" if v is True else "false" if v is False else repr(v).replace("'", '"')
