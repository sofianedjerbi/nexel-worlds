"""End-to-end fixtures: a fresh server on a temporary world, Chrome, and a player who has just woken up.

Run with `uv run pytest -m e2e` (needs Google Chrome). Every test fails on any page error.
"""

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
needs_sounds = pytest.mark.skipif(not (ROOT / "src" / "megastructure" / "web" / "audio" / "sfx.json").exists(),
                                  reason="no sounds built: uv run python tools/build_audio.py")


# `-m "e2e and quick"`: one short test of each file that has one (not the demo: it fetches Pyodide; nothing that times
# the machine), about a minute at -n 2: what an agent runs, with the files it touched, before handing back (README.md).
# file (test_e2e_<name>.py) -> its test
QUICK = {
    "account": "test_a_world_without_accounts_asks_nothing",
    "ask": "test_an_animal_is_named_with_a_name_tag",
    "behind": "test_a_tree_behind_a_ledge_is_cut_at_its_edge",
    "blocks": "test_land_that_changes_is_made_again",
    "bookkeys": "test_no_key_caps_on_a_phone",
    "bubbles": "test_what_is_typed_in_capitals_is_shouted",
    "build": "test_walls_are_thin_and_hide_nothing_and_a_side_door_has_its_leaf_and_shadow",
    "building": "test_tilling_needs_a_hoe",
    "caves": "test_standing_behind_a_hill_it_hides_you",
    "complete": "test_a_tap_takes_one_on_a_phone",
    "curve": "test_on_where_you_stand_nothing_moves_and_far_rows_go_up_to_a_horizon",
    "daylight": "test_at_night_the_lights_are_whole_pixels_in_steps",
    "depth": "test_the_ground_behind_a_step_is_darker_along_it",
    "digging": "test_a_dug_floor_is_earth_with_no_grass_at_the_foot_of_its_walls",
    "edges": "test_a_gate_is_seen_from_the_side_in_a_fence_that_runs_north_and_south",
    "fall": "test_dust_shows_on_level_ground_and_not_behind_a_ledge",
    "frame": "test_a_frame_paints_the_land_once",
    "gathering": "test_too_far_is_too_far",
    "hd": "test_two_walls_side_by_side_touch_and_a_bridge_is_drawn",
    "hd_behind": "test_on_a_small_hill_and_behind_it_no_window_opens_and_behind_it_you_show_through",
    "hd_land": "test_under_a_roof_an_open_pit_shows_a_bright_floor_and_the_meadow_stays",
    "hd_phone": "test_the_land_is_the_size_the_zoom_says_and_fills_a_screen_held_upright",
    "help": "test_the_help_is_a_window_of_short_pages",
    "holes": "test_the_first_frame_of_a_cut_is_a_checker_of_whole_px_of_paint_in_the_roll_too",
    "living": "test_who_stands_far_over_you_is_not_on_your_tile",
    "mark": "test_the_box_is_the_four_edges_of_its_top_and_the_two_uprights_and_the_foot_of_its_front",
    "menu": "test_the_volumes_act_at_once_and_are_kept",
    "models": "test_a_body_is_behind_the_posts_in_front_of_it_and_before_the_ones_behind",
    "moving": "test_walls_stop_you_and_turn_you",
    "narrow": "test_a_wall_one_tile_wide_has_one_top_from_end_to_end",
    "phone": "test_build_mode_by_thumbs",
    "phone_taps": "test_on_its_side_the_hud_is_one_low_band",
    "place": "test_the_floor_you_stand_on_is_seen_under_a_higher_floor_drawn_over_it",
    "prompts": "test_what_you_face_has_its_key_beside_it",
    "races": "test_an_ai_player_is_its_races_robot",
    "relief": "test_walls_have_no_dark_line_at_their_foot",
    "roll": "test_after_a_teleport_the_screen_keeps_its_picture_until_the_land_there_has_come",
    "section": "test_the_ground_beside_the_opening_keeps_the_shadow_of_the_land_that_stands",
    "shaders": "test_nothing_is_reflected_in_water_that_a_hill_hides",
    "social": "test_following_someone_by_their_link",
    "sound": "test_the_first_screen_has_its_own_piece_that_comes_in_slowly_and_recedes_in_the_world",
    "sunland": "test_the_land_north_of_water_is_seen_in_it",
    "swim": "test_a_page_older_than_the_servers_code_reloads_itself",
    "tall": "test_high_over_the_land_the_sky_is_behind_you",
    "title": "test_wake_up_says_the_world_is_still_coming",
    "title_scene": "test_the_islands_people_choose_what_they_do",
    "touch": "test_play_with_thumbs",
    "ui": "test_hotbar_keys_and_q_cycle_what_is_in_hand",
    "underground": "test_earth_left_between_two_tunnels_is_the_nearer_ones_back_wall_not_a_strip_of_meadow",
    "views": "test_v_goes_through_the_four_views_and_the_picture_page_has_them",
    "water": "test_a_bed_step_under_water_is_one_colour_no_checker",
    "wild": "test_a_named_animal_carries_its_name",
    "world": "test_a_coop_collects_the_eggs",
    "xray": "test_the_side_of_a_cliff_beside_open_water_is_not_seen_through",
    "zoom": "test_the_keys_of_the_main_row_zoom_on_any_layout_and_for_a_watcher_too",
}


def pytest_collection_modifyitems(config, items):
    again = config.pluginmanager.hasplugin("rerunfailures")
    for item in items:                                    # everything in this folder is end-to-end
        if "e2e" in item.path.parts:
            item.add_marker(pytest.mark.e2e)
            if QUICK.get(item.path.name[len("test_e2e_"):-3]) == getattr(item, "originalname", item.name):
                item.add_marker(pytest.mark.quick)
            if again:                                     # (a browser on a busy machine: a test that fails is tried once more,
                item.add_marker(pytest.mark.flaky(reruns=1))   #  a new player on a cleared meadow: and it is said, tests/conftest.py)


def pace_of(item) -> float:
    return 1.0 if item.get_closest_marker("realtime") else clock.PACE


def pytest_runtest_protocol(item, nextitem):
    """What the test after this one will play on, for the page that is loaded ahead (pages.py)."""
    clock.coming = pace_of(nextitem) if nextitem is not None and "game" in getattr(nextitem, "fixturenames", ()) else None


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


@pytest.fixture(autouse=True)
def pace(request):
    """The game's time runs clock.PACE times as fast in this test, in its world and on its pages (clock.py); a test
    marked `realtime` has it as it is."""
    clock.now = pace_of(request.node)
    if "server" in request.fixturenames:
        url = request.getfixturevalue("server")
        if _world_pace.get(url, 1.0) != clock.now:
            clock.set_world(url, clock.now)
            _world_pace[url] = clock.now
    yield
    if "browser" in request.fixturenames:                 # (a page left open is a player left awake in the next test's world: pages.py)
        request.getfixturevalue("browser").shut()
    clock.now = 1.0


@pytest.fixture
def circle_view(game):
    """What hides you shown as a circle round you seen through it (options.js: VIEWS): for the circle's own tests
    (pytestmark = pytest.mark.usefixtures("circle_view")); the other views: test_e2e_views.py."""
    game.js("setOpt('above', 'circle')")


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
