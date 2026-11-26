"""Sound effects in the real client: the right sound for what happens, nothing breaks when one is missing."""

from pathlib import Path

import pytest

AUDIO = Path(__file__).parents[2] / "src" / "nexel_worlds" / "web" / "audio" / "sfx.json"
pytestmark = pytest.mark.skipif(not AUDIO.exists(), reason="no sounds built: uv run --extra audio python tools/build_audio.py (CI builds them: ci.yml)")

ALL_LOADED = """sounds.manifest && Object.values(sounds.manifest.sounds).flatMap((s) => s.files)
                .every((f) => sounds.buffers.get(f) instanceof AudioBuffer)"""


BOSS_STATE = """JSON.stringify({fight, muted, awake: awake(), loop: sounds.manifest.play[fight], on: bossTrack.on, nodes: bossTrack.nodes.size,
  at: bossTrack.at, run: bossTrack.run, music: music.on, ctx: audio && audio.state})"""


def played(game) -> set:
    return set(game.js("Object.keys(sounds.lastAt)"))


def test_every_file_loads_and_each_action_plays_its_own_sound(game):
    game.wait(ALL_LOADED, 60000)                      # joining was the first gesture: the cache warms in the background
    game.clear_area(4)                                # (flat grass: where you woke had a ledge and a bush east of it on main: a fall and a rustle, no step)
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
    game.press("x", 900)
    assert {"hit", "moo"} <= played(game), sorted(played(game))
    assert cow


# (each time struckOnce runs: the chops heard before it, and after)
ONCE = """(() => { window.__once = []; const f = struckOnce; window.struckOnce = (a, r) => { const n = () => __snd.filter((s) => s === 'chop').length;
  const b = n(); f(a, r); __once.push([b, n()]); }; return 1; })()"""


@pytest.mark.parametrize("drawn", [False, True])
def test_a_chop_with_no_frame_drawn_at_its_strike_still_sounds_and_never_twice(game, drawn):
    """The strike sounds on the frame drawn at a swing's fourth (characters.js). A frame longer than the swing's first
    third went from before it to the action's end: on the tests' fast clock on a runner (0.47 s of the game a frame),
    the axe felled the tree in silence, "chop" not in what test_e2e_ui test_actions_make_their_sounds heard (#47). No
    body drawn while it chops: the strike still sounds once, as the work is done (agent.js struckOnce). Drawn as
    always: when the dig ends, struckOnce adds a chop only if none was heard since the key was pressed. It added one
    to a chop a frame had drawn from the world's tick, before the server's word the dig had started: two chops."""
    game.js("window.__snd = []; const s0 = sfx; window.sfx = (n, x, y) => { __snd.push(n); s0(n, x, y); }")
    game.js(ONCE)
    game.stamp(-1, 0, ["T"])
    game.face(-1, 0)
    game.give(axe=1)
    game.hold_item("axe")
    if not drawn:
        game.js("(() => { window.__db = drawBody; drawBody = () => {}; return 1; })()")   # (no frame of the swing drawn)
    try:
        game.press("x", 0)
        game.wait(f"combAt({game.pos()[0] - 1}, {game.pos()[1]}) === 't'", 8000)
        game.wait("!busy && __once.length > 0", 3000)                              # (the dig's answer in: struckOnce has run)
    finally:
        if not drawn:
            game.js("(() => { drawBody = window.__db; return 1; })()")
    once = game.js("__once")
    assert all(after == max(1, before) for before, after in once) and not game.errors, (drawn, once, game.js("__snd"), game.errors)
    if not drawn:
        assert once[-1] == [0, 1], once                                            # (no frame chopped: struckOnce did, once)


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


@pytest.mark.parametrize("fight", ["boss", "nyxwing"])
def test_the_boss_piece_takes_over_during_a_fight_and_hands_back(game, fight):
    """Each fight its own loop (boss.js names it): Old Mossback's "boss" (Old Mossback), Nyxwing's "nyxwing" (Sugar
    rush). It comes in over the moment, none starts while it is on, silence after."""
    if not game.js("!!sounds.manifest"):
        game.wait("sounds.manifest", 20000)
    if not game.js(f"!!sounds.manifest.tracks && !!sounds.manifest.play['{fight}']"):
        pytest.skip("no music rendered")
    game.js("moment.next = 0")
    game.wait("music.on && music.nodes.size > 0", 30000)
    game.js("(() => { window.realBossMusic = bossMusic; bossMusic = () => {}; })()")     # (boss.js turns it off twice a second: no boss in view)
    game.js(f"realBossMusic('{fight}')")                       # (a fight is named since Nyxwing, #40: "boss" or "nyxwing", false)
    try:                                                       # (on GitHub's runners it once never started: say why, #47)
        game.wait("bossTrack.on && bossTrack.nodes.size > 0", 15000)
    except Exception:
        raise AssertionError("the boss piece never started: " + game.js(BOSS_STATE)) from None
    # the boss's piece comes in and the moment recedes (SOUND.giveWay): waited for, not timed (a slow runner's timers are late)
    game.wait("bossTrack.gain.gain.value > 0.3 && !music.on && music.gain.gain.value < 0.02", 20000)
    assert game.js("bossTrack.key") == game.js(f"sounds.manifest.play['{fight}']")
    game.js("moment.next = 0")
    game.sleep(1500)
    assert not game.js("music.on")                             # no moment starts while the fight is on
    game.js("realBossMusic(false)")
    game.wait("!bossTrack.on", 3000)
    assert game.js("moment.next") > game.js("performance.now()") + 15000    # silence after the fight
    game.js("bossMusic = realBossMusic")


def test_a_piece_ends_on_its_own_then_silence_and_night_has_its_own_pieces(game):
    if not game.js("!!sounds.manifest"):
        game.wait("sounds.manifest", 20000)
    if not game.js("!!sounds.manifest.tracks && sounds.manifest.play.night.length > 0"):
        pytest.skip("no music rendered")
    game.js("(() => { if (music.on) { muted = true; tune(.1); muted = false; } })()")          # (a moment left by another test)
    game.wait("!music.on && music.nodes.size === 0", 10000)
    key = game.js("(() => { SOUND.length.day = 1; clock.night = false; clock.phase = .5; moment.next = 0; moments(); return music.key; })()")
    assert game.js("sounds.manifest.play.day.includes(music.key)")
    game.wait("music.on && music.nodes.size > 0", 20000)
    game.wait("!music.on", 90000)                              # one pass of a day piece: 35 to 55 s
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



def test_far_from_home_by_day_the_adventure_piece_plays_and_the_night_keeps_its_own(game):
    """Sailing, or further than SOUND.away tiles from your bed (no bed yet: only sailing), a day's moment is the
    adventure's piece (play.adventure: Trailblazer). At night the night's pieces play wherever you are."""
    if not game.js("!!sounds.manifest"):
        game.wait("sounds.manifest", 20000)
    if not game.js("!!sounds.manifest.tracks && (sounds.manifest.play.adventure || []).length > 0"):
        pytest.skip("no music rendered")
    assert game.js("""(() => { const o = meObs, p = me; try {
        const at = (self, x, y) => { meObs = {self}; me = {x, y}; return farFromHome(); };
        return [at({spawn: [0, 0]}, 10, 10), at({spawn: [0, 0]}, SOUND.away + 5, 0), at({sailing: true}, 0, 0), at({}, 500, 500)];
      } finally { meObs = o; me = p; } })()""") == [False, True, True, False]
    stop = "(() => { if (music.on) { muted = true; tune(.1); muted = false; } })()"
    game.js(stop)
    game.wait("!music.on && music.nodes.size === 0", 10000)
    game.js("(() => { window.homeAway = farFromHome; farFromHome = () => true; clock.night = false; moment.next = 0; moments(); })()")
    game.wait("music.on && music.nodes.size > 0", 20000)
    assert game.js("[music.hour, music.key]") == ["adventure", "trailblazer"]
    game.js(stop)
    game.wait("!music.on && music.nodes.size === 0", 10000)
    game.rpc("dev_time", phase=.8)
    game.wait("clock.night", 8000)
    game.js("(() => { moment.next = 0; moments(); })()")
    game.wait("music.on && music.nodes.size > 0", 20000)
    assert game.js("music.hour") == "night"
    game.js("farFromHome = window.homeAway")
    assert not game.errors

def test_the_first_screen_has_its_own_piece_that_comes_in_slowly_and_recedes_in_the_world(browser, server):
    """"Make that the home screen song", "with just a gradient at the beginning to avoid it popping out of nowhere":
    the first screen's piece starts at the first key (a browser plays nothing before one), rises from nothing, keeps
    the day's pieces out, and recedes once you are in the world."""
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("localStorage.setItem('nexel-muted', '0')")
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
