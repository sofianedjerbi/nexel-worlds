"""A plateau's top seen far off, squeezed to a few px a tile, is drawn in whole rows of its paint (vox_style_glsl.js,
a top's pick: #4's rule 3): no speckle along its rim. Each px was the nearest row of the paint, a different one each
px: its lip's dark flecks dotted the rim; and a lip's rows kept whole were a steady dark band along it (#85)."""

from test_e2e_hd_sun import hd

# a canvas row of the HD picture from x0 to x1 (canvas px): [r, g, b] each px
ROW = """([x0, x1, y]) => { const d = HdLook.read(x0, y, x1 - x0, 1).data, out = []; for (let i = 0; i < d.length; i += 4) out.push([d[i], d[i + 1], d[i + 2]]); return out; }"""


def tone(px):
    """The row's own tone (the median of each colour), and the share of its px a step off it (sum of |rgb| over 24)."""
    mid = [sorted(p[i] for p in px)[len(px) // 2] for i in range(3)]
    off = sum(1 for p in px if sum(abs(p[i] - mid[i]) for i in range(3)) > 24)
    return mid, off / len(px)


def test_a_far_plateaus_top_has_no_speckle_and_no_dark_band_along_its_rim(browser, server):
    g = hd(browser, server)
    try:
        x, y = g.pos()
        g.stamp(-14, -24, ["." * 29] * 20)                                         # (the meadow up to it: nothing of the world's in front)
        g.rpc("dev_col", tiles=[[x + i, y + j] for j in range(-14, -10) for i in range(-12, 13)], col=[3])   # a plateau 3 high, 11 to 14 tiles north
        g.js("(() => { setOpt('view', 37); zoom = ZOOM.to = 2; return 1; })()")
        g.hour(.375, still=True)                                                   # (noon: no long shadows on it)
        g.rest()
        g.wait("!HdLook.busy && HdLook.bare() === 0", 15000)
        k = g.js("cv.width / innerWidth")
        (ax, edge), (bx, _) = g.js(f"[HdLook.screenOf({x - 9}, {y - 10}, 3), HdLook.screenOf({x + 9}, {y - 10}, 3)]")   # (its south rim: the top's south edge)
        far = g.js(f"HdLook.screenOf({x}, {y - 14}, 3)")[1]                     # (its north edge)
        assert (edge - far) * k > 12, (edge, far)                                  # (seen squeezed: its 4 tiles' 64 rows of paint in a few px)
        x0, x1 = round(ax * k), round(bx * k)
        body, _ = tone(g.js(ROW, [x0, x1, round((edge + far) / 2 * k)]))
        y0 = round(edge * k)
        top = next((y for y in range(y0, y0 - 24, -1) if (lambda m: m[1] > m[0] + 20)(tone(g.js(ROW, [x0, x1, y]))[0])), None)   # (the top's first row over its earth side: green)
        assert top is not None, (y0, [tone(g.js(ROW, [x0, x1, y])) for y in range(y0, y0 - 24, -4)])
        rows = []
        for y in (top, top - 1, top - 2):                                          # (the canvas rows of its rim)
            mid, off = tone(g.js(ROW, [x0, x1, y]))
            rows.append((y0 - y, mid, round(off, 3)))
        assert all(sum(abs(m - b) for m, b in zip(mid, body)) <= 30 and off <= .08 for _, mid, off in rows), (body, rows)
        assert not g.errors, g.errors
    finally:
        g.js("(() => { setOpt('view', OPT_DEFAULT.view); zoom = ZOOM.to = 3; return 1; })()")
        g.page.close()
