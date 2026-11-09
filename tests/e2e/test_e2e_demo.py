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
    page.goto(site)
    page.wait_for_function("blocks.size > 0", timeout=90000)       # Pyodide comes from the CDN on first load
    page.fill("#name", "visitor")
    page.click("#join")
    page.wait_for_function("meObs !== null", timeout=20000)
    tick = page.evaluate("rpc('ping').then(r => r.tick)")
    page.wait_for_timeout(1000)
    assert page.evaluate("rpc('ping').then(r => r.tick)") >= tick + 8      # the world ticks at 10 Hz in the tab
    page.wait_for_timeout(15500)                                    # past a save (every 15 s)
    page.reload()
    page.wait_for_function("blocks.size > 0", timeout=90000)
    page.wait_for_function("agents.some((a) => a.name === 'visitor')", timeout=5000)   # saved, asleep
    ctx.close()
    assert not errors, errors
