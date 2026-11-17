"""End-to-end fixtures: a fresh server on a temporary world, Chrome, and a player who has just woken up.

Run with `uv run pytest -m e2e` (needs Google Chrome). Every test fails on any page error.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from game import Game, new_name

ROOT = Path(__file__).parents[2]


def pytest_collection_modifyitems(config, items):
    again = config.pluginmanager.hasplugin("rerunfailures")
    for item in items:                                    # everything in this folder is end-to-end
        if "e2e" in item.path.parts:
            item.add_marker(pytest.mark.e2e)
            if again:                                     # (a browser on a busy machine: a test that fails is tried once more,
                item.add_marker(pytest.mark.flaky(reruns=1))   #  a new player on a cleared meadow: and it is said, tests/conftest.py)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    """A fresh world (fixed seed) with dev tools on; stopped at the end."""
    port, saves = free_port(), tmp_path_factory.mktemp("saves")
    import game as game_module
    game_module.SERVER_LOG = saves / "server.log"         # (what the server says is kept: a player who does not get in reads it)
    proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", str(saves), "--world", "e2e",
                             "--port", str(port), "--seed", "7", "--dev"], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=open(game_module.SERVER_LOG, "w"))
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=.2).close()
            break
        except OSError:
            time.sleep(.1)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(10)


@pytest.fixture(scope="session")
def browser():
    pw = pytest.importorskip("playwright.sync_api").sync_playwright().start()
    try:
        b = pw.chromium.launch(channel="chrome", headless=True)
    except Exception as e:  # noqa: BLE001 - no Chrome here: skip the suite rather than fail it
        pw.stop()
        pytest.skip(f"Chrome is needed for the end-to-end suite: {e}")
    yield b
    b.close()
    pw.stop()


def open_game(browser, server, name=None, zoom=4) -> Game:
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    g = Game(page, server)
    g.join(name or new_name(), zoom)
    return g


@pytest.fixture
def circle_view(game):
    """What hides you shown as a circle round you seen through it (options.js: VIEWS): for the circle's own tests
    (pytestmark = pytest.mark.usefixtures("circle_view")); the other views: test_e2e_views.py."""
    game.js("setOpt('above', 'circle')")


@pytest.fixture
def game(request, browser, server):
    """A new player, daytime, standing in the middle of a cleared 21x21 meadow with no animals nearby."""
    g = open_game(browser, server)
    g.clear_area()
    if request.node.path.name == "test_e2e_sound.py":     # (the music's tests were written at the old pace of this
        g.sleep(750)                                      #  set-up, 0.75 s of sleeps: the first screen's piece has receded by then)
    yield g
    errors = g.errors
    g.page.close()
    assert not errors, f"page errors: {errors}"
