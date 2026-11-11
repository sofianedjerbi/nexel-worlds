"""Sound effects in the real client: the right sound for what happens, nothing breaks when one is missing."""

from pathlib import Path

import pytest

AUDIO = Path(__file__).parents[2] / "src" / "megastructure" / "web" / "audio" / "sfx.json"
pytestmark = pytest.mark.skipif(not AUDIO.exists(), reason="no sounds built: uv run python tools/build_audio.py")

ALL_LOADED = """sounds.manifest && Object.values(sounds.manifest.sounds).flatMap((s) => s.files)
                .every((f) => sounds.buffers.get(f) instanceof AudioBuffer)"""


def played(game) -> set:
    return set(game.js("Object.keys(sounds.lastAt)"))


def test_every_file_loads_and_each_action_plays_its_own_sound(game):
    game.wait(ALL_LOADED, 60000)                      # joining was the first gesture: the cache warms in the background
    game.hold(["d"], 700)
    assert "step" in played(game)                     # walking on grass

    game.give(fence=1, rug=1, path=1)
    for item, face, sound in (("fence", (0, -1), "place_post"), ("rug", (0, 1), "place_soft"), ("path", (-1, 0), "place_path")):
        game.hold_item(item)
        game.face(*face)
        game.press("Space", 800)
        assert sound in played(game), f"placing a {item} should play {sound}: {sorted(played(game))}"

    cow = game.spawn("cow", 1, 0, still=30)           # hit a cow: the blow, and the cow answers
    game.face(1, 0)
    game.hold_item(None)
    game.press("Space", 900)
    assert {"hit", "moo"} <= played(game), sorted(played(game))
    assert cow


def test_an_unknown_sound_is_reported_once_and_does_not_break(game):
    game.wait("sounds.manifest", 20000)
    game.js("(() => { sfx('no_such_sound'); sfx('no_such_sound', 1, 1); })()")
    assert game.js("[...sounds.warned]") == ["no_such_sound"]


def test_muting_stops_new_sounds(game):
    game.wait(ALL_LOADED, 60000)
    game.press("m")
    before = game.js("sounds.voices + Object.keys(sounds.lastAt).length")
    game.hold(["d"], 600)
    assert game.js("sounds.voices + Object.keys(sounds.lastAt).length") == before
    game.press("m")


def test_the_music_loops_in_the_background_and_m_silences_it(game):
    if not game.js("sounds.manifest ? !!sounds.manifest.music : null"):
        game.wait("sounds.manifest", 20000)
    if not game.js("!!sounds.manifest.music"):
        pytest.skip("no music rendered: uv run python music/compose.py, then tools/build_audio.py")
    game.wait("music.node && music.node.loop && music.node.buffer.duration > 60", 90000)
    game.sleep(1500)
    assert game.js("music.gain.gain.value") > 0.05             # fading in
    game.press("m")
    game.sleep(1500)
    assert game.js("music.gain.gain.value") < 0.02             # faded out, still running
    game.press("m")
    game.sleep(1500)
    assert game.js("music.gain.gain.value") > 0.05
