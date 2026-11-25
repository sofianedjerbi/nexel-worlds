"""Whole px: the land's pixel is a whole number of the screen's px at any density, and what is written over a body (a bubble,
a name) goes with it px for px. ("When walking, chat bubbles become blurry", the owner.)

What was measured (a second player talking beside you, both walking then sprinting, each frame): at zoom 3 the bubble went
by its own 2 px, the body by the land's 3: the bubble 1 px off the speaker's head and back each step (offsets -169, -170,
-169...), at any density. At a density of 1.25 or 1.75 (a laptop's, a page zoomed in the browser) an art px was 3.75 or
5.25 px of the screen (art px 3 and 4 px wide in turn: the land shimmering as it went by), and the bubble was put at
fractions of a px: its letters drawn another way every other step (two rasters of it, 2052 and 2006 soft px)."""

import pytest
from conftest import open_game
from game import Game, new_name

pytestmark = pytest.mark.realtime                 # (every frame of a walk is looked at: on the tests' clock there are four times fewer)

DPRS = [1, 2, 1.25, 1.75]

# each frame: the bubble said by the other player (where, its size, its pixel, the land's pixel), the place of the speaker's body
# on the land's pixel, and how many of the bubble's px on the screen (the game's canvas, from the bubble's corner) are not as
# in the frame before: by more than 24 in a channel (the canvas, read each frame, is drawn by the CPU after a while: its
# letters' soft px then differ by 1)
REC = """(name) => { window.__pr = []; let ref = null, mine = null; const f0 = frame, o0 = outlined; window.__prOff = () => { frame = f0; outlined = o0; };
  outlined = (text, x, y, c) => { if (text === me) mine = [x, y]; return o0(text, x, y, c); };   // (your own name, where it is written)
  frame = function (now) { mine = null; f0(now); const p = [...ents.values()].find((q) => q.e && q.e.name === name), b = bubbles.find((b) => b.name === name && b.at); if (!p || !b) return;
    const s = HdLook.screenOf(p.x + .5, p.y + .5, HdLook.drawnAt(p) ?? 0); if (!s) return;
    const d = ctx.getImageData(Math.round(b.at[0] * DPR), Math.round(b.at[1] * DPR), Math.round(b.w * DPR), Math.round(b.h * DPR)).data; if (!ref || ref.length !== d.length) ref = d; let off = 0;
    for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - ref[i]) > 24 || Math.abs(d[i + 1] - ref[i + 1]) > 24 || Math.abs(d[i + 2] - ref[i + 2]) > 24 || Math.abs(d[i + 3] - ref[i + 3]) > 24) off++;
    const m = ents.get('agent' + myId), ms = m && HdLook.screenOf(m.x + .5, m.y + .5, HdLook.drawnAt(m) ?? 0);
    ref = d; __pr.push({at: b.at.slice(), w: b.w, n: d.length / 4, q: b.q, u: artPx(), body: [onArt(s[0]), onArt(s[1])], off, x: p.x, mine: mine && ms && mine[0] - onArt(ms[0])}); };
  return 1; }"""


def whole(v):
    return abs(v - round(v)) < 1e-6


@pytest.mark.parametrize("dpr", DPRS)
def test_a_bubble_goes_with_its_speaker_px_for_px_and_its_letters_stay_as_they_are(browser, server, dpr):
    page = browser.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=dpr)
    other = None
    try:
        g = Game(page, server)
        g.join(new_name(), 3)                         # (zoom 3: the land's pixel and the bubble's (2) are not one in the other)
        g.clear_area(6)
        g.stamp(-6, -4, ["." * 60] * 6)              # (a road east for both)
        other = open_game(browser, server)
        x, y = g.pos()
        other.rpc("dev_teleport", x=x + 2, y=y - 3)   # (its bubble not over your name)
        g.wait(f"[...ents.values()].some((p) => p.e && p.e.name === {other.name!r} && p.x === {x + 2})", 8000)
        g.rest()
        g.js(f"bubbles.push({{name: {other.name!r}, text: 'nice day for a walk, is it not', t: performance.now() / 1000 - 2}})")   # (written out already; 4 s before it fades)
        g.frames(3)
        g.js(REC, other.name)
        g.frames(10)
        still = g.js("__pr.splice(0)")
        assert still, still
        far = f"[...ents.values()].some((p) => p.e && p.e.name === {other.name!r} && p.x >= {x + 2} + %d)"
        for k, tiles in (("d", 5), ("Shift", 12)):    # (walk 5 tiles, then sprint 7 more, both of them: as far, not as long, on a slow machine)
            other.page.keyboard.down(k)
            g.page.keyboard.down(k)
            g.wait(far % tiles, 30000)
        for k in ("Shift", "d"):
            other.page.keyboard.up(k)
            g.page.keyboard.up(k)
        g.frames(3)
        walk = g.js("(() => { __prOff(); return __pr; })()")
        assert len(walk) > 12 and walk[-1]["x"] - walk[0]["x"] > 4, (len(walk), walk[0], walk[-1])     # (they walked: frames of it, and tiles)
        u, q = walk[0]["u"], walk[0]["q"]
        assert whole(u * dpr) and whole(q * dpr), (u, q)                                   # an art px and a bubble's px: whole px of the screen
        for f in walk:
            x0, y0 = f["at"]
            assert whole(x0 * dpr) and whole(y0 * dpr), f                                  # on whole px of the screen
            assert whole(x0 / u), f                                                        # ...and on the land's pixel
        tail = {round(f["at"][0] + round(f["w"] / 2 / u) * u - f["body"][0], 4) for f in walk}
        assert len(tail) == 1, tail                                                        # over the speaker's head: the same place every frame
        offs = [f["off"] for f in still + walk]
        assert max(offs) < walk[0]["n"] / 100, (max(offs), walk[0]["n"], offs)   # its px as the frame before's: not drawn another way (its letters
        # put a fraction of a px aside were most of their px. At a density of 1.25 or 1.75 on a runner a few px of the
        # outline, 4 or so in 20 000, come out another way from frame to frame)
        mine = {round(f["mine"], 4) for f in walk if f["mine"] is not None}
        assert len(mine) == 1, mine        # your own name over your head: the same place every frame (from your place to 1/16 tile, it was an art px off and back)
        assert not g.errors and not other.errors
    finally:
        if other:
            other.page.close()
        page.close()


# The land's own canvas made a checker of art px, the frames stopped, all else hidden: the widths of its px on the screen
STOP = "(() => { window.__stop = frame; frame = () => {}; for (const e of document.body.children) if (e !== HdView.el) e.style.visibility = 'hidden'; return 1; })()"   # (the frame already asked for is the last: it asks for none; nothing over the land's canvas)
GO = "(() => { frame = window.__stop; for (const e of document.body.children) e.style.visibility = ''; requestAnimationFrame(frame); return 1; })()"
CHECKER = """() => { const el = HdView.el, g = el.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0);
  for (let j = 0; j < el.height; j++) for (let i = 0; i < el.width; i++) { g.fillStyle = (i + j) % 2 ? '#000' : '#fff'; g.fillRect(i, j, 1, 1); }
  return [el.width, el.height, zoom, artPx(), devicePixelRatio]; }"""


def runs(g, png, row):
    """The widths of the black and white runs along a row of the screenshot (read by the page itself), its two ends left out
    (the screen's edges cut them)"""
    import base64
    return g.js("""async ([b64, row]) => { const im = await createImageBitmap(await (await fetch('data:image/png;base64,' + b64)).blob()), c = document.createElement('canvas');
      c.width = im.width; c.height = 1; const x = c.getContext('2d'); x.drawImage(im, 0, -row); const d = x.getImageData(0, 0, im.width, 1).data, out = []; let n = 1;
      for (let i = 1; i < im.width; i++) { if ((d[i * 4] > 127) === (d[i * 4 - 4] > 127)) n++; else { out.push(n); n = 1; } } return out.slice(1); }""", [base64.b64encode(png).decode(), row])


@pytest.mark.parametrize("dpr", DPRS)
def test_an_art_px_is_a_whole_number_of_the_screen_s_px_after_a_zoom_too(browser, server, dpr):
    """Each art px of the land as many px of the screen as the next, at zoom 3, and after a glide to 4: the shown scale ends on
    a whole step. (At 1.25 zoom 3 was 3.75 px: 3 and 4 px wide in turn, the land shimmering as it moved.)"""
    page = browser.new_page(viewport={"width": 1000, "height": 600}, device_scale_factor=dpr)
    try:
        g = Game(page, server)
        g.join(new_name(), 3)
        g.rest()
        for step in (None, "Equal"):
            if step:
                g.js(GO)
                g.page.keyboard.press(step)
                g.wait("zoom === 4 && !ZOOM.busy && !HdView.el.getAnimations().length && !cv.getAnimations().length", 4000)
                g.frames(3)
            g.js(STOP)
            g.frames(3)
            w, h, z, u, d = g.js(CHECKER)
            png = g.page.screenshot()
            k = round(z * d)
            assert abs(u * d - k) < 1e-6, (z, u, d)
            for row in (int(40 * d), int(150 * d)):
                r = runs(g, png, row)
                assert len(r) > 20 and set(r) == {k}, (z, d, k, sorted(set(r)), r[:12])   # every art px k px wide
        assert not g.errors
    finally:
        page.close()
