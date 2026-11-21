"""A phone's GPU draws the land as a desk's does: no lines at fixed rows of the screen (vox_style_glsl.js, highp).

The owner, on the demo: "there's some line artefacts everywhere": thin lit and dark lines across the grass and the farm's
field, along whole rows of tiles. A phone's GPU runs a fragment shader's `mediump` as half floats (11 bits, 65504 at
most); this Mac's runs it as full floats, so the lines never showed here. The page below plays a phone's mediump: every
input of a fragment shader that is mediump comes in rounded to a half float. The first screen's island, its clock held
and nobody on it, is read an art px a px with and without; a line is a row of one px that differs from the desk's
along a tenth of the width while the rows over and under it do not."""
import base64

import numpy as np

HALF = """(() => {
  const Q = `highp float q16(highp float x) { highp float a = abs(x); if (a > 65504.) return sign(x) * 1e30; if (a < 6.1e-5) return 0.; highp float s = exp2(floor(log2(a)) - 10.); return sign(x) * floor(a / s + .5) * s; }
highp vec2 q16(highp vec2 v) { return vec2(q16(v.x), q16(v.y)); } highp vec3 q16(highp vec3 v) { return vec3(q16(v.x), q16(v.y), q16(v.z)); } highp vec4 q16(highp vec4 v) { return vec4(q16(v.x), q16(v.y), q16(v.z), q16(v.w)); }
`;
  window.__half = 0;
  const src = WebGL2RenderingContext.prototype.shaderSource;
  WebGL2RenderingContext.prototype.shaderSource = function (sh, s) {
    if (/precision mediump float;/.test(s) && /out vec4 o;/.test(s) && /void main\\(\\) \\{/.test(s)) {
      const lets = [];
      s.replace(/\\bin (float|vec2|vec3|vec4) ([\\w, ]+);/g, (all, t, names) => { for (const n of names.split(",")) lets.push(`${t} ${n.trim()} = q16(${n.trim()});`); return all; });
      if (lets.length) { s = s.replace(/(out vec4 o;)/, "$1\\n" + Q).replace(/void main\\(\\) \\{/, "void main() { " + lets.join(" ")); window.__half++; }
    }
    return src.call(this, sh, s);
  };
})();"""
STILL = """() => { const S = TitleScene.S; clearInterval(S.timer);
  cam.x = camT.x = S.ox + S.C.centre[0]; cam.y = camT.y = S.oy + S.C.centre[1] + TITLE_DY;
  ents.clear(); bubbles.length = 0; emotes.clear(); clock.phase = .3;
  for (let i = 0; i < 400 && (i < 3 || HdLook.busy); i++) frame(1000);
  const cv = HdView.el, a = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
  let s = ''; for (let i = 0; i < a.length; i += 4) s += String.fromCharCode(a[i], a[i + 1], a[i + 2]);
  return {w: cv.width, h: cv.height, px: btoa(s), half: window.__half}; }"""
READY = "typeof TitleScene !== 'undefined' && TitleScene.on && document.body.classList.contains('scene') && HdLook.live && HdLook.builds > 0 && !HdLook.busy"


def island(browser, server, half):
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    if half:
        page.add_init_script(HALF)
    page.goto(server)
    page.wait_for_function(READY, timeout=60000)
    r = page.evaluate(STILL)
    page.close()
    return np.frombuffer(base64.b64decode(r["px"]), np.uint8).reshape(r["h"], r["w"], 3).astype(int), r["half"]


def lines(a, b):
    """Rows where a one-px band differs from the other picture along a tenth of the width (gaps of two px)."""
    d = np.abs(a - b).sum(2) > 18
    thin = d[1:-1] & ~d[:-2] & ~d[2:]
    out = []
    for y, row in enumerate(thin):
        run = best = gap = 0
        for v in row:
            if v:
                run, gap = run + 1, 0
            elif run and gap < 2:
                gap += 1
            else:
                run = gap = 0
            best = max(best, run)
        if best >= a.shape[1] * .1:
            out.append((y + 1, best))
    return out


def test_a_phones_half_floats_draw_no_lines_across_the_land(browser, server):
    desk, _ = island(browser, server, False)
    phone, half = island(browser, server, True)
    assert half is not None                                   # (the phone's mediump was in the page)
    assert desk.shape == phone.shape and len(np.unique(desk.reshape(-1, 3), axis=0)) > 40
    found = lines(desk, phone)
    assert found == [], f"lines across the land with a phone's half floats (row, px long): {found}"
