"""End-to-end fixtures: a fresh server on a temporary world, Chrome, and a player who has just woken up.

Run with `uv run pytest -m e2e` (needs Google Chrome). Every test fails on any page error.
"""

import os
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

import clock
import pytest
from game import Game, new_name
from pages import Pages

ROOT = Path(__file__).parents[2]
# The sounds are built files, not in git (tools/build_audio.py; the demo's test builds them): a new worktree has none.
# A test that waits for them says so at once (one waited a minute for them, twice).
SOUNDS = (ROOT / "src" / "nexel_worlds" / "web" / "audio" / "sfx.json").exists()
needs_sounds = pytest.mark.skipif(not SOUNDS,
                                  reason="no sounds built: uv run python tools/build_audio.py")


# `-m "e2e and quick"`: one short test of each file that has one (not the demo: it fetches Pyodide; nothing that times
# the machine), about a minute at -n 2: what an agent runs, with the files it touched, before handing back (README.md).
# file (test_e2e_<name>.py) -> its test
QUICK = {
    "account": "test_a_world_without_accounts_asks_nothing",
    "ask": "test_an_animal_is_named_with_a_name_tag",
    "bookkeys": "test_no_key_caps_on_a_phone",
    "bubbles": "test_what_is_typed_in_capitals_is_shouted",
    "build": "test_a_door_in_a_run_going_north_is_a_side_door_and_opens_for_whoever_is_by_it",
    "building": "test_tilling_needs_a_hoe",
    "complete": "test_a_tap_takes_one_on_a_phone",
    "curve": "test_curved_world_is_a_setting_on_the_picture_page_on_unless_chosen_otherwise",
    "daylight": "test_the_day_is_a_gradient_not_day_then_night",
    "digging": "test_the_block_you_stand_on_is_dug_from_on_it_and_you_come_down_with_it",
    "edges": "test_a_gate_is_seen_from_the_side_in_a_fence_that_runs_north_and_south",
    "f3": "test_f3_opens_and_shuts_it_and_it_says_where_you_are_and_what_a_frame_costs",
    "fall": "test_a_drop_of_two_layers_is_still_a_hop_and_three_a_short_fall",
    "frame": "test_what_is_kept_from_frame_to_frame_is_what_would_be_worked_out_now",
    "gathering": "test_too_far_is_too_far",
    "hand": "test_the_slot_in_hand_is_bigger_and_says_its_name",
    "hd": "test_two_walls_side_by_side_touch_and_a_bridge_is_drawn",
    "hd_behind": "test_on_a_small_hill_and_behind_it_no_window_opens_and_behind_it_you_show_through",
    "hd_vanish": "test_at_a_mountain_s_foot_the_window_is_your_few_tiles_not_the_meadow_behind_it_and_it_does_not_flicker",
    "hd_land": "test_under_a_roof_an_open_pit_shows_a_bright_floor_and_the_meadow_stays",
    "hd_phone": "test_the_land_is_the_size_the_zoom_says_and_fills_a_screen_held_upright",
    "help": "test_the_help_is_a_window_of_short_pages",
    "layout": "test_the_key_over_a_breaks_on_any_layout_and_x_too",
    "living": "test_who_stands_far_over_you_is_not_on_your_tile",
    "menu": "test_the_volumes_act_at_once_and_are_kept",
    "models": "test_a_bridges_last_planks_step_down_to_the_bank",
    "moving": "test_walls_stop_you_and_turn_you",
    "phone": "test_build_mode_by_thumbs",
    "phone_taps": "test_on_its_side_the_hud_is_one_low_band",
    "prompts": "test_what_you_face_has_its_key_beside_it",
    "races": "test_an_ai_player_is_its_races_robot",
    "relief": "test_every_layer_is_the_same_step_up",
    "social": "test_following_someone_by_their_link",
    "sound": "test_the_first_screen_has_its_own_piece_that_comes_in_slowly_and_recedes_in_the_world",
    "swim": "test_a_page_older_than_the_servers_code_reloads_itself",
    "tall": "test_high_over_the_land_the_sky_is_behind_you",
    "target_px": "test_a_box_lies_on_its_block_its_line_on_every_edge_px_and_none_outside",
    "title": "test_wake_up_says_the_world_is_still_coming",
    "title_scene": "test_the_islands_people_choose_what_they_do",
    "touch": "test_play_with_thumbs",
    "ui": "test_hotbar_keys_and_tab_cycle_what_is_in_hand",
    "water": "test_a_pillar_and_an_islet_standing_in_a_pond_do_not_change_the_bed_round_them",
    "wild": "test_a_named_animal_carries_its_name",
    "world": "test_a_coop_collects_the_eggs",
    "zoom": "test_the_keys_of_the_main_row_zoom_on_any_layout_and_for_a_watcher_too",
}


def pytest_collection_modifyitems(config, items):
    # (no second try: "all tests should pass first try. a test that needs many tries to pass is a regression OR should be fixed", 2026-11-23)
    for item in items:                                    # everything in this folder is end-to-end
        if "e2e" in item.path.parts:
            item.add_marker(pytest.mark.e2e)
            if QUICK.get(item.path.name[len("test_e2e_"):-3]) == getattr(item, "originalname", item.name):
                item.add_marker(pytest.mark.quick)


def pace_of(item) -> float:
    return 1.0 if item.get_closest_marker("realtime") or item.get_closest_marker("stepped") else clock.PACE


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """The test's own result, kept on it for its fixtures' teardown (a failed test's pages are photographed: pages.py)."""
    rep = yield
    if rep.when == "call":
        item.rep_call = rep
    return rep


def pytest_runtest_protocol(item, nextitem):
    """What the test after this one will play on, for the page that is loaded ahead (pages.py)."""
    clock.coming = pace_of(nextitem) if nextitem is not None and "game" in getattr(nextitem, "fixturenames", ()) and not nextitem.get_closest_marker("stepped") else None


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
    proc = subprocess.Popen([sys.executable, "-m", "nexel_worlds.server", "--saves", str(saves), "--world", "e2e",
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


# What draws the land: E2E_CHROME_ARGS picks it (ci.yml: on runners with no GPU Chrome draws on the CPU, and the renderer
# it uses for that sets how slow every frame is); the run's last line names the one it got
RENDERER = []


def webgl_renderer(b) -> str:
    page = b.new_page()
    try:
        return page.evaluate("""() => { const gl = document.createElement('canvas').getContext('webgl2'); if (!gl) return 'no WebGL2';
          const d = gl.getExtension('WEBGL_debug_renderer_info'); return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); }""")
    finally:
        page.close()


def pytest_terminal_summary(terminalreporter):
    if RENDERER:
        terminalreporter.write_line(f"WebGL renderer: {RENDERER[0]} (E2E_CHROME_ARGS={os.environ.get('E2E_CHROME_ARGS', '')!r})")
    if MACHINE:
        terminalreporter.write_line(f"Pace: {MACHINE[1]} (a frame of the game: {MACHINE[0]:.0f} ms; E2E_PACE={os.environ.get('E2E_PACE', '4')})")


# RUNNER-LIKE (#275, tools/e2e_local.sh): E2E_RUNNER_LIKE=<rate> plays a GitHub runner on the Mac, to loop one flaky test
# in minutes: the land drawn on the CPU (SwiftShader, as the runners' lavapipe) and every page's CPU slowed `rate` times
# (CDP Emulation.setCPUThrottlingRate), its frames ~100-120 ms as in the CI logs. Never the whole suite: that is GitHub's
RUNNER_LIKE = float(os.environ.get("E2E_RUNNER_LIKE") or 0)


def throttled(b):
    """The browser `b`, each page it makes slowed RUNNER_LIKE times (its contexts' pages too)."""
    def slow(page):
        page._throttle = page.context.new_cdp_session(page)    # (kept: the rate holds while the session lives)
        page._throttle.send("Emulation.setCPUThrottlingRate", {"rate": RUNNER_LIKE})
        return page
    new_page, new_context = b.new_page, b.new_context
    b.new_page = lambda *a, **kw: slow(new_page(*a, **kw))
    def context(*a, **kw):
        ctx = new_context(*a, **kw)
        ctx.on("page", slow)
        return ctx
    b.new_context = context
    return b


@pytest.fixture(scope="session")
def browser():
    pw = pytest.importorskip("playwright.sync_api").sync_playwright().start()
    args = shlex.split(os.environ.get("E2E_CHROME_ARGS", "")) + (["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] if RUNNER_LIKE else [])
    try:
        b = pw.chromium.launch(channel="chrome", headless=True, args=args)
    except Exception as e:  # noqa: BLE001 - no Chrome here: skip the suite rather than fail it
        pw.stop()
        pytest.skip(f"Chrome is needed for the end-to-end suite: {e}")
    if RUNNER_LIKE:
        b = throttled(b)
    RENDERER.append(webgl_renderer(b))
    yield Pages(b)                                        # (its pages on the tests' clock, counted and shut: pages.py)
    b.close()
    pw.stop()


def open_game(browser, server, name=None, zoom=4) -> Game:
    g = (zoom == 4 and browser.take()) or Game(browser.new_page(viewport={"width": 1200, "height": 800}), server)
    if g.url != server:                                   # (asked for ahead, for another world: test_e2e_curve.py has one of its own)
        g.page.close()
        g = Game(browser.new_page(viewport={"width": 1200, "height": 800}), server)
    g.join(name or new_name(), zoom)
    return g


_world_pace = {}         # a world's address -> the pace it was last given
MACHINE = []             # [ms of the machine's time a frame of the game took, the pace fitted to it]

# the frames' length on a page that plays (ms, of 40: the one a quarter are longer than)
FRAMES = """() => new Promise((ok) => { const t = []; const f = (n) => { t.push(n); if (t.length <= 40) requestAnimationFrame(f);
  else { const d = t.slice(1).map((v, i) => v - t[i]).sort((a, b) => a - b); ok(d[Math.floor(d.length * .75)]); } }; requestAnimationFrame(f); })"""


@pytest.fixture(scope="session")
def machine(browser, server):
    """What a frame of the game costs this machine, measured once on a player's page at the game's own pace, sprinting
    over the land (the frames a test has), and the tests' pace fitted to it (clock.fit: on the runners, Chrome drawing
    on the CPU, it is about 1; on the Mac, 4)."""
    if clock.PACE > 1:
        page = browser._inner.new_page(viewport={"width": 1200, "height": 800})     # (not paced: its frames as they are)
        try:
            g = Game(page, server)
            g.join(new_name("pace"))
            # (sprinting, the land made as it comes: what a test's frames cost. Standing in the meadow just woken, a runner
            # measured 17 ms a frame and got pace 4, and its tests then walked at 1.3 tiles a second, frames of 0.1 s
            # and more cut there: what costs a frame is the land being made and drawn as you go)
            page.keyboard.down("Shift")
            page.keyboard.down("d")
            try:
                ms = page.evaluate(FRAMES)
            finally:
                page.keyboard.up("d")
                page.keyboard.up("Shift")
        finally:
            page.close()
        was = clock.PACE
        MACHINE.extend([ms, clock.fit(ms)])
        if clock.coming == was:                           # (the first test's next page, asked for at the pace before)
            clock.coming = clock.PACE


@pytest.fixture(autouse=True)
def pace(request):
    """The game's time runs clock.PACE times as fast in this test, in its world and on its pages (clock.py); a test
    marked `realtime` has it as it is."""
    if "browser" in request.fixturenames:
        request.getfixturevalue("machine")
    clock.now = pace_of(request.node)
    clock.step = request.node.get_closest_marker("stepped") is not None   # (its pages' time 1/60 s a frame: clock.py STEP)
    if "server" in request.fixturenames:
        url = request.getfixturevalue("server")
        if _world_pace.get(url, 1.0) != clock.now:
            clock.set_world(url, clock.now)
            _world_pace[url] = clock.now
    yield
    if "browser" in request.fixturenames:                 # (a page left open is a player left awake in the next test's world: pages.py)
        rep = getattr(request.node, "rep_call", None)
        request.getfixturevalue("browser").shut(failed=bool(rep and rep.failed))
    if clock.step and "server" in request.fixturenames:  # (a stepped page set the world's pace to its own, 0.15 on a slow runner: unknown now, so the
        _world_pace[request.getfixturevalue("server")] = None   # next test sets it whatever its pace, 1 too: dropped, it read as 1 and a test at 1 kept 0.15)
    clock.now, clock.step = 1.0, False


@pytest.fixture
def game(request, browser, server):
    """A new player, daytime, standing in the middle of a cleared 21x21 meadow with no animals nearby."""
    g = open_game(browser, server)
    browser.ahead(lambda page: Game(page, server).load(4, wait="commit"))      # (the next test's page comes while this one plays: pages.py)
    g.rpc("dev_luck", luck=1)                             # (a test before made every drop sure, lucky(): for as long as the server runs)
    g.js("opt('depth') || setOpt('depth', true)")       # (the land's depth, on as a player has it: a test that turned it off to look at the land as painted does not leave it off for the next)
    g.clear_area()
    if request.node.path.name == "test_e2e_sound.py":     # (the music's tests were written at the old pace of this
        g.sleep(750)                                      #  set-up, 0.75 s of sleeps: the first screen's piece has receded by then)
    yield g
    errors = g.errors
    g.page.close()
    assert not errors, f"page errors: {errors}"
