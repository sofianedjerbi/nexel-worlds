"""PROBE for #106, not for merge: frame by frame, the ground at your feet beside HdLook.raw() (the screen's px drawn
with a paint that is not there: the shader's mean colour): is the first land frame after a stamp a missing paint?"""

import pytest

from test_e2e_hd_sun import hd, settled

pytestmark = pytest.mark.e2e

# after each HdView.show: [why, the GL canvas's middle px (its own buffer), the screen's middle px, the middle px of the
# texture bound to unit 1 (the hour's light, vox_style.js ltx), gl's error, the lamp picture's version, the picture's size]
PROBE = """() => { window.__pr = []; const show = HdView.show; HdView.show = (o) => { const r = show(o); try {
  const c = o.pic, gl = c.getContext("webgl2"), px = new Uint8Array(4), x = c.width >> 1, y = c.height >> 1;
  gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); const glpx = [...px.slice(0, 3)].join();
  gl.activeTexture(gl.TEXTURE1); const t = gl.getParameter(gl.TEXTURE_BINDING_2D); gl.activeTexture(gl.TEXTURE0); let tpx = "none";
  if (t) { const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE; if (ok) { gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); tpx = [...px.slice(0, 3)].join(); } else tpx = "incomplete";
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.deleteFramebuffer(fb); }
  const k = devicePixelRatio, s = HdLook.read(Math.round(innerWidth * k / 2), Math.round(innerHeight * k / 2), 1, 1).data;
  const pp = myPos(); self.__probeAt = [Math.floor(pp.x), Math.floor(pp.y)]; const fa = HdLook.screenOf(pp.x + .5, pp.y + .92, topAt(pp.x, pp.y)), FX = Math.round(fa[0] * k), FY = Math.round(fa[1] * k), fs = HdLook.read(FX, FY, 1, 1).data;   // (your feet: the shadow test's px)
  let fl = "none"; if (t) { const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    const W2 = 320, H2 = 180;   // (the hour's light picture's size, as the probe recorded it: 320 x 180)
    if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE) { gl.readPixels(Math.round(FX / c.width * W2), Math.round((1 - FY / c.height) * H2), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); fl = [...px.slice(0, 3)].join(); }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.deleteFramebuffer(fb); }
  __pr.push([HdLook.why, glpx, [...s.slice(0, 3)].join(), tpx, gl.getError(), "roof " + (HdLevel.cover && HdLevel.cover.roof), "lit " + HdLook.youLit, "b " + HdLook.builds, "busy " + (HdLook.busy ? 1 : 0), "feet " + [...fs.slice(0, 3)].join(), "light@feet " + fl, "feet@ " + FX + "," + FY, "raw " + (typeof HdLook.raw === "function" ? HdLook.raw() : "?"), "mo " + JSON.stringify((self.__moLog || []).slice(-1)), "pin " + JSON.stringify(HdLook.pinned && HdLook.pinned.map((v) => (typeof v === "number" ? Math.round(v * 100) / 100 : v)))]); } catch (e) { __pr.push(["err", String(e)]); } return r; }; return 1; }"""


@pytest.mark.parametrize("run", range(4))
def test_probe_the_ground_under_you_and_missing_paints(browser, server, run):
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.js(PROBE)
        g.hour(.9)
        g.wait("Math.abs((clock.phase || 0) - .9) < .02")
        g.stamp(-3, -3, ["T.b", "...", "M.C"])
        for dx, dy in ((3, 2), (-2, -1), (0, 0)):
            g.rpc("dev_teleport", x=x + dx, y=y + dy, z=0)
            settled(g)
        g.js("__pr.push(['--- land made again from here'])")
        g.stamp(-12, -6, ["M" + "." * 11 + "M" + "." * 11 + "M"])
        g.sleep(2500)
        rec = g.js("__pr")
        print("light", g.js("JSON.stringify(Light.now())"))
        print("errors", g.errors)
        for r in rec:
            print(r)
        raise AssertionError("probe: see the frames printed above")
    finally:
        g.page.close()
