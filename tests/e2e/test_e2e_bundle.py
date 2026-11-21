"""A server started with --bundle sends the client as few files (web_bundle.py): a phone gets in, walks, and the page
says nothing went wrong; loaded again, the script and the pictures are the browser's own copy."""

import subprocess
import sys
import time
import socket

import pytest

from conftest import ROOT, free_port


@pytest.fixture(scope="module")
def bundled(tmp_path_factory):
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", str(tmp_path_factory.mktemp("bundle")), "--world", "b", "--port", str(port),
                             "--seed", "7", "--dev", "--bundle"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
def test_a_phone_plays_on_the_one_script_and_keeps_it(browser, bundled):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
    page, errors, asked = ctx.new_page(), [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("request", lambda r: r.url.startswith("http") and asked.append(r.url.split("/")[-1].split("?")[0]))      # (not the pictures cut from the pack: blob:)
    try:
        page.goto(bundled, wait_until="commit")
        page.wait_for_function("typeof blocks !== 'undefined' && blocks.size > 0", timeout=30000)
        scripts = page.evaluate("[...document.scripts].map((s) => s.getAttribute('src')).filter(Boolean)")
        assert len(scripts) == 1 and scripts[0].startswith("js/game."), scripts
        assert page.evaluate("document.querySelectorAll('link[rel=stylesheet]').length") == 0
        assert not [n for n in asked if n.endswith(".png") and n not in ("panel.png", "slot.png", "slot_sel.png", "cursor.png", "cursor_point.png")], asked   # (the sheets came in the pack)
        assert sum(n.startswith("pack.") for n in asked) == 1 and len(asked) < 25, asked
        assert page.evaluate("Object.keys(IMG).length > 60 && IMG.grass.naturalWidth === 176 && Object.keys(GEN).length > 5")
        page.fill("#name", "packed")
        page.touchscreen.tap(*page.evaluate("(() => { const r = document.getElementById('join').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()"))
        page.wait_for_function("meObs !== null && !!myPos() && HdLook.on && HdLook.faces > 500 && HdLook.catSeen() > .8", timeout=30000)
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
        page.reload()                                               # again: the script and the pack are not fetched (kept for good under their own names)
        page.wait_for_function("typeof blocks !== 'undefined' && blocks.size > 0", timeout=30000)
        kept = page.evaluate("performance.getEntriesByType('resource').filter((e) => /game\\.|pack\\./.test(e.name)).map((e) => [e.name.split('/').pop(), e.transferSize])")
        assert len(kept) == 2 and all(size == 0 for _, size in kept), kept
        assert not errors, errors
    finally:
        ctx.close()
