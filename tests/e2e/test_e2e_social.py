"""Two people: chat, giving, mail; a spectator watching; boats."""

import pytest
from conftest import open_game


@pytest.fixture
def friend(browser, server, game):
    """A second player standing two tiles east of the first."""
    g = open_game(browser, server)
    x, y = game.pos()
    g.rpc("dev_teleport", x=x + 2, y=y)
    g.sleep(1200)
    yield g
    errors = g.errors
    g.page.close()
    assert not errors, f"page errors: {errors}"


def test_chat_shows_and_fades(game, friend):
    game.press("Enter", 200)
    game.page.keyboard.type("hello over there")
    game.press("Enter", 1200)
    for g in (game, friend):                                 # both see it in the chat and as a bubble
        assert "hello over there" in g.js("$('chatlog').innerText")
        assert g.js("bubbles.some((b) => b.text === 'hello over there')")
    friend.sleep(10500)
    assert friend.js("[...$('chatlog').children].pop().classList.contains('old')")   # faded away


def test_give_and_see_each_other(game, friend):
    game.give(berries=3)
    assert game.js(f"[...ents.values()].some((q) => q.e && q.e.name === '{friend.name}')")
    assert friend.name in game.js("$('agents').innerText")
    game.hold_item("berries")
    x, y = friend.pos()
    me = game.pos()
    game.js(f"perform({{x: {x}, y: {y}}}, intent({{x: {x}, y: {y}}}, false))")
    game.sleep(1000)
    assert friend.inv("berries") == 1 and game.inv("berries") == 2


def test_letters_through_a_mailbox(game, friend):
    game.give(mailbox=1)
    game.hold_item("mailbox")
    game.face(1, 0)
    game.press("Space", 800)
    game.press("0", 100)
    game.press("Space", 500)                                 # open the mailbox panel
    assert game.js("$('mail').style.display") == "block"
    game.page.fill("#letter", "come see my farm")
    game.page.click("#postbtn")
    game.sleep(700)
    game.press("Escape", 200)
    mx, my = game.pos()[0] + 1, game.pos()[1]
    friend.js(f"(() => {{ actTarget = {{x: {mx}, y: {my}}}; openMailPanel(actTarget); }})()")
    friend.page.click("#openbtn")
    friend.sleep(800)
    assert "come see my farm" in friend.js("$('letters').innerText")


def test_watching_as_a_spectator(browser, server, game):
    page = browser.new_page(viewport={"width": 1000, "height": 700})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined'")
    page.click("#watch")
    page.wait_for_function("blocks.size > 0", timeout=8000)
    page.wait_for_timeout(1500)
    assert game.name in page.evaluate("$('agents').innerText")
    page.close()
    assert not errors


def test_boat_launch_sail_and_moor(game):
    game.stamp(1, -3, ["~~~~~~", "~~~~~~", "~~~~~~"])        # a pond to the north-east
    game.give(boat=1)
    game.rpc("dev_teleport", x=game.pos()[0] + 1, y=game.pos()[1] - 0)
    game.sleep(800)
    game.hold_item("boat")
    game.face(0, -1)
    game.press("Space", 800)
    x, y = game.pos()
    assert game.tile(0, -1) == "V"
    game.js(f"act('move_to', {{x: {x}, y: {y - 1}}})")       # board
    game.sleep(800)
    assert game.server()["sailing"]
    game.hold(["w"], 380)
    game.sleep(600)
    assert game.server()["sailing"]
    game.hold(["s"], 900)                                    # back to the shore: you step out, the boat stays
    game.sleep(800)
    assert not game.server()["sailing"]


def test_the_goals_stay_and_tab_shows_the_day_who_you_are_and_who_is_awake(game, friend, browser, server):
    """While you play: the goals, top left, with the help's link under them; no title panel, no list of who is awake.
    Held, Tab shows one panel at the top: the day, your name and where you are, who else is awake; it is there at
    once (the goals were on Tab for a day and slid in again at each press, which looked like lag) and goes when the
    key is let go. Someone only watching keeps the title and the list: they pick who to follow."""
    box = "(id) => { const r = $(id).getBoundingClientRect(); return r.width ? [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)] : null; }"
    goals = game.js(box, "goals")
    assert goals and goals[0] <= 12 and goals[1] <= 12 and game.js(box, "brand") is None and game.js(box, "side") is None
    assert len(game.js("[...document.querySelectorAll('.goal')].map((g) => g.innerText)")) == 3 and game.js("$('goalhelp').innerText") == "help (H)"
    was = game.js("$('help').style.display")
    game.js("$('goalhelp').click()")                                               # the help, from the goals
    assert game.js("$('help').style.display") != was
    game.js("$('goalhelp').click()")
    game.wait(f"agents.filter((a) => a.online).length >= 2 && agents.some((a) => a.name === {friend.name!r})", 10000)   # (the list is asked for now and then)
    game.page.keyboard.down("Tab")
    shown = game.js("""() => new Promise((ok) => requestAnimationFrame(() => { const s = $('side'), r = s.getBoundingClientRect();     // the frame after the key
      ok({top: r.top, mid: Math.round(r.left + r.width / 2), text: s.innerText, moving: s.getAnimations({subtree: true}).length}); }))""")
    assert shown["top"] >= 70 and abs(shown["mid"] - game.js("innerWidth") / 2) <= 2 and shown["moving"] == 0     # there, in the middle, nothing sliding in
    lines = shown["text"].split("\n")
    assert lines[0].startswith("day ") and lines[1].startswith(game.name + " · ")  # the day and the hour; who you are, and where
    assert f"{game.name} (you)" in shown["text"] and friend.name in shown["text"]  # ...and who is awake
    assert game.js(box, "goals") == goals                                          # (the goals do not move for it)
    game.page.keyboard.up("Tab")
    game.sleep(100)
    assert game.js(box, "side") is None
    game.give(wood=4)                                                              # a goal done: ticked where it is, no line of news for it
    game.sleep(600)
    assert "Goal done" not in game.toast() and game.js("document.querySelectorAll('.goal.done').length") == 1
    page = browser.new_page()                                                      # someone watching
    page.goto(server)
    page.wait_for_function("typeof agents !== 'undefined' && agents.some((a) => a.online)", timeout=15000)
    assert page.evaluate("$('side').getBoundingClientRect().width") > 100 and page.evaluate("$('brand').innerText").startswith("MEGASTRUCTURE")
    assert page.evaluate("getComputedStyle($('tabday')).display") == "none" and "help (H)" in page.evaluate("$('brand').innerText")
    page.close()


SAID = """() => { window.__said = []; const P = AudioBufferSourceNode.prototype, o = P.start, say = new Set(sounds.manifest.sounds.say.files.map((f) => sounds.buffers.get(f)));
  P.start = function (when, off, dur) { if (say.has(this.buffer)) window.__said.push([when, dur, this.playbackRate.value]); return o.apply(this, arguments); }; return say.size; }"""


def test_a_line_is_said_in_a_run_of_syllables_as_it_is_written(game, friend):
    """Speech was one sound a line (and none for your own). It is a run of short pieces of the recorded "say" voices,
    about one for every two letters, each at its letter's pitch and the speaker's own, on the audio clock, while the
    line is written out in its bubble. A space is a breath; a question rises at its end; another speaker, another voice."""
    for g in (game, friend):
        g.wait("sounds.manifest && sounds.manifest.sounds.say.files.every((f) => sounds.buffers.get(f) instanceof AudioBuffer)", 60000)
        assert g.js(SAID) == 5
    line = "hello over there, are you awake?"
    game.press("Enter", 200)
    game.page.keyboard.type(line)
    game.page.keyboard.press("Enter")
    game.wait(f"bubbles.some((b) => b.text === {line!r})", 5000)
    shown = game.js(f"(() => {{ const b = bubbles.find((b) => b.text === {line!r}); return written(b.text, performance.now() / 1000 - b.t).length; }})()")
    assert 0 < shown < len(line)                                    # being written, a letter every 45 ms
    game.sleep(1700)
    assert game.js(f"(() => {{ const b = bubbles.find((b) => b.text === {line!r}); return written(b.text, performance.now() / 1000 - b.t); }})()") == line
    for g in (game, friend):                                        # the one who speaks hears it too
        said = g.js("window.__said")
        when, rate = [s[0] for s in said], [s[2] for s in said]
        assert 11 <= len(said) <= 15, len(said)                     # 26 letters in six words: a syllable for every two, each word starting one
        gaps = [round(b - a, 3) for a, b in zip(when, when[1:])]
        assert min(gaps) >= .085 and max(gaps) <= .2 and all(.05 < s[1] < .16 for s in said), gaps    # in time, short, a breath between words
        assert len({round(r, 3) for r in rate}) >= 5 and rate[-1] > rate[0]      # not one note: the letters', and the question rises
    mine, theirs = game.js("voiceOf(me)"), friend.js("voiceOf(me)")
    assert -4 <= mine <= 4 and game.js(f"voiceOf({friend.name!r})") == theirs    # a voice from the name: the same on every screen
    game.js("(() => { muted = true; window.__said = []; return 1; })()")
    assert game.js("babble('x', 'not a sound when muted', undefined, undefined, false)") == 0 and game.js("window.__said") == []
