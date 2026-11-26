"""The wait (index.html #boot): the first thing on the screen and nothing else, the cat running in place over a pixel
bar, moving before any script has come; its bar never goes back; gone once the island is painted. The owner: "the loading
screen looks bad, can't you just show the loading and nothing else first so it doesn't look stuck?"; "improve its
loading speed": the sheets the title never shows (assets.js LATE) are not waited for."""

import socket
import subprocess
import sys
import time

import pytest

from conftest import ROOT, free_port

HOLD = """(() => { const add = DOMTokenList.prototype.add; window.__hold = true;
  DOMTokenList.prototype.add = function (...a) { if (window.__hold && a.includes('scene')) { window.__held = true; return; } return add.apply(this, a); };
  window.__p = 0; Object.defineProperty(window, 'ASSETS_OF', {get: () => 100, set: () => {}}); Object.defineProperty(window, 'ASSETS_IN', {get: () => window.__p * 100, set: () => {}}); })();"""
# the bar's fill in art px (what shows of it: it slides in from the left of its track), and the art px in screen px
BAR = "(() => { const b = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bootpx')), f = document.getElementById('bootfill'); return [(f.getBoundingClientRect().right - f.parentElement.getBoundingClientRect().left) / b, b * devicePixelRatio]; })()"
SLIDING = "document.getElementById('bootfill').getAnimations().length > 0"
FRAMES = "(n) => new Promise((ok) => { const f = () => (n-- > 0 ? requestAnimationFrame(f) : ok(1)); f(); })"
RUNNING = "document.getAnimations().filter((a) => a.playState === 'running' && a.effect.target.closest('#boot')).length"


def test_the_wait_runs_before_any_script_and_its_bar_never_goes_back(browser, server):
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    held = []
    page.route("**/js/*.js*", lambda r: held.append(r))           # (no script of the game's has come)
    page.goto(server, wait_until="commit")
    page.wait_for_function(f"!!document.getElementById('boot') && {RUNNING} >= 6", timeout=10000)      # the cat runs; the meadow, the hills, the clouds go by; the bar's glint, the line under it
    js = page.evaluate
    assert js("[!!document.getElementById('poster'), !!document.getElementById('loading')]") == [False, False]   # the still picture and the old strip: gone
    assert js("[[2, 2], [innerWidth - 3, innerHeight - 3], [innerWidth / 2, innerHeight / 2]].every(([x, y]) => document.elementFromPoint(x, y).closest('#boot'))")   # it alone is seen
    n, px = js(BAR)
    assert abs(n) < .01 and px == round(px) and px >= 6, (n, px)        # a whole number of screen px an art px, big enough on a phone
    page.close()
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    page.add_init_script(HOLD)
    page.goto(server)
    js = page.evaluate
    page.wait_for_function("typeof titleDraw === 'function'", timeout=20000)
    js("window.__p = .5")
    page.wait_for_function(f"{BAR}[0] >= 20 && !{SLIDING}", timeout=5000)   # (at rest: its slide in, 90 ms, done)
    n = js(BAR)[0]
    assert abs(n - round(n)) < .01, n                              # (whole art px)
    js("window.__p = .1")                                          # what is told goes back: the bar does not
    js(FRAMES, 10)                                                 # (ten of the page's frames to go back in, if it did)
    assert js(BAR)[0] >= n - .01
    js("window.__hold = false; document.body.classList.add('scene')")
    page.wait_for_function("!document.getElementById('boot')", timeout=5000)    # the island painted: the wait is gone
    page.close()


def test_the_title_does_not_wait_for_the_sheets_it_never_shows(browser, server):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    held = []
    page.route("**/assets/emoji.png*", lambda r: held.append(r))  # (the emotes' 119 KB: not come)
    page.goto(server, wait_until="commit")                        # (the page's load event waits for every picture asked for)
    page.wait_for_function("document.body && document.body.classList.contains('scene') && !document.getElementById('boot')", timeout=30000)   # (no body yet while the wait's stylesheet comes)
    assert held and page.evaluate("!IMG.emoji.naturalWidth")
    for r in held:
        r.continue_()
    page.wait_for_function("IMG.emoji.naturalWidth > 0", timeout=10000)   # and it comes, for the world
    page.close()


def test_the_wait_moves_with_no_script_at_all(browser, server):
    """CSS alone: no script of the page's runs (not even its own few lines), and the wait still moves, by the compositor's
    own steps (two pictures 0.3 s apart are not the same), in the page's ink, its frame there from the first picture."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True, java_script_enabled=False)
    page = ctx.new_page()
    try:
        page.goto(server, wait_until="domcontentloaded")
        page.wait_for_selector("#boot .win", state="visible", timeout=10000)
        box = page.locator("#boot .win").bounding_box()
        assert box and box["width"] > 100, box
        page.wait_for_timeout(400)                                  # (past its fade in)
        a = page.screenshot(clip=box)
        page.wait_for_timeout(300)
        b = page.screenshot(clip=box)
        assert a != b, "the wait stood still with no script"
        corner = page.screenshot(clip={"x": 2, "y": 2, "width": 4, "height": 4})
        assert corner == page.screenshot(clip={"x": 380, "y": 830, "width": 4, "height": 4})   # (the ink all round it)
    finally:
        ctx.close()


SKY = """async (b64) => { const im = new Image(); im.src = 'data:image/png;base64,' + b64; await im.decode();
  const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0); return [...x.getImageData(0, 0, 1, 1).data].slice(0, 3); }"""
AT = "(t) => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; } }"
hexrgb = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def test_the_wait_has_a_day_and_holds_still_at_dusk_when_asked_for_less_motion(browser, server):
    """The owner: "can you add a nice daylight cycle into loading screen?" The window's sky (its top band, an art px in from
    the corner: no star, sun, moon or cloud there) is the day's blue at 1 s, the night's (daylight.js) at 8 s, by CSS
    alone; asked for less motion, it is the dusk's and stays so, whatever time it is."""
    import base64
    for reduce, want in ((False, None), (True, "#8f6bb2")):
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True, reduced_motion="reduce" if reduce else "no-preference")
        try:
            page.route("**/js/*.js*", lambda r: None)                  # (no script of the game's comes: the wait stays)
            page.goto(server, wait_until="commit")
            page.wait_for_selector("#boot .win", state="visible", timeout=10000)
            page.wait_for_timeout(400)
            b = page.locator("#boot .win").bounding_box()
            px = page.evaluate("parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bootpx'))")
            clip = {"x": b["x"] + 2.5 * px, "y": b["y"] + 1.5 * px, "width": 1, "height": 1}
            def sky(t):
                page.evaluate(AT, t)
                page.wait_for_timeout(100)
                return page.evaluate(SKY, base64.b64encode(page.screenshot(clip=clip)).decode())
            near = lambda a, h: all(abs(u - v) <= 3 for u, v in zip(a, hexrgb(h)))
            day, night = sky(1000), sky(8000)
            if not reduce:
                assert near(day, "#549aed") and near(night, "#32356b"), (day, night)
                assert page.evaluate("document.getAnimations().filter((a) => a.effect.target.matches('#boot .sky.night')).length") == 1
            else:
                assert near(day, want) and near(night, want), (day, night)    # a still dusk
                assert page.evaluate("document.getAnimations().filter((a) => a.effect.target.closest('#boot .win') && !a.effect.target.closest('.cloud, .far, .near, .cat, .ground')).length") == 0
        finally:
            page.close()


# every frame the wait is on the screen: [ms, the % it says, the script's bytes read, the island's [warm, part %, busy] (hd.js)]; and the page's long tasks
WATCH = """window.__bar = [];
(() => { const f = (t) => { const s = document.getElementById('bootsay'); if (!s && __bar.length) return;
  if (s) __bar.push([Math.round(t), parseInt(s.textContent.replace(/\\D+/g, '')) || 0, window.ASSET_PACK ? ASSET_PACK.jsGot : -1, typeof HdLook === 'object' ? [HdLook.warm, Math.round(HdLook.part * 100), HdLook.busy] : null]); requestAnimationFrame(f); }; requestAnimationFrame(f); })();"""


@pytest.fixture(scope="module")
def bundled(tmp_path_factory):
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "nexel_worlds.server", "--saves", str(tmp_path_factory.mktemp("loading")), "--world", "l", "--port", str(port),
                             "--seed", "7", "--bundle"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=.2).close()
            break
        except OSError:
            time.sleep(.1)
    yield f"http://127.0.0.1:{port}/"
    proc.terminate()
    proc.wait(10)


@pytest.mark.realtime
def test_on_a_phone_the_bar_goes_on_by_small_steps(browser, bundled):
    """A phone on 4G (9 Mbit/s, 170 ms), its CPU four times slower, the page as a phone gets it (one script, one pack:
    web_bundle.py). The script's bytes are counted as they come (it was a tag: nothing of it counted till it had run, the bar
    leapt 22% to 58%); the bar never goes back and never leaps more than 15%. On GitHub's runners the pack was all in
    before the bar's first look and a third of the way was 1% to 20% at once: a step is 12% at most.
    (It also held every task under 120 ms till the island was shown. Gone, #47: there Chrome draws on the CPU (lavapipe),
    and the island's first picture made tasks of 121-132 ms however the CPU was slowed: it measured software drawing, not
    the game.)"""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    ctx.add_init_script(WATCH)
    page, errors = ctx.new_page(), []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 170, "downloadThroughput": 9e6 / 8, "uploadThroughput": 4.5e6 / 8})
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        page.goto(bundled, wait_until="commit")
        try:
            page.wait_for_function("document.body && document.body.classList.contains('scene') && !document.getElementById('boot')", timeout=60000, polling=100)
        except Exception:
            raise AssertionError("the island never came: " + str(page.evaluate("({bar: window.__bar && __bar.slice(-3), pack: window.ASSET_PACK && [ASSET_PACK.got, ASSET_PACK.need, ASSET_PACK.jsGot, ASSET_PACK.jsLen], "
                                 "decoded: [window.ASSETS_IN, window.ASSETS_OF], warm: typeof HdLook === 'object' ? [HdLook.warm, HdLook.busy, HdLook.part] : null})")) + f" {errors}") from None
        bar, js_len = page.evaluate("__bar"), page.evaluate("ASSET_PACK.jsLen")
        said = [b[1] for b in bar]
        steps = [b - a for a, b in zip(said, said[1:])]
        assert len(said) > 10 and min(steps) >= 0, said                                   # never back
        assert max(steps) <= 15, [(bar[i][0], said[i], said[i + 1], bar[max(0, i - 6):i + 2]) for i, s in enumerate(steps) if s > 15]
        assert any(0 < b[2] < js_len for b in bar), "the script's bytes were not counted as they came"
        assert not errors, errors
    finally:
        ctx.close()


def test_an_island_that_never_comes_does_not_hold_the_wait_for_ever(browser, server):
    """"still stuck at 76% in homescreen": the pictures in, the island never drawn (a GPU stuck after a hang): after
    8 s with nothing new, the wait goes and the page is shown as it is."""
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.add_init_script(HOLD)
    page.goto(server)
    page.wait_for_function("typeof titleDraw === 'function'", timeout=20000)
    page.evaluate("window.__p = 1; if (typeof HdLook === 'object') Object.defineProperty(HdLook, 'part', {get: () => .1, set: () => {}, configurable: true})")   # (the island stands still)
    page.evaluate(STILL)
    page.wait_for_function("window.__gone", timeout=30000)
    moved = page.evaluate("window.__moved")
    stall = max(b - a for a, b in zip(moved, moved[1:]))
    assert 7000 < stall < 10000, (stall, moved)                    # 8 s of the page's own with nothing new, then it goes (timed from the test's start on a slow machine, where the island's parts came in later: 12.7 s)
    assert not page.evaluate("document.body.classList.contains('scene')")   # (gone with no island: the give-up, not the island's end)
    page.close()


# the page's own times at which the bar moved, from now till the wait went: its longest pause is the stall the page gives up on
STILL = """(() => { const f = document.getElementById('bootfill'), w = () => { const r = f.parentElement.getBoundingClientRect(); return (f.getBoundingClientRect().right - r.left) / r.width; };
  let was = w(); window.__moved = [performance.now()];
  const go = () => { const now = w(); if (now !== was) __moved.push(performance.now()); was = now;
    if (!document.getElementById('boot')) { __moved.push(performance.now()); window.__gone = 1; return; } requestAnimationFrame(go); };
  requestAnimationFrame(go); return 1; })()"""


# every frame from the press of Enter: [the world's picture shown, the HD look live, you on the page], until your world is drawn
WOKE = """() => { window.__wk = []; const f = () => { const p = typeof myId !== 'undefined' && myId !== null && ents.get('agent' + myId);
  __wk.push([!!HdView.el && HdView.el.style.display === 'block', HdLook.live, !!p]); if (!(p && HdLook.live && HdLook.drew) && __wk.length < 600) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


def test_waking_up_the_island_stays_on_the_screen_until_your_land_is_drawn(browser, server):
    """"the world black after joining" (the phone; the desk now and then): Wake up pressed, the island went and the page's
    dark brown came with the bar, the hearts and the welcome, a fifth of a second or more: until the world sent you, the
    HD look had nobody to look at and hid its picture. Now the island's last picture stays until then: no frame between
    the first screen and your world without a picture of the world."""
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && HdLook.live && !document.getElementById('boot')", timeout=30000)
    page.fill("#name", f"wake{int(time.time() * 1000) % 100000}")
    page.evaluate(WOKE)
    page.keyboard.press("Enter")
    page.wait_for_function("(() => { const p = myId !== null && ents.get('agent' + myId); return !!p && HdLook.live && HdLook.drew; })()", timeout=20000)
    rec = page.evaluate("window.__wk")
    assert all(r[0] for r in rec), ([i for i, r in enumerate(rec) if not r[0]][:10], len(rec))
    page.close()
