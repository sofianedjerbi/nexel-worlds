"""PROBE (#85, removed before review): pictures of a far plateau's rim seen edge on, for the runner to upload."""

import os
from pathlib import Path

from test_e2e_hd_sun import hd


def test_probe_a_far_plateaus_rim(browser, server):
    g = hd(browser, server)
    out = Path(os.environ.get("E2E_SHOTS", "/tmp/shots")) / "rim"
    out.mkdir(parents=True, exist_ok=True)
    try:
        x, y = g.pos()
        g.stamp(-14, -34, ["." * 29] * 30)
        for h, (a, b) in ((3, (-22, -16)), (8, (-32, -26))):
            g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(a, b) for i in range(-12, 13)], col=[h])
        for v in (13, 25, 37):
            for hr in (.375, .15):
                g.js(f"(() => {{ setOpt('view', {v}); return 1; }})()")
                g.hour(hr, still=True)
                g.rest()
                g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
                g.page.screenshot(path=str(out / f"v{v}_h{hr}.png"))
                for z in (2, 5):
                    g.js(f"(() => {{ zoom = ZOOM.to = {z}; return 1; }})()")
                    g.rest()
                    g.page.screenshot(path=str(out / f"v{v}_h{hr}_z{z}.png"))
                g.js("(() => { zoom = ZOOM.to = 3; return 1; })()")
        assert False, "probe: pictures in the shots artifact"
    finally:
        g.page.close()
