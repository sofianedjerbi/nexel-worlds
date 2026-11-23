"""Keys by place, whatever the keyboard (options.js keyId): an AZERTY's Z Q S D walk and are no letter's shortcut (its q
cycled the hand, its z opened build mode); break is the key over A (A on an AZERTY, Q on a QWERTY), X too ("you cannot
push X while going right"); Tab takes the next thing in hand; build mode is the key under A, or B; the caps say each key
as this keyboard types it. The events are sent as a keyboard sends them: where the key is (code), what it types (key)."""

KEY = "([type, code, key, shift]) => { dispatchEvent(new KeyboardEvent(type, {code, key, shiftKey: !!shift, bubbles: true, cancelable: true})); }"
SPY = "() => { window.__brk = 0; const f = useFacing; useFacing = (alt, again) => { if (alt) __brk++; return f(alt, again); }; }"
AZERTY = [("KeyQ", "a"), ("KeyW", "z"), ("KeyA", "q"), ("KeyZ", "w")]
QWERTY = [("KeyQ", "q"), ("KeyW", "w"), ("KeyA", "a"), ("KeyZ", "z")]


def tap(game, code, key, shift=False):
    game.js(KEY, ["keydown", code, key, shift])
    game.frames(1)
    game.js(KEY, ["keyup", code, key, shift])
    game.frames(1)


def test_azerty_z_and_q_walk_and_do_nothing_else(game):
    game.give(wood=1, stone=1)
    game.js("selectSlot(0)")
    for code, key, way in (("KeyA", "q", "W"), ("KeyW", "z", "N"), ("KeyS", "s", "S"), ("KeyD", "d", "E")):
        game.js(KEY, ["keydown", code, key])
        game.wait(f"walking && walking.dir === '{way}'")
        assert game.js("[handSlot, Build.on]") == [0, False], (code, key)         # the hand as it was, no build mode
        game.js(KEY, ["keyup", code, key])
        game.wait("!walking")
    assert game.js("[handSlot, Build.on]") == [0, False]


def test_the_key_over_a_breaks_on_any_layout_and_x_too(game):
    game.js(SPY)
    for code, key in (("KeyQ", "a"), ("KeyQ", "q"), ("KeyX", "x")):              # AZERTY's A, QWERTY's Q, and X
        n = game.js("__brk")
        game.js(KEY, ["keydown", code, key])
        game.frames(1)
        assert game.js("__brk") == n + 1 and not game.js("walking"), (code, key)  # it breaks; AZERTY's a does not walk
        game.js(KEY, ["keyup", code, key])
        game.frames(1)
    n = game.js("__brk")
    game.press("q", 100)                                                         # (a real key press, a QWERTY's)
    assert game.js("__brk") == n + 1


def test_tab_takes_the_next_thing_in_hand_and_held_shows_who_is_awake(game):
    game.give(wood=1, stone=1)
    game.js("selectSlot(0)")
    tap(game, "Tab", "Tab")
    assert game.js("handSlot") == 1
    tap(game, "Tab", "Tab", True)                                                # Shift+Tab: back
    assert game.js("handSlot") == 0
    game.press("Tab", 100)
    assert game.js("handSlot") == 1 and not game.js("document.body.classList.contains('tab')")
    game.js("selectSlot(0)")
    game.js(KEY, ["keydown", "Tab", "Tab"])                                      # held: who is awake, and the hand as it was
    game.wait("document.body.classList.contains('tab')")
    assert game.js("handSlot") == 0
    game.js(KEY, ["keyup", "Tab", "Tab"])
    assert not game.js("document.body.classList.contains('tab')")


def test_build_mode_is_the_key_under_a_or_b(game):
    for code, key in (("KeyZ", "w"), ("KeyB", "b"), ("KeyZ", "z")):              # AZERTY's W, B, QWERTY's Z
        tap(game, code, key)
        assert game.js("Build.on"), (code, key)
        tap(game, code, key)
        assert not game.js("Build.on"), (code, key)


def test_the_caps_say_each_key_as_this_keyboard_types_it(game):
    for code, key in AZERTY:                                                     # (each key, as it is pressed, says what it types)
        game.js(KEY, ["keyup", code, key])
    assert game.js("[capOf('alt'), capOf('next'), capOf('build'), ['w', 'a', 's', 'd'].map(keyCap).join('')]") == ["A", "Tab", "W", "ZQSD"]
    game.face(0, 1)
    game.wait("availableActions().some((r) => r[0] === 'A')")                   # the hint: "A Dig down", not "X"
    game.wait("[...document.querySelectorAll('#actions .key, #prompts .key')].some((k) => k.textContent === 'A')")
    assert not game.js("availableActions().some((r) => r[0] === 'X' || r[0] === 'Q')")
    game.press("h")
    game.page.click("#help .tab[data-i='0']")
    assert game.js("[...document.querySelector('#help .row kbd').parentNode.children].map((k) => k.textContent).join('')") == "ZQSD"
    game.page.click("#help .tab[data-i='2']")
    assert game.js("[...document.querySelectorAll('#help .row')][1].querySelector('.keys').textContent") == "AX"
    game.press("h")
    for code, key in QWERTY:
        game.js(KEY, ["keyup", code, key])
    assert game.js("[capOf('alt'), capOf('build'), ['w', 'a', 's', 'd'].map(keyCap).join('')]") == ["Q", "Z", "WASD"]
    assert not game.errors
