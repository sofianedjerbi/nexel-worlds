"""The debug screen (js/f3.js): one readout for the game and the machine, opened by F3, ?perf=1, ?debug=1, /coords,
/perf. There were three made apart (the HD look's ?perf=1 box, /coords and /perf top right, F3's line of server
numbers): they are its sections now, and gone as boxes of their own."""

import pytest
from game import Game, new_name
from waits import FRAMES, until

TEXT = "(() => { const e = document.getElementById('f3'); return e && e.style.display !== 'none' ? e.innerText : ''; })()"
OLD = "['xyz', 'debug', 'hdperf'].filter((id) => document.getElementById(id))"


def test_f3_opens_and_shuts_it_and_it_says_where_you_are_and_what_a_frame_costs(game):
    game.js("F3.set(false)")
    assert game.js(TEXT) == "" and game.js(OLD) == []
    x, y = game.pos()
    game.press("F3", 100)
    game.wait(f"{TEXT}.includes('XYZ {x}.00 / {y}.00 / 0') && {TEXT}.includes(' fps') && {TEXT}.includes('ms/tick')", 5000)
    text = game.js(TEXT)
    for words in ("Facing ", "Tile ", "Chunk ", "Time ", "Near ", "script ", "ticks ", "world "):
        assert words in text, (words, text)
    look = game.js("""(() => { const d = document.querySelector('#f3 .f3c div'), s = getComputedStyle(d); return [s.fontFamily, s.borderRadius, s.backgroundColor, s.textShadow]; })()""")
    assert "SproutPixel" in look[0] and look[1] == "0px" and look[2].startswith("rgba(") and look[3].startswith("rgb("), look   # (the game's font on a see-through strip, a shadow; no rounded box)
    assert game.js(OLD) == [] and game.js("localStorage.getItem('nexel-f3')") == "1"
    game.press("F3", 100)
    assert game.js(TEXT) == "" and not game.js("F3.on")


def test_off_it_is_never_made(game):
    game.js("F3.set(false)")
    game.page.reload()
    game.wait("typeof F3 !== 'undefined' && typeof ready !== 'undefined'", 15000)
    game.frames(3)
    assert game.js("document.getElementById('f3')") is None and not game.js("F3.on")


@pytest.mark.realtime                                       # (it times the machine: what the HD look's section costs)
def test_perf_in_the_address_opens_it_with_the_hd_looks_section_and_it_costs_little(browser, server):
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    g = Game(page, server)
    try:
        page.goto(f"{server}/?zoom=4&perf=1")
        g.loaded = f"{server}/?zoom=4"                   # (join keeps this page)
        g.join(new_name("f3"), 4)
        g.wait(f"F3.on && {TEXT}.includes('HD look') && {TEXT}.includes(' fps') && {TEXT}.includes('XYZ ')", 8000)
        assert g.js(OLD) == []
        # what it costs a frame, on: its sample each frame and its text 4 times a second
        cost = g.js("""(() => new Promise((ok) => { const s0 = F3.sample; let t = 0, n = 0, f0 = 0;
          F3.sample = (...a) => { const b = performance.now(); s0(...a); t += performance.now() - b; };
          const f = () => { if (++f0 < 90) requestAnimationFrame(f); else { F3.sample = s0; ok([t, f0]); } }; requestAnimationFrame(f); }))()""")
        assert cost[0] / cost[1] < .3, cost
        assert not g.errors
    finally:
        g.js("F3.set(false)")
        page.close()


def test_it_says_what_the_gpu_takes_a_frame_by_its_own_clock_or_n_a(game):
    """The GPU's ms (js/gpu_time.js: a timer query a frame on every WebGL canvas): a phone's GPU fills px slowly, and
    only its own clock says how long it took. Without the timer (Safari): "GPU n/a"."""
    game.js("F3.set(true)")
    try:
        game.wait(f"{TEXT}.includes('GPU ')", 5000)
        if game.js("GpuTime.ok"):
            game.wait(f"/GPU \\d+\\.\\d ms a frame \\(mean, \\d+ canvases\\)/.test({TEXT})", 5000)
            assert game.js("GpuTime.ms") >= 0 and game.js("GpuTime.contexts") >= 1
        else:
            assert "GPU n/a" in game.js(TEXT)
        assert not game.errors
    finally:
        game.js("F3.set(false)")


def test_on_the_home_screen_it_is_not_shown_even_when_left_on(browser, server):
    """"why does the F3 menu appear in the homescreen?": left on from the game (saved), it waits for the game; the home
    screen is never covered by it."""
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(server)
    page.evaluate("localStorage.setItem('nexel-f3', '1')")
    page.reload()
    page.wait_for_function("document.body.classList.contains('scene')", timeout=20000)
    until(page, "!document.body.classList.contains('booting')")
    page.evaluate(FRAMES, 2)                                     # (shown, it is painted on its first frame: f3.js paints at once, then 4 times a second)
    assert page.evaluate(TEXT) == "" and not page.evaluate("document.body.classList.contains('f3')")
    page.close()
