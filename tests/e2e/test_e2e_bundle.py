"""A server started with --bundle sends the client as few files (web_bundle.py): a phone gets in, walks, and the page
says nothing went wrong; loaded again, the script and the pictures are the browser's own copy."""

import subprocess
import sys
import time
import socket

import pytest

from conftest import ROOT, free_port
from game import new_name


@pytest.fixture(scope="module")
def bundled(tmp_path_factory):
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "nexel_worlds.server", "--saves", str(tmp_path_factory.mktemp("bundle")), "--world", "b", "--port", str(port),
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


def test_a_phone_plays_on_the_one_script_and_keeps_it(browser, bundled):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
    page, errors, asked = ctx.new_page(), [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("response", lambda r: r.status >= 400 and errors.append(f"{r.status} {r.url}"))      # (which file: the console says only "404")
    page.on("request", lambda r: r.url.startswith("http") and asked.append(r.url.split("/")[-1].split("?")[0]))      # (not the pictures cut from the pack: blob:)
    try:
        page.goto(bundled, wait_until="commit")
        try:
            page.wait_for_function("typeof blocks !== 'undefined' && blocks.size > 0", timeout=30000)
        except Exception:
            raise AssertionError(f"the land did not come: {errors} asked {asked} scripts {page.evaluate('[...document.scripts].map((s) => s.getAttribute(`src`)).filter(Boolean).slice(0, 3)')}") from None
        # (the one script: read by the page, its bytes counted for the wait's bar, run as parts from what was read: asked for once, no tag of its own)
        scripts = page.evaluate("[...document.scripts].map((s) => s.getAttribute('src')).filter(Boolean)")
        assert len(scripts) == 4 and all(s.startswith("blob:") for s in scripts) and sum(n.startswith("game.") for n in asked) == 1, (scripts, asked)
        assert page.evaluate("document.querySelectorAll('link[rel=stylesheet]').length") == 0
        assert not set(asked) & set(page.evaluate("Object.keys(ASSET_PACK.files)")), asked   # (the sheets came in the pack: the page's own pictures, its icon and frames, are files of their own)
        assert sum(n.startswith("pack.") for n in asked) == 1 and len(asked) < 25, asked
        assert page.evaluate("Object.keys(IMG).length > 60 && IMG.grass.naturalWidth === 176 && Object.keys(GEN).length > 5")
        # (Join is tapped once the wait is gone (index.html #boot: over everything till the island is painted): tapped as the
        #  land came, the tap fell on the wait's own picture, and nobody joined; the page said: join shown, no socket, under the tap an element that is not the button)
        page.wait_for_function("document.body.classList.contains('scene') && !document.getElementById('boot')", timeout=30000)
        page.fill("#name", new_name("packed"))                      # (a name of this try's own: at its second try "packed" was "already someone else", and it waited 30 s for a player who never got in)
        page.touchscreen.tap(*page.evaluate("(() => { const r = document.getElementById('join').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()"))
        # (a new player wakes somewhere else every run: behind a tree, in a pond: seven tenths of the cat seen, for good: it waited 30 s for the rest and passed at its second try, elsewhere. A meadow first, as every other test has)
        try:
            page.wait_for_function("meObs !== null && !!myPos()", timeout=30000)
        except Exception:
            raise AssertionError("tapped Join, not in: " + str(page.evaluate("({obs: meObs !== null, join: document.getElementById('joinbox').style.display, said: (document.getElementById('joinerr') || {}).textContent, toast: document.getElementById('toast').textContent, name: document.getElementById('name').value, ws: typeof agentWs === 'undefined' ? null : agentWs && agentWs.readyState, scene: typeof TitleScene === 'undefined' ? null : TitleScene.on, btn: (() => { const b = document.getElementById('join'); const r = b.getBoundingClientRect(); return [r.x, r.y, r.width, r.height, getComputedStyle(b).display, document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) && document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2).id]; })()})")) + f" {errors}") from None
        page.evaluate("(async () => { const p = myPos(); await rpc('dev_creatures', {clear: 40}); await rpc('dev_stamp', {x: p.x - 8, y: p.y - 8, rows: Array(17).fill('.'.repeat(17)), levels: [], roofs: [], heads: []}); return 1; })()")
        try:
            page.wait_for_function("meObs !== null && !!myPos() && HdLook.on && HdLook.faces > 500 && HdLook.catSeen() > .8", timeout=30000)
        except Exception:
            raise AssertionError("not in, or not drawn: " + str(page.evaluate("({obs: meObs !== null, pos: typeof myPos === 'function' && !!meObs && myPos(), on: HdLook.on, live: HdLook.live, faces: HdLook.faces, cat: HdLook.on ? HdLook.catSeen() : null, busy: HdLook.busy, "
                                 "join: document.getElementById('joinbox').style.display, said: (document.getElementById('joinerr') || {}).textContent, toast: document.getElementById('toast').textContent, name: document.getElementById('name').value})")) + f" {errors}") from None
        cdp = ctx.new_cdp_session(page)
        touch = lambda kind, x=0, y=0: cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y}]})
        for way in (1, -1):                                         # east, then back west: one of the two is open ground
            touch("touchStart", 90, 600)
            x0 = page.evaluate("myPos().x")
            for i in range(1, 6):                                   # (a move a frame drawn, not one every 30 ms of the machine's: #47)
                touch("touchMove", 90 + way * i * 8, 600)
                page.evaluate("new Promise((ok) => requestAnimationFrame(() => ok(1)))")
            try:                                                    # (held till three tiles gone that way, not 1.2 s; the closed way of the two ends it at 3 s)
                page.wait_for_function(f"Math.abs(myPos().x - {x0}) >= 3", timeout=3000)
            except Exception:
                pass
            touch("touchEnd")
        page.wait_for_function("HdLook.builds > 1 && HdLook.catSeen() > .8", timeout=8000)      # (the land was made again as you went, and you are still drawn on it)
        assert not errors, errors
        page.reload()                                               # again: the script and the pack are not fetched (kept for good under their own names)
        try:
            page.wait_for_function("typeof blocks !== 'undefined' && blocks.size > 0", timeout=30000)
        except Exception:
            raise AssertionError("loaded again, the land did not come: " + str(page.evaluate("({state: document.readyState, blocks: typeof blocks === 'undefined' ? null : blocks.size, me: typeof me === 'undefined' ? null : me, scene: typeof TitleScene === 'undefined' ? null : [TitleScene.on, TitleScene.S.tick], "
                                 "join: document.getElementById('joinbox').style.display, img: typeof IMG === 'undefined' ? null : Object.keys(IMG).length, pack: typeof ASSET_PACK === 'undefined' ? null : Object.keys(ASSET_PACK), ws: typeof ws === 'undefined' ? null : ws && ws.readyState, "
                                 "res: performance.getEntriesByType('resource').map((e) => [e.name.split('/').pop().slice(0, 24), Math.round(e.duration), e.transferSize])})")) + f" {errors}") from None
        kept = page.evaluate("performance.getEntriesByType('resource').filter((e) => /game\\.|pack\\./.test(e.name)).map((e) => [e.name.split('/').pop(), e.transferSize])")
        assert len(kept) == 2 and all(size == 0 for _, size in kept), kept
        assert not errors, errors
    finally:
        ctx.close()
