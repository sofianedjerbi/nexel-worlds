"""The home screen's island, frame after frame (title_scene.js, drawn by the HD look: hd.js):

- "vertical lines in the water": the water's picture (water.js: its waves and glints, waterCv) was made over the flat
  view's rectangle, and the tilted eye sees further north and south; past the picture's edge the GPU stretched its
  last row down the water (vox_style_glsl.js: the texture clamped): thin vertical lines, sliding as the view went.
  Every water tile the HD look shows is under the picture now (voxels.js still: over hd.js reach).
- "the whole world sometimes disappears": when the GPU took a context back (the sky's, VoxGL; the land's, vox_style.js)
  and gave no new one at once, the world's canvas was hidden, or drawn from the dead canvas: nothing but the page's
  dark, a second at a time. The last picture stays now, and the look comes back when a context is given."""

import pytest
from playwright.sync_api import TimeoutError as NotYet

from clock import stepped_wait

OPEN = "typeof TitleScene !== 'undefined' && TitleScene.on && document.body.classList.contains('scene') && HdLook.live && !HdLook.busy"
STILL = "(() => { TitleScene.stop(); document.getElementById('joinbox').style.display = ''; TitleScene.start(5); clearInterval(TitleScene.S.timer); })()"
# the water tiles on the screen whose place is not in the water's picture: [x, y]. Those of the land the HD look makes round its eye (hd.js
# box, the one the picture is laid over: voxels.js still); past it the far land is drawn without the picture. (It read a window of 23 rows
# round the camera: the box, round the eye's own tile, is the land the picture is for)
UNCOVERED = """() => { const out = [], v = waterView, c = waterCv, [x0, y0, x1, y1] = HdLook.box || [0, 0, -1, -1];
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const b = blockOf(x, y); if (!b || !Voxels.made(b) || !b.water.any || !Voxels.host.water(x, y)) continue;
    const s = HdLook.screenOf(x + .5, y + .5, topAt(x, y)); if (!s || s[0] < 0 || s[1] < 0 || s[0] >= innerWidth || s[1] >= innerHeight) continue;
    if (!v || x * 16 < v.x || y * 16 < v.y || (x + 1) * 16 > v.x + c.width || (y + 1) * 16 > v.y + c.height) out.push([x, y]); }
  return out; }"""


def open_title(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(server)
    page.wait_for_function(OPEN, timeout=30000)
    return page, errors


@pytest.mark.e2e
def test_the_water_picture_lies_on_all_the_water_the_island_shows(browser, server):
    page, errors = open_title(browser, server)
    page.evaluate(STILL)
    page.wait_for_function(OPEN, timeout=20000)
    off = {}
    for x, y in [(48.5, 26.5), (62, 42), (38, 36), (52.5, 21), (44, 34)]:      # (over the meadow, the river, the pond, the sea's edge: TITLE_MAP's view)
        page.evaluate(f"(() => {{ cam.x = camT.x = -8000 + {x}; cam.y = camT.y = -8000 + {y}; }})()")
        page.wait_for_function("!HdLook.busy", timeout=10000)
        ver = page.evaluate("Voxels.wver")
        page.wait_for_function(f"Voxels.wver > {ver} + 1", timeout=5000)          # (a picture made since the view moved)
        assert page.evaluate("Math.abs(cam.x - camT.x) < .01 && Math.abs(cam.y - camT.y) < .01")
        # (the land round the new place may come after those pictures: !busy above was read before any frame saw the move, and the
        #  picture is laid over the land the look made last, hd.js box. So: until a picture covers it all; one over the flat view's
        #  rectangle, as it was, never does. It was read 100 ms after: on a slow runner the north rows still the old place's, 81 tiles)
        assert page.evaluate("!!HdLook.box")                 # (the land the look makes, read: else nothing was looked at)
        try:
            page.wait_for_function(f"!({UNCOVERED})().length", timeout=8000)
        except NotYet:
            pass
        # (left uncovered across two pictures more: land made since the last picture is uncovered until the next, a tenth of a
        #  second, and on a loaded runner land round the new place is still being made seconds on: 11 tiles of a block just made,
        #  inside the picture's place a moment after. A picture's edge stretched, or laid on less than the box, stays uncovered)
        left = page.evaluate(UNCOVERED)
        if left:
            ver = page.evaluate("Voxels.wver")
            page.wait_for_function(f"Voxels.wver > {ver} + 1", timeout=5000)
            still = {tuple(t) for t in page.evaluate(UNCOVERED)}
            left = [t for t in left if tuple(t) in still]
        if left:
            off[(x, y)] = (len(left), left[:4], page.evaluate("[HdLook.box, Math.round(cam.x), Math.round(cam.y), waterView, waterCv && [waterCv.width, waterCv.height]]"))
    page.close()
    assert not off, off                                   # each of them was drawn with the picture's stretched edge: lines
    assert not errors, errors


@pytest.mark.e2e
def test_the_island_never_leaves_the_screen_even_when_the_gpu_takes_its_context_back(browser, server):
    page, errors = open_title(browser, server)
    # each frame: is the world's canvas on the screen, and is something drawn on it (not one colour: the backdrop alone is two)
    page.evaluate("""() => { window.__f = []; const g = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
      const f = () => { const el = HdView.el; let n = 0;
        if (el && el.style.display === 'block' && getComputedStyle(el).opacity !== '0') { g.canvas.width = el.width; g.canvas.height = el.height; g.drawImage(el, 0, 0);
          const d = g.getImageData(0, Math.floor(el.height / 2), el.width, Math.ceil(el.height / 2)).data, set = new Set(); for (let i = 0; i < d.length; i += 4 * 37) set.add(d[i] >> 4 << 8 | d[i + 1] >> 4 << 4 | d[i + 2] >> 4); n = set.size; }
        window.__f.push(n); requestAnimationFrame(f); }; requestAnimationFrame(f); }""")
    # (the frames AND the time: 4 s and 1.5 s had to hold 60 frames, 40 a second, on a runner's software GPU (#47); a fast
    # machine's 60 frames are a second of it: both, so neither watches less than it did)
    stepped_wait(page, 4000)                              # the island as it goes, the view moving after its people
    page.wait_for_function("window.__f.length >= 60", timeout=30000)
    # the GPU takes both contexts back and gives none for two seconds (a GPU reset on a busy machine: Chrome asks a page to wait)
    page.evaluate("""() => { window.__lose = [HdView.pic.getContext('webgl2'), VoxGL.gl].map((c) => c.getExtension('WEBGL_lose_context'));
      const g0 = HTMLCanvasElement.prototype.getContext; window.__none = true;
      HTMLCanvasElement.prototype.getContext = function (k, ...a) { return k === 'webgl2' && window.__none ? null : g0.call(this, k, ...a); };
      window.__lose.forEach((x) => x.loseContext()); setTimeout(() => { window.__none = false; }, 2000); }""")
    page.wait_for_function("!HdLook.live", timeout=5000)  # (it is lost indeed: no context given)
    page.wait_for_function("HdLook.live && HdLook.drew", timeout=10000)   # a context given again: the land drawn anew
    n = page.evaluate("window.__f.length")
    stepped_wait(page, 1500)
    page.wait_for_function(f"window.__f.length >= {n + 20}", timeout=20000)   # (and 1.5 s and twenty frames after it)
    frames = page.evaluate("window.__f")
    page.close()
    empty = [i for i, n in enumerate(frames) if n < 8]
    assert len(frames) > 60 and not empty, (len(frames), empty[:20])
    assert not errors, errors
