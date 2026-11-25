"""Water in Chrome: it has depth and is drawn as a see-through layer; you swim on any of it, with a wake behind."""

import pytest
import os
from conftest import needs_sounds

SHOT = os.environ.get("WILD_SHOTS")


def mine(game, js):
    return game.js(f"(() => {{ const p = ents.get('agent' + myId); return {js}; }})()")


STATE = """(() => { const p = ents.get('agent' + myId); return {x: p.x, tx: p.tx, swims: swimsAt(p, p.e), mode: BodyPlace.of(p).mode,
  wake: p.wake ? p.wake.length : null, walking: !!walking, race: p.e.race}; })()"""


def until(game, done, timeout=8000):
    """until the page has `done` (of p, you); not met: where you are, in the error"""
    try:
        game.wait(f"(() => {{ const p = ents.get('agent' + myId); return {done}; }})()", timeout)
    except Exception as e:
        raise AssertionError((done, game.js(STATE))) from e


def swim_until(game, key, done, timeout=8000):
    """`key` held until the page has `done` (of p, you): a way in the water is so many tiles, not so many ms."""
    game.page.keyboard.down(key)
    try:
        until(game, done, timeout)
    finally:
        game.page.keyboard.up(key)


TRACK = """(() => { window.__sw = []; window.__swOn = true; const f = (now) => { const p = ents.get('agent' + myId); __sw.push([now, p.x, walking && p.walking ? 1 : 0]);
  if (__swOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()"""


def pace(game):
    """tiles a second you went, as drawn, by the frames' own time since TRACK, while the key had you walking (not the
    glide into place and the stop after it), its first 300 ms left out (setting off)"""
    rec = game.js("(() => { __swOn = false; return __sw; })()")
    rec = [r for r in rec if r[2] and r[0] >= rec[0][0] + 300]
    return (rec[-1][1] - rec[0][1]) / (rec[-1][0] - rec[0][0]) * 1000 if len(rec) > 2 and rec[-1][0] > rec[0][0] else None


def gaps(ts):
    """the middle one of the ms between marks laid one after another"""
    d = sorted(b - a for a, b in zip(ts, ts[1:]))
    return d[len(d) // 2] if d else None


def test_you_swim_across_water_of_every_depth_and_leave_a_wake(game):
    game.clear_area(8)
    s = game.server()
    rows = ["~~((==))", "~~((==))", "~~((==))", "~~((==))", "~~(==)))", "~~((==))", "~~~((==)"]
    game.rpc("dev_stamp", x=s["x"] + 2, y=s["y"] - 3, rows=rows)
    game.rpc("dev_give", items={"straw_hat": 1})
    game.rpc("dev_race", race="bunny")
    game.act("wear", item="straw_hat"); game.sleep(900)
    assert not mine(game, "swimsAt(p, p.e)")
    layer = game.js("(() => { const b = [...blocks.values()].find((b) => b.water && b.water.any && b.water.foam.length > 0); return b ? [b.water.canvas.width, true] : null; })()")   # (the block the pond is in, not any block with water)
    assert layer == [512, True]                                # the water layer is built, with foam along the shore
    assert game.js("[depthAt(%d, %d), depthAt(%d, %d), depthAt(%d, %d)]" % (s["x"] + 2, s["y"], s["x"] + 5, s["y"], s["x"] + 9, s["y"])) == [1, 2, 4]
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/water.png")
    game.page.keyboard.down("d")                               # into the shallows, a wake behind us (laid as the swimmer is drawn)
    try:
        until(game, f"swimsAt(p, p.e) && p.tx >= {s['x'] + 3} && !!p.wake && p.wake.length >= 2")
        assert game.server()["swimming"]
        until(game, f"p.tx >= {s['x'] + 6}")                   # and on over the deep (a tile on: the world has you past +5)
    finally:
        game.page.keyboard.up("d")
    assert game.server()["swimming"] and game.server()["x"] >= s["x"] + 5
    if SHOT:
        game.page.screenshot(path=f"{SHOT}/water_swim.png")
    swim_until(game, "a", f"p.tx <= {s['x'] + 1} && !swimsAt(p, p.e)")   # and back out
    game.wait("!walking && !pred", 4000)
    assert not game.server()["swimming"] and not mine(game, "swimsAt(p, p.e)")
    assert not game.errors


def test_a_page_older_than_the_servers_code_reloads_itself(game):
    stamp = game.js("webStamp")
    assert stamp > 0                                           # the server said when its client code last changed
    game.js("spec.onmessage({data: JSON.stringify({type: 'hello', web: webStamp})})")
    game.sleep(300)
    assert game.js("myId") is not None                         # the same code: nothing happens
    with game.page.expect_navigation():                        # newer code after a reconnect: the page loads it
        game.js("spec.onmessage({data: JSON.stringify({type: 'hello', web: webStamp + 1})})")


@needs_sounds
def test_swimming_sounds_like_swimming_not_like_walking(game):
    game.clear_area(8)
    s = game.server()
    game.rpc("dev_stamp", x=s["x"] + 1, y=s["y"] - 2, rows=["~~((==))"] * 5)
    game.sleep(600)
    game.wait("sounds.manifest && Object.values(sounds.manifest.sounds).flatMap((s) => s.files).every((f) => sounds.buffers.get(f) instanceof AudioBuffer)", 20000)
    game.hold(["d"], 400)                                      # in: one splash
    game.js("sounds.lastAt = {}")
    game.hold(["d"], 800)                                      # swimming on
    heard = set(game.js("Object.keys(sounds.lastAt)"))
    assert "swim" in heard and not heard & {"step", "wade", "water"}, sorted(heard)
    game.sleep(600)                                            # (the stroke that carries you onto the tile you were entering)
    game.js("sounds.lastAt = {}")
    game.sleep(1200)                                           # treading water: nothing
    assert not set(game.js("Object.keys(sounds.lastAt)")) & {"swim", "step", "wade", "water"}
    assert not game.errors


@pytest.mark.realtime
def test_a_sprint_in_the_water_is_twice_as_fast_and_leaves_a_longer_wake(game):
    """Shift in the water did nothing (nobody sprinted there). Now it is a sprint: twice a swim, and the water halves
    both (2.5 tiles a second swimming, 5 at a sprint: "speed in water should be decreased, half of ground speed"), with
    its own look: strokes twice as often, and a wake of marks twice as close that last longer."""
    game.clear_area(8)
    s = game.server()
    game.rpc("dev_needs", hp=20, hunger=20)
    game.rpc("dev_stamp", x=s["x"] + 1, y=s["y"] - 4, rows=["(" * 40] * 9)
    game.sleep(600)
    game.hold(["d"], 600)                                      # in, and swimming
    assert mine(game, "swimsAt(p, p.e)") and game.js("SWIM_SPRINT") is True
    game.js(TRACK)
    game.hold(["d"], 1000)
    swum, slow = pace(game), gaps(mine(game, "p.wake.filter((w) => !w.dash).map((w) => w.t)"))
    game.page.keyboard.down("Shift")
    game.js(TRACK)
    game.js("(() => { window.__fr = []; window.__frOn = true; const f = (now) => { __fr.push(now); if (__frOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()")
    game.page.keyboard.down("d")
    game.sleep(1000)
    ran = mine(game, "p.running")                              # (asked while still at it: asked after the keys were let go, it was sometimes over)
    game.page.keyboard.up("d")
    dashed, marks = pace(game), gaps(mine(game, "p.wake.filter((w) => w.dash).map((w) => w.t)"))
    game.page.keyboard.up("Shift")
    frame = gaps(game.js("(() => { __frOn = false; return __fr; })()"))
    assert swum and dashed and 2 <= swum <= 3 and 4 <= dashed <= 6 and game.js("SWIM_PACE") == 2, (swum, dashed)   # 2.5 tiles a second, then five
    assert ran is True and slow and marks and slow >= 110 and 45 <= marks <= 45 + 1.5 * frame and marks < slow, (slow, marks, frame)   # (its wake: a mark every 45 ms, not every 110: the first frame past it, a mark a frame at most. Counted in a second it was the machine's frames a second)
    assert game.server()["swimming"] and not game.errors


# The wake's picture as the HD look lays it on the water (swim.js wakePicture), read along the way they came: px of foam
# in each band of 8 art px across, from where they are back to its end; and how far the marks reach (art px)
WAKE = """(() => { const p = ents.get('agent' + myId), w = wakePicture(p, performance.now()); if (!w) return null;
  const c = w.canvas, d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data, bands = [];
  for (let x0 = w.fx; x0 - 8 >= 0; x0 -= 8) { let n = 0; for (let x = x0 - 8; x < x0; x++) for (let y = 0; y < c.height; y++) if (d[(y * c.width + x) * 4 + 3] > 0) n++; bands.push(n); }
  const alpha = new Set(); for (let i = 3; i < d.length; i += 4) alpha.add(d[i]);
  return {bands, reach: Math.max(...p.wake.map((m) => (p.x - m.x) * 16)), room: w.fx, alpha: [...alpha]}; })()"""


@pytest.mark.realtime
def test_a_sprints_wake_thins_out_to_nothing_at_its_end_and_is_not_cut(game):
    """"When sprinting in water: particles are abruptly cut at the end". The HD look drew the wake in the swimmer's own
    picture, four tiles wide: cut in a straight line a tile and a half behind them; and with no blending there, a
    fleck's fading alpha was whole, then gone. Now it is a picture of its own on the water, as long as the wake, and a
    mark thins out in whole px (a 2x2 pattern) and shortens over the last part of its life."""
    game.clear_area(8)
    s = game.server()
    game.rpc("dev_needs", hp=20, hunger=20)
    game.rpc("dev_stamp", x=s["x"] + 1, y=s["y"] - 4, rows=["(" * 40] * 9)
    game.sleep(600)
    game.hold(["d"], 600)
    game.page.keyboard.down("Shift")
    game.page.keyboard.down("d")
    game.sleep(2200)                                           # (longer than a mark lives: the wake is whole, its end thinning)
    w = game.js(WAKE)
    game.page.keyboard.up("d")
    game.page.keyboard.up("Shift")
    assert w and w["reach"] > 6 * 16 and w["room"] >= w["reach"] + 16, w            # its picture holds all of it: nothing cut
    assert set(w["alpha"]) <= {0, 255}, w["alpha"]                                 # whole px, no smooth alpha
    b = [n for n in w["bands"]]
    last = max(i for i, n in enumerate(b) if n)                                     # (its end, counted from them)
    peak = max(b[: max(1, last // 2)])
    tail = b[last - 3: last + 1]
    assert peak > 0 and max(tail) <= .5 * peak and tail[-1] <= .25 * peak, (b, last)   # thinner and thinner to its end: no edge
    assert not game.errors


@pytest.mark.realtime
def test_letting_go_of_the_key_in_the_water_you_swim_on_into_place_not_walk(game):
    """Let go of the key while swimming, you go on to where the world has you at the swim's pace (2.5 tiles a second),
    as under the key: the glide into place went at the pace on land, twice as fast ("the swimming animation goes faster
    when player releases the key, turning into normal walking"). One pace for a person, walking or gliding: walk.js speedAt."""
    game.clear_area(8)
    s = game.server()
    game.rpc("dev_needs", hp=20, hunger=20)
    game.rpc("dev_stamp", x=s["x"] + 1, y=s["y"] - 4, rows=["(" * 40] * 9)
    game.sleep(600)
    game.hold(["d"], 1500)                                     # in, and swimming
    glide = []
    for ms in (700, 550, 820, 640):                            # (let go wherever the walk is: a walk that ends on the world's own tile has no glide)
        game.js("""(() => { window.__sw = []; const f = (now) => { const p = ents.get('agent' + myId); __sw.push([now, p.x, walking && p.walking ? 1 : 0]);
          if (__sw.length < 150) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; })()""")
        game.hold(["d"], ms)
        game.sleep(1300)
        rec = game.js("__sw")
        glide += [(b[1] - a[1]) / min(.1, (b[0] - a[0]) / 1000) for a, b in zip(rec, rec[1:]) if not a[2] and not b[2] and b[0] > a[0] and b[1] != a[1]]
        if len(glide) >= 5:
            break
    assert glide and max(glide) < 2.5 * 1.35, [round(v, 2) for v in glide]                    # (it was 5 to 6.5: the pace on land)
    assert mine(game, "swimsAt(p, p.e)") and game.server()["swimming"] and not game.errors
