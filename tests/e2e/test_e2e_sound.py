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
        game.press("e", 800)
        assert sound in played(game), f"placing a {item} should play {sound}: {sorted(played(game))}"

    cow = game.spawn("cow", 1, 0, still=30)           # hit a cow: the blow, and the cow answers
    game.face(1, 0)
    game.hold_item(None)
    game.press("e", 900)
    assert {"hit", "moo"} <= played(game), sorted(played(game))
    assert cow


def test_an_unknown_sound_is_reported_once_and_does_not_break(game):
    game.wait("sounds.manifest", 20000)
    game.js("(() => { sfx('no_such_sound'); sfx('no_such_sound', 1, 1); })()")
    assert game.js("[...sounds.warned]") == ["no_such_sound"]


def test_muting_stops_new_sounds(game):
    game.wait(ALL_LOADED, 60000)
    game.press("m")
    before = game.js("JSON.stringify(sounds.lastAt)")         # (when each sound last started: one ending changes nothing)
    game.hold(["d"], 600)
    assert game.js("JSON.stringify(sounds.lastAt)") == before
    game.press("m")


def test_a_piece_of_music_plays_as_a_moment_and_m_silences_it(game):
    """By day and by night a piece plays now and then (audio.js moments), streamed a few seconds at a time. Muted, it
    stops (nothing is fetched while it isn't heard); sound back on, another moment comes within seconds."""
    if not game.js("!!sounds.manifest"):
        game.wait("sounds.manifest", 20000)
    if not game.js("!!sounds.manifest.tracks && sounds.manifest.play.day.length > 0"):
        pytest.skip("no music rendered: music/pieces.py, music/master.py, then tools/build_audio.py")
    assert not game.js("music.on") and game.js("moment.next") > game.js("performance.now()")     # silence first: the first piece waits
    game.js("moment.next = 0")                                 # (not the 8 to 20 s a player waits)
    game.wait("music.on && music.nodes.size > 0", 30000)
    game.sleep(1500)
    assert game.js("music.gain.gain.value") > 0.05
    assert game.js("sounds.manifest.play.day.includes(music.key)") and game.js("music.nodes.size") <= 2
    assert game.js("moment.next") == float("inf") or game.js("moment.next === Infinity")       # none is due while one plays
    game.press("m")
    game.sleep(2600)
    assert game.js("music.gain.gain.value") < 0.02 and not game.js("music.on") and game.js("music.nodes.size") == 0
    game.press("m")
    game.wait("music.on && music.nodes.size > 0", 15000)
    game.sleep(1500)
    assert game.js("music.gain.gain.value") > 0.05


def test_the_boss_piece_takes_over_during_a_fight_and_hands_back(game):
    if not game.js("!!sounds.manifest"):
        game.wait("sounds.manifest", 20000)
    if not game.js("!!sounds.manifest.tracks && !!sounds.manifest.play.boss"):
        pytest.skip("no music rendered")
    game.js("moment.next = 0")
    game.wait("music.on && music.nodes.size > 0", 30000)
    game.js("(() => { window.realBossMusic = bossMusic; bossMusic = () => {}; })()")     # (boss.js turns it off twice a second: no boss in view)
    game.js("realBossMusic(true)")
    game.wait("bossTrack.on && bossTrack.nodes.size > 0", 15000)
    game.sleep(6500)                                           # (the moment takes SOUND.giveWay seconds to recede)
    assert game.js("bossTrack.key") == game.js("sounds.manifest.play.boss") and game.js("bossTrack.gain.gain.value") > 0.3
    assert not game.js("music.on") and game.js("music.gain.gain.value") < 0.02                 # the moment gave way
    game.js("moment.next = 0")
    game.sleep(1500)
    assert not game.js("music.on")                             # no moment starts while the fight is on
    game.js("realBossMusic(false)")
    game.sleep(500)
    assert not game.js("bossTrack.on") and game.js("moment.next") > game.js("performance.now()") + 15000    # silence after the fight
    game.js("bossMusic = realBossMusic")


def test_a_piece_ends_on_its_own_then_silence_and_night_has_its_own_pieces(game):
    if not game.js("!!sounds.manifest"):
        game.wait("sounds.manifest", 20000)
    if not game.js("!!sounds.manifest.tracks && sounds.manifest.play.night.length > 0"):
        pytest.skip("no music rendered")
    game.js("(() => { if (music.on) { muted = true; tune(.1); muted = false; } })()")          # (a moment left by another test)
    game.wait("!music.on && music.nodes.size === 0", 10000)
    key = game.js("(() => { SOUND.passes.day = 1; clock.night = false; moment.next = 0; moments(); return music.key; })()")
    assert game.js("sounds.manifest.play.day.includes(music.key)")
    game.wait("music.on && music.nodes.size > 0", 20000)
    game.wait("!music.on", 60000)                              # one pass of a day piece: about 35 s
    assert game.js("music.gain.gain.value") < 0.1              # it faded on its last chord
    wait = game.js("moment.next - performance.now()")
    assert 45000 < wait < 141000                               # SOUND.gap: silence before the next
    night = game.js("(() => { clock.night = true; moment.next = 0; moments(); return music.key; })()")
    assert game.js("sounds.manifest.play.night.includes(music.key)") and night != key


def test_moving_the_selection_makes_its_own_quiet_sound(game):
    """Another recipe in the crafting list, another hotbar slot: `pick`, quieter than a tab's `ui`."""
    game.wait(ALL_LOADED, 60000)
    assert game.js("sounds.manifest.sounds.pick.category") == "Interface"
    game.press("c")
    game.wait("isOpen('craft')", 5000)
    game.sleep(300)
    t0 = game.js("performance.now()")
    game.press("ArrowDown")
    game.sleep(200)
    assert game.js("sounds.lastAt.pick || 0") > t0             # the recipe below
    tab = game.js("sounds.lastAt.ui || 0")
    game.press("e")
    game.sleep(200)
    assert game.js("sounds.lastAt.ui || 0") > tab              # another kind: the tab's own sound, as before
    game.press("c")


def test_night_falling_on_a_day_piece_closes_it_and_brings_the_nights(game):
    """A day piece went on playing into the night, all its passes. Now the hour turning ends it at the end of the pass
    it is in, on its last chord; after a short silence (SOUND.turn) a night piece comes in."""
    if not game.js("!!sounds.manifest"):
        game.wait("sounds.manifest", 20000)
    if not game.js("!!sounds.manifest.tracks && sounds.manifest.play.night.length > 0"):
        pytest.skip("no music rendered")
    game.js("(() => { if (music.on) { muted = true; tune(.1); muted = false; } })()")
    game.wait("!music.on && music.nodes.size === 0", 10000)
    game.js("(() => { clock.night = false; moment.next = 0; moments(); })()")
    game.wait("music.on && music.nodes.size > 0", 20000)
    assert game.js("[music.hour, music.left > 1, !!music.turned]") == ["day", True, False]
    game.rpc("dev_time", phase=.8)
    game.wait("clock.night && music.turned", 8000)
    assert game.js("music.on && music.left <= 1")              # not cut: it plays on, to the end of this pass
    game.wait("!music.on", 80000)
    assert game.js("music.gain.gain.value") < 0.1              # closed on its last chord
    assert 0 < game.js("moment.next - performance.now()") < 12500
    game.wait("music.on && music.hour === 'night' && sounds.manifest.play.night.includes(music.key)", 20000)
    assert not game.errors


def test_the_first_screen_has_its_own_piece_that_comes_in_slowly_and_recedes_in_the_world(browser, server):
    """"Make that the home screen song", "with just a gradient at the beginning to avoid it popping out of nowhere":
    the first screen's piece starts at the first key (a browser plays nothing before one), rises from nothing, keeps
    the day's pieces out, and recedes once you are in the world."""
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("localStorage.setItem('megastructure-muted', '0')")
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined' && typeof titleOpen === 'function' && titleOpen()")
    js = page.evaluate
    assert js("!audio") and js("!menuTrack.on")                       # silence until a key
    page.keyboard.type("Tide")
    page.wait_for_function("!!sounds.manifest", timeout=20000)
    if not js("!!(sounds.manifest.play && sounds.manifest.play.menu)"):
        page.close()
        pytest.skip("no first-screen piece built: music/slowtide.py, then tools/build_audio.py")
    page.wait_for_function("menuTrack.on && menuTrack.nodes.size > 0", timeout=30000)
    assert js("menuTrack.key") == "high_tide"
    early = js("menuTrack.gain.gain.value")
    page.wait_for_timeout(2500)
    mid = js("menuTrack.gain.gain.value")
    assert early < 0.3 and early < mid, (early, mid)                  # the gradient: it rises, it does not pop
    page.wait_for_timeout(6000)
    assert js("menuTrack.gain.gain.value") > 0.5 and js("menuTrack.far.frequency.value") > 8000      # full and clear
    assert not js("music.on")                                         # the day's pieces wait
    page.keyboard.press("Enter")                                      # into the world
    page.wait_for_function("!!me", timeout=20000)
    page.wait_for_timeout(8500)
    assert not js("menuTrack.on") and js("menuTrack.nodes.size") == 0 and js("menuTrack.gain.gain.value") < 0.06
    page.close()
    assert not errors, errors
