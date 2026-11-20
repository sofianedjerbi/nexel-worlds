"""The GitHub Pages demo: the static build runs the whole game in the tab (Pyodide) and keeps the world on reload."""

import functools
import http.server
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "tools"))
from build_pages import build  # noqa: E402


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("pages") / "dist"
    # (one build at a time: the first one makes the sounds where there are none (a new worktree), and two workers
    # making them at once read each other's half-written files: "No such file ... eat_1.flac")
    import fcntl
    with open(tmp_path_factory.getbasetemp().parent / "pages.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        build(out)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    handler.log_message = lambda *a: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()


def test_the_demo_plays_and_remembers_the_world(browser, site):
    ctx = browser.new_context(viewport={"width": 1100, "height": 750})
    page, errors = ctx.new_page(), []
    page.on("pageerror", lambda e: errors.append(str(e)))
    asked = []
    page.on("request", lambda r: asked.append(r.url.split("/")[-1].split("?")[0]))
    page.goto(site, wait_until="commit")
    # the world starts to come with the page, before its scripts have (its start and the styles are in the page itself)
    page.wait_for_function("typeof bootLocal === 'function' && document.body.classList.contains('booting')", timeout=5000)
    assert page.evaluate("[document.querySelectorAll('link[rel=stylesheet]').length, !!document.querySelector('script[src*=\"local.js\"]')]") == [0, False]
    page.wait_for_function("!!document.querySelector('#poster.in') && document.getElementById('poster').currentSrc.includes('?v=')", timeout=10000)   # the island's still picture: there, with the build's mark
    page.wait_for_function("blocks.size > 0", timeout=90000)       # Pyodide comes from the CDN on first load
    page.wait_for_function("!document.body.classList.contains('booting')", timeout=90000)
    assert "sfx.json" not in asked[:asked.index("py.zip")], "the sounds were asked for before the world had come"
    # every script the page names has the build's mark: a page loaded again after a publish is the new build at once
    marks = page.evaluate("[...document.scripts].filter((s) => s.getAttribute('src') && s.getAttribute('src').startsWith('js/')).map((s) => s.getAttribute('src').split('?v=')[1])")
    assert len(marks) > 50 and all(marks) and len(set(marks)) == 1, marks[:5]
    page.fill("#name", "visitor")
    page.click("#join")
    page.wait_for_function("meObs !== null", timeout=20000)
    tick = page.evaluate("rpc('ping').then(r => r.tick)")
    page.wait_for_timeout(1000)
    assert page.evaluate("rpc('ping').then(r => r.tick)") >= tick + 8      # the world ticks at 10 Hz in the tab
    page.evaluate("saveWorld()")                                    # what the 15 s autosave does
    page.reload()
    page.wait_for_function("blocks.size > 0", timeout=90000)
    page.wait_for_function("agents.some((a) => a.name === 'visitor')", timeout=5000)   # saved, asleep
    ctx.close()
    assert not errors, errors
    phone = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)       # a phone: its picture of the island is in the page itself
    page = phone.new_page()
    page.route("**/js/*.js*", lambda r: r.abort())             # (no script has come yet)
    page.goto(site, wait_until="domcontentloaded")
    page.wait_for_function("!!document.querySelector('#poster.in') && document.getElementById('poster').currentSrc.startsWith('data:image/webp') && document.getElementById('poster').naturalWidth === 480", timeout=5000)
    assert page.evaluate("document.fonts.check('18px SproutPixel') && !performance.getEntriesByType('resource').some((e) => /sprout-pixel/.test(e.name))")   # (and its letters)
    phone.close()


def test_a_phone_plays_the_demo_in_the_hd_look(browser, site):
    """The demo is what a phone plays, and the HD look had never been run in it: in, the land drawn round you, the
    thumb's stick walks, and the page says nothing went wrong."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
    page, errors = ctx.new_page(), []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    try:
        page.goto(site, wait_until="commit")
        page.wait_for_function("typeof blocks !== 'undefined' && blocks.size > 0 && !document.body.classList.contains('booting')", timeout=90000)
        page.fill("#name", "thumbs")
        page.touchscreen.tap(*page.evaluate("(() => { const r = document.getElementById('join').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()"))
        page.wait_for_function("meObs !== null && !!myPos() && HdLook.on && HdLook.faces > 500 && HdLook.catSeen() > .8", timeout=30000)
        assert page.evaluate("zoom === 2 && !!document.getElementById('tMenu') && getComputedStyle(document.getElementById('prompts')).display === 'none'")
        cdp = ctx.new_cdp_session(page)
        touch = lambda kind, x=0, y=0: cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y}]})
        for way in (1, -1):                                         # east, then back west: one of the two is open ground
            touch("touchStart", 90, 600)
            for i in range(1, 6):
                touch("touchMove", 90 + way * i * 8, 600)
                page.wait_for_timeout(30)
            page.wait_for_timeout(1200)
            touch("touchEnd")
        page.wait_for_function("HdLook.builds > 1 && HdLook.catSeen() > .8", timeout=8000)      # (the land was made again as you went, and you are still drawn on it)
        assert not errors, errors
    finally:
        ctx.close()
