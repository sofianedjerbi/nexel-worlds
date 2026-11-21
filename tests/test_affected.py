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


def test_a_js_change_asks_for_the_tests_that_use_its_globals_not_those_that_only_say_the_word(tmp_path):
    r = repo(tmp_path, {"src/megastructure/web/js/wayshow.js": "const WayShow = {};\nfunction wayTrail() {}\n",
                        "tests/e2e/test_e2e_way.py": 'def test_a(g):\n    g.wait("WayShow.cur")\n',
                        "tests/e2e/test_e2e_doc.py": '"""WayShow is drawn by wayshow"""\ndef test_b(g):\n    pass  # WayShow\n',
                        "tests/e2e/test_e2e_file.py": 'def test_c(g):\n    """x"""\n    p = "web/js/wayshow.js"\n',
                        "tests/e2e/test_e2e_call.py": 'def test_d(game):\n    game.js("1")\n'})
    e2e, unit, quick = A.affected(["src/megastructure/web/js/wayshow.js"], r)
    assert e2e == ["tests/e2e/test_e2e_file.py", "tests/e2e/test_e2e_way.py"] and unit == [] and not quick
    r2 = repo(tmp_path, {"src/megastructure/web/js/game.js": "const gameThing = 1;\n"})
    assert A.affected(["src/megastructure/web/js/game.js"], r2)[0] == []          # (game.js("..."): the test's method, not the file)


def test_the_hd_look_css_python_and_test_files_fall_back_to_their_sets(tmp_path):
    r = repo(tmp_path, {"src/megastructure/web/js/vox_water.js": "const VoxWater = {};\n",
                        "tests/e2e/test_e2e_hd_sky.py": "def test_a(g): pass\n", "tests/e2e/test_e2e_menu.py": "def test_m(g): pass\n",
                        "tests/e2e/test_e2e_world.py": "def test_w(g): pass\n", "tests/e2e/test_e2e_dig.py": "def test_d(g): g.rpc('x')  # building\n",
                        "tests/test_vox_layer.py": "F = 'vox_engine.js'\n", "tests/test_building.py": "from megastructure import building\n",
                        "tests/test_other.py": "def test_o(): pass\n"})
    e2e, unit, _ = A.affected(["src/megastructure/web/js/vox_water.js"], r)
    assert e2e == ["tests/e2e/test_e2e_hd_sky.py"] and unit == ["tests/test_vox_layer.py"]
    assert A.affected(["src/megastructure/web/css/menu.css"], r)[0] == ["tests/e2e/test_e2e_menu.py"]
    e2e, unit, _ = A.affected(["src/megastructure/building.py"], r)
    assert e2e == ["tests/e2e/test_e2e_world.py"] and unit == ["tests/test_building.py"]
    assert A.affected(["src/megastructure/nowhere.py"], r)[1] == ["tests/test_building.py", "tests/test_other.py", "tests/test_vox_layer.py"]   # (no unit test names it: all)
    assert A.affected(["tests/e2e/test_e2e_menu.py", "tests/e2e/game.py"], r) == (["tests/e2e/test_e2e_menu.py"], [], True)


def test_on_the_real_repo_known_files_ask_for_their_tests():
    e2e = A.affected(["src/megastructure/web/js/wayshow.js"], ROOT)[0]
    assert "tests/e2e/test_e2e_wayshow.py" in e2e and "tests/e2e/test_e2e_sound.py" not in e2e
    e2e = A.affected(["src/megastructure/web/js/hd_sun.js"], ROOT)[0]
    assert "tests/e2e/test_e2e_hd_sun.py" in e2e and all(Path(t).name.startswith("test_e2e_hd") for t in e2e if "hd" in t)
    e2e, unit, _ = A.affected(["src/megastructure/devtools.py"], ROOT)
    assert "tests/test_devtools.py" in unit and "tests/e2e/test_e2e_world.py" in e2e
