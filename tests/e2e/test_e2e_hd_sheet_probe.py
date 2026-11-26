"""PROBE (#111, removed before review): the phone's tiny sheet, the land before and after it is made again from none, for the runner to upload."""

import base64
import os
from pathlib import Path

import pytest
from test_e2e_hd_sheet import DIFF, LINE, PHONE, WHERE

from conftest import Game, new_name

# a picture of the HD look's px (data: window.__was, or the picture now), and one of where they differ (red), as PNG data URLs
PNG = """(which) => { const W = cv.width, H = cv.height, now = HdLook.read(0, 0, W, H).data, was = window.__was, c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d'), im = x.createImageData(W, H), d = im.data;
  for (let i = 0; i < d.length; i += 4) { const diff = Math.abs(was[i] - now[i]) + Math.abs(was[i + 1] - now[i + 1]) + Math.abs(was[i + 2] - now[i + 2]) > 24;
    const s = which === 'was' ? was : now; if (which === 'diff') { d[i] = diff ? 255 : s[i] / 3; d[i + 1] = diff ? 0 : s[i + 1] / 3; d[i + 2] = diff ? 0 : s[i + 2] / 3; } else { d[i] = s[i]; d[i + 1] = s[i + 1]; d[i + 2] = s[i + 2]; } d[i + 3] = 255; }
  x.putImageData(im, 0, 0); return c.toDataURL('image/png'); }"""


@pytest.mark.realtime
def test_probe_phone_tiny_sheet(browser, server):
    out = Path(os.environ.get("E2E_SHOTS", "/tmp/shots")) / "sheet"
    out.mkdir(parents=True, exist_ok=True)
    page = browser.new_page(**PHONE)
    page.add_init_script("window.SHEET_AW = 1024")
    g = Game(page, server)
    g.join(new_name(), 3)
    g.js("setOpt('names', false); setOpt('hints', false); setOpt('clouds', 0); setOpt('rays', 0); setOpt('shimmer', 0)")
    g.rpc("dev_creatures", clear=60)
    g.hour(.3, still=True)
    g.rest()
    for key in ("d", "w", "a", "s"):
        g.hold(["Shift", key], 2500)
        g.rest()
    g.rpc("dev_creatures", clear=60)
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    g.js("(() => { HdLook.landOnly = true; return 1; })()")
    g.frames(3)
    g.js(f"(() => {{ window.__was = HdLook.read(0, 0, cv.width, cv.height).data; window.__line = {LINE}; return 1; }})()")
    box0 = g.js("[HdLook.box, HdLook.work, myPos(), HdLook.why]")
    g.js("HdLook.forget()")
    g.rest()
    g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
    g.frames(3)
    d = g.js(DIFF)
    for which in ("was", "now", "diff"):
        (out / f"{which}.png").write_bytes(base64.b64decode(g.js(PNG, which).split(",", 1)[1]))
    info = (d, g.js(WHERE), box0, g.js("[HdLook.box, HdLook.work, myPos(), HdLook.why]"))
    (out / "info.txt").write_text(repr(info))
    page.close()
    raise AssertionError(("probe", info))
