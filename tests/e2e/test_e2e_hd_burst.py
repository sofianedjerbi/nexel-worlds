"""The HD look under ground does not flash (hd.js, vox_style.js, vox_style_land.js): walking down a stair and off its
foot into a room two levels lower, your space is the same one all the way (the stair, the room, and the stair again
seen from the room: the floors you dropped FROM), so the window on it is the same one; only the light changes, a floor at a
time over a third of a second: the stair behind you cools. Every frame of that walk is looked at: the share of the
picture's px that jump, and the step of its mean light, stay near the walk's own scroll."""

import pytest
from test_e2e_hd_sun import hd, settled

# every frame of the land's own canvas (#hd, a px an art px): [mean light, share of px whose light moved by more than 28, the eye's pitch, your tile's x]
REC = """(() => { const c = document.createElement('canvas'), q = c.getContext('2d', {willReadFrequently: true}); let prev = null; window.__r = []; window.__on = true;
  const f = () => { const el = document.getElementById('hd'); if (el && el.width) { if (c.width !== el.width) { c.width = el.width; c.height = el.height; prev = null; } q.drawImage(el, 0, 0);
      const d = q.getImageData(0, 0, c.width, c.height).data, n = c.width * c.height, lum = new Uint8Array(n); let s = 0, big = 0;
      for (let i = 0; i < n; i++) { const l = (d[i * 4] * 3 + d[i * 4 + 1] * 6 + d[i * 4 + 2]) / 10; lum[i] = l; s += l; if (prev && Math.abs(l - prev[i]) > 28) big++; }
      __r.push([s / n, big / n, HdLook.cam.pitch, myPos().x]); prev = lum; }
    if (__on) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""
CUT = "([x0, x1, y0, y1]) => { const o = {}; for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const c = HdLook.winAt(x, y); if (c) o[x + ',' + y] = c.join(); } return o; }"   # (the window's tiles: floor, ceiling)


def stair(g):
    """From your tile west: a stair of eight treads, a level a tile, under a roof from the third on; at its foot a drop of
    two levels into a room 4 x 3. -> (x, y, z): the stair's top tile, the ground's level"""
    x, y = g.pos()
    z = g.js(f"topAt({x}, {y})")
    for i in range(1, 9):
        g.rpc("dev_col", tiles=[[x - i, y]], col=[z - i] if i < 3 else [z - i, z - i + 3, z])
    g.rpc("dev_col", tiles=[[x - 9 - i, y + j] for i in range(4) for j in (-1, 0, 1)], col=[z - 10, z - 6, z])
    g.sleep(800)
    return x, y, z


@pytest.mark.realtime
def test_walking_a_stair_and_dropping_into_the_room_at_its_foot_the_window_stays_and_no_frame_flashes(browser, server):
    g = hd(browser, server)
    g.rpc("dev_time", phase=.3)
    x, y, z = stair(g)
    g.rpc("dev_teleport", x=x - 4, y=y, z=z - 4)
    g.wait("HdLook.win.a === 1 && HdLook.win.n > 10 && !HdLook.busy && HdLook.cam.pitch > HdLook.steep - .1", timeout=8000)
    settled(g)
    box = [x - 16, x + 2, y - 6, y + 9]
    cut0 = g.js(CUT, box)
    assert g.js(f"HdLook.spaceAt({x - 6}, {y})") == [z - 6, 1]            # the stair: walked to
    assert g.js(f"HdLook.spaceAt({x - 10}, {y})") == [z - 10, 2]          # the room: dropped to; of your space already
    g.js(REC)
    g.page.keyboard.down("ArrowLeft")
    g.wait(f"myPos().x <= {x - 10}", timeout=8000)
    g.page.keyboard.up("ArrowLeft")
    g.wait("!HdLook.busy", timeout=6000)
    g.sleep(500)
    r = g.js("(() => { __on = false; return __r; })()")
    assert g.pos()[0] <= x - 10 and g.js("HdLook.level[0]") == z - 10
    # the window after the drop is the window before it (it was another space, another hole: a quarter of the picture in one frame)
    cut1 = g.js(CUT, box)
    changed = [k for k in set(cut0) | set(cut1) if cut0.get(k) != cut1.get(k)]
    assert len(cut0) >= 17 and len(changed) <= 2, (len(cut0), changed)        # (the five roofed treads, the room's twelve tiles: the third tread's roof is none thick, [z-3, z, z]: under the open sky, out of the window, which is only under a roof of land)
    # the stair is still of your space, as floors you cannot walk to; the room is walked
    assert g.js(f"HdLook.spaceAt({x - 6}, {y})") == [z - 6, 3]
    assert g.js(f"HdLook.spaceAt({x - 10}, {y})") == [z - 10, 1]
    # no frame of the walk flashes: the px that jump stay near the scroll's own share, the mean light moves in small steps
    steady = [(b, a) for a, b in zip(r, r[1:]) if a[2] > 57.9 and b[2] > 57.9]
    assert len(steady) > 40, len(steady)
    shares = sorted(b[1] for b, a in steady)
    scroll = shares[len(shares) * 9 // 10]
    worst = max(steady, key=lambda v: v[0][1])
    assert worst[0][1] <= max(.12, 2.2 * scroll), (worst[0], scroll)       # (the drop was .24 against a scroll of .07)
    light = max(abs(b[0] - a[0]) for b, a in steady)
    assert light < 2.2, light                                              # (it was 5.0 in one frame)
