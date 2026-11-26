"""tools/affected.py: which tests a change asks for (a small repo of its own in tmp_path, and the real one)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import affected as A  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def repo(tmp_path, files):
    for f, text in files.items():
        p = tmp_path / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def test_the_globals_a_script_makes():
    js = "const WayShow = (() => {})();\nlet busyNow = 0, x = 1;\nfunction drawTile(a) {}\nclass Keyhole {}\nwindow.HdLook = {};\n  const inner = 1;\nconst {alpha, beta: gamma} = Q;\nconst ab = 1;"
    assert A.globals_of(js) == {"WayShow", "busyNow", "drawTile", "Keyhole", "HdLook", "alpha", "gamma"}
    assert A.globals_of("const Nyx = 1;\nconst IMG = {}, now = 0;") == {"Nyx"}      # (a module's name of 3, not a constant or a word)


def test_a_part_of_a_split_file_asks_for_the_tests_of_the_whole(tmp_path):
    """(nyxwing_sky.js is a part of nyxwing.js: its tests use Nyx, the whole's, and a part's change ran none of them)"""
    r = repo(tmp_path, {"src/nexel_worlds/web/js/nyxwing.js": "const Nyx = (() => {})();\n",
                        "src/nexel_worlds/web/js/nyxwing_sky.js": "const NyxSky = (K) => {};\n",
                        "src/nexel_worlds/web/js/lone_part.js": "const LonePart = 1;\n",
                        "tests/e2e/test_e2e_nyx.py": 'def test_a(g):\n    g.wait("Nyx.owns")\n'})
    assert A.affected(["src/nexel_worlds/web/js/nyxwing_sky.js"], r)[0] == ["tests/e2e/test_e2e_nyx.py"]
    assert A.affected(["src/nexel_worlds/web/js/lone_part.js"], r)[0] == []          # (no lone.js beside it: no whole)


def test_a_js_change_asks_for_the_tests_that_use_its_globals_not_those_that_only_say_the_word(tmp_path):
    r = repo(tmp_path, {"src/nexel_worlds/web/js/wayshow.js": "const WayShow = {};\nfunction wayTrail() {}\n",
                        "tests/e2e/test_e2e_way.py": 'def test_a(g):\n    g.wait("WayShow.cur")\n',
                        "tests/e2e/test_e2e_doc.py": '"""WayShow is drawn by wayshow"""\ndef test_b(g):\n    pass  # WayShow\n',
                        "tests/e2e/test_e2e_file.py": 'def test_c(g):\n    """x"""\n    p = "web/js/wayshow.js"\n',
                        "tests/e2e/test_e2e_call.py": 'def test_d(game):\n    game.js("1")\n'})
    e2e, unit, quick = A.affected(["src/nexel_worlds/web/js/wayshow.js"], r)
    assert e2e == ["tests/e2e/test_e2e_file.py", "tests/e2e/test_e2e_way.py"] and unit == [] and not quick
    r2 = repo(tmp_path, {"src/nexel_worlds/web/js/game.js": "const gameThing = 1;\n"})
    assert A.affected(["src/nexel_worlds/web/js/game.js"], r2)[0] == []          # (game.js("..."): the test's method, not the file)


def test_the_hd_look_css_python_and_test_files_fall_back_to_their_sets(tmp_path):
    r = repo(tmp_path, {"src/nexel_worlds/web/js/vox_water.js": "const VoxWater = {};\n",
                        "tests/e2e/test_e2e_hd_sky.py": "def test_a(g): pass\n", "tests/e2e/test_e2e_menu.py": "def test_m(g): pass\n",
                        "tests/e2e/test_e2e_world.py": "def test_w(g): pass\n", "tests/e2e/test_e2e_dig.py": "def test_d(g): g.rpc('x')  # building\n",
                        "tests/test_vox_layer.py": "F = 'vox_engine.js'\n", "tests/test_building.py": "from nexel_worlds import building\n",
                        "tests/test_other.py": "def test_o(): pass\n"})
    e2e, unit, _ = A.affected(["src/nexel_worlds/web/js/vox_water.js"], r)
    assert e2e == ["tests/e2e/test_e2e_hd_sky.py"] and unit == ["tests/test_vox_layer.py"]
    assert A.affected(["src/nexel_worlds/web/css/menu.css"], r)[0] == ["tests/e2e/test_e2e_menu.py"]
    e2e, unit, _ = A.affected(["src/nexel_worlds/building.py"], r)
    assert e2e == ["tests/e2e/test_e2e_world.py"] and unit == ["tests/test_building.py"]
    assert A.affected(["src/nexel_worlds/nowhere.py"], r)[1] == ["tests/test_building.py", "tests/test_other.py", "tests/test_vox_layer.py"]   # (no unit test names it: all)
    assert A.affected(["tests/e2e/test_e2e_menu.py", "tests/e2e/game.py"], r) == (["tests/e2e/test_e2e_menu.py"], [], True)


def test_on_the_real_repo_known_files_ask_for_their_tests():
    e2e = A.affected(["src/nexel_worlds/web/js/wayshow.js"], ROOT)[0]
    assert "tests/e2e/test_e2e_wayshow.py" in e2e and "tests/e2e/test_e2e_sound.py" not in e2e
    e2e = A.affected(["src/nexel_worlds/web/js/hd_sun.js"], ROOT)[0]
    assert "tests/e2e/test_e2e_hd_sun.py" in e2e and all(Path(t).name.startswith("test_e2e_hd") for t in e2e if "hd" in t)
    e2e, unit, _ = A.affected(["src/nexel_worlds/devtools.py"], ROOT)
    assert "tests/test_devtools.py" in unit and "tests/e2e/test_e2e_world.py" in e2e


def test_the_sound_pipeline_asks_for_every_test_that_plays_sound(tmp_path):
    """The sounds made again (tools/build_audio.py, music/**, the CI workflow that builds them): the tests that play
    sound are those audio.js asks for, also when audio.js itself did not change (#47: a sound test did not run)."""
    r = repo(tmp_path, {"src/nexel_worlds/web/js/audio.js": "const bossTrack = {};\nfunction bossMusic(on) {}\n",
                        "tests/e2e/test_e2e_sound.py": 'def test_a(g):\n    g.wait("bossTrack.on")\n',
                        "tests/e2e/test_e2e_walk.py": "def test_b(g):\n    pass\n"})
    for f in ("tools/build_audio.py", "music/adventure.py", "music/sfx_map.json", ".github/workflows/ci.yml"):
        assert A.affected([f], r)[0] == ["tests/e2e/test_e2e_sound.py"], f
    assert A.affected(["README.md"], r)[0] == []


def test_a_helper_of_the_browser_tests_asks_for_the_tests_that_import_it(tmp_path):
    """#146: #78 changed waits.py, and no browser test ran. A helper asks for the test files that import it, directly or
    through another helper; conftest.py (and what it imports) for every one: pytest gives its fixtures to all."""
    r = repo(tmp_path, {"tests/e2e/waits.py": "def arrive(): pass\n",
                        "tests/e2e/game.py": "from waits import arrive\nclass Game: pass\n",
                        "tests/e2e/home.py": "PLACE = (0, -40)\n",
                        "tests/e2e/pages.py": "class Pages: pass\n",
                        "tests/e2e/conftest.py": "import pytest\nfrom pages import Pages\n",
                        "tests/e2e/test_e2e_a.py": "from game import Game\n\ndef test_a(): pass\n",
                        "tests/e2e/test_e2e_b.py": "import home, os\n\ndef test_b(game): pass\n",
                        "tests/e2e/test_e2e_c.py": "from test_e2e_b import helper\n\ndef test_c(): pass\n",
                        "tests/e2e/test_e2e_d.py": "def test_d(game): pass\n",
                        "tests/e2e/durations.json": "{}\n"})
    every = [f"tests/e2e/test_e2e_{x}.py" for x in "abcd"]
    assert A.affected(["tests/e2e/waits.py"], r) == (["tests/e2e/test_e2e_a.py"], [], False)          # (through game.py)
    assert A.affected(["tests/e2e/home.py"], r)[0] == ["tests/e2e/test_e2e_b.py", "tests/e2e/test_e2e_c.py"]   # (and what imports b)
    assert A.affected(["tests/e2e/conftest.py"], r) == (every, [], False)
    assert A.affected(["tests/e2e/pages.py"], r)[0] == every                                           # (conftest imports it)
    assert A.affected(["tests/e2e/test_e2e_b.py"], r)[0] == ["tests/e2e/test_e2e_b.py", "tests/e2e/test_e2e_c.py"]
    assert A.affected(["tests/e2e/test_e2e_d.py"], r) == (["tests/e2e/test_e2e_d.py"], [], False)
    assert A.affected(["tests/e2e/durations.json"], r) == ([], [], True)                               # (nothing imports it: the quick set)


def test_on_the_real_repo_a_change_to_waits_py_runs_browser_tests():
    e2e, _, _ = A.affected(["tests/e2e/waits.py"], ROOT)
    assert len(e2e) > 20 and "tests/e2e/test_e2e_moving.py" in e2e
