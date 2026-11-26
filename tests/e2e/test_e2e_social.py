"""Two people: chat, giving, mail; a spectator watching; boats."""

import pytest
from conftest import needs_sounds, open_game


@pytest.fixture
def friend(browser, server, game):
    """A second player standing two tiles east of the first."""
    g = open_game(browser, server)
    x, y = game.pos()
    g.rpc("dev_teleport", x=x + 2, y=y); g.arrive()
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
    game.wait(f"$('agents').innerText.includes('{friend.name}')", 5000)    # (the list of who is here is asked for every second and a half: waited for, not looked at once)
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
    game.press("e", 800)
    game.press("0", 100)
    game.press("e", 500)                                 # open the mailbox panel
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


def test_following_someone_by_their_link(browser, server, game):
    page = browser.new_page(viewport={"width": 1000, "height": 700})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{server}/?follow={game.name}")
    page.wait_for_function("typeof ready !== 'undefined'")
    page.wait_for_function("blocks.size > 0", timeout=8000)
    page.wait_for_timeout(1500)
    assert game.name in page.evaluate("$('agents').innerText")
    page.close()
    assert not errors


def test_boat_launch_sail_and_moor(game):
    game.stamp(1, -6, ["~~~~~~"] * 6)                        # a pond to the north-east (six rows of it: on a busy machine a key let go late took you three tiles, not two, and out on the far shore)
    game.give(boat=1)
    game.rpc("dev_teleport", x=game.pos()[0] + 1, y=game.pos()[1] - 0)
    game.sleep(800)
    game.hold_item("boat")
    game.face(0, -1)
    game.press("e", 800)
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
    """While you play the goals are not on the screen: early in the game a small tab says their key, G. G shows the
    card, top left, in the inventory's pixel (how many are done, the next three each a line with its small picture in
    a cell and a box; G puts it away again, H is the help); a goal done while it is away is said in the line of news. No title panel, no list of who
    is awake. Held, Tab shows one window in the top right corner (who.js), drawn as the recipe book is: the sun or the moon, the day and the
    hour, the day as a bar in the sky's colours with a mark at the hour, then a line for each one awake with their picture, their name and
    their level, you first and lit; at the foot where you are and how many are awake. It comes, whole, once Tab has been
    held a moment (a tap of Tab is the next thing in hand; the goals were on Tab for a day and slid in again at each press,
    which looked like lag) and goes when the key is let go.
    Someone only watching keeps the title and the list: they pick who to follow."""
    box = "(id) => { const r = $(id).getBoundingClientRect(); return r.width ? [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)] : null; }"
    assert game.js(box, "goals") is None and game.js("$('goalhint').textContent") == "Ggoals0/12" and game.js(box, "goalhint")[0] <= 14     # away; the tab, early in the game
    game.press("g", 200)                                                           # G: the card (and the tab goes)
    assert game.js(box, "goalhint") is None and game.js("localStorage.getItem('nexel-goals-off')") == "0"
    goals = game.js(box, "goals")
    assert goals and goals[0] <= 14 and goals[1] <= 14 and game.js(box, "brand") is None and game.js(box, "side") is None and game.js(box, "who") is None
    assert len(game.js("[...document.querySelectorAll('.goal')].map((g) => g.innerText)")) == 3 and game.js("$('goalhide').textContent + ' ' + $('goalhelp').textContent") == "Ghide Hhelp"
    look = game.js("(() => { const g = getComputedStyle($('goals')), q = parseFloat(g.getPropertyValue('--q')), r = $('goals').getBoundingClientRect(); return [g.backgroundColor, Math.round(r.width / q), $('goalcount').textContent, document.querySelectorAll('.goal .gc canvas').length, q, [...document.querySelectorAll('.goal .tick')].map((t) => Math.round(r.right - t.getBoundingClientRect().right))]; })()")
    assert look[0] == "rgb(232, 207, 166)" and look[1] == 106 and look[2] == "0/12" and look[3] == 3 and len(set(look[5])) == 1    # a card of paper, 106 of its px wide (it was 128, and 110 high: way too big); nothing done yet; each picture in its cell; the boxes in one column
    assert game.js("(() => { const r = $('goals').getBoundingClientRect(); return [r.width, r.height]; })()") == [318, 186]              # 318 by 186 on the screen (it was 384 by 330)
    assert game.js("[...document.querySelectorAll('.goal .gt')].every((t) => t.scrollWidth <= t.clientWidth) && $('goals').scrollWidth <= $('goals').clientWidth")   # no words cut
    assert look[4] == game.js("parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--q'))") == 3              # at the land's pixel, the recipe book's (at two thirds of it, it was too small and its px were not the game's)
    was = game.js("$('help').style.display")
    game.js("$('goalhelp').click()")                                               # the help, from the goals
    assert game.js("$('help').style.display") != was
    game.js("$('goalhelp').click()")
    game.press("h", 200)                                                           # H is the help
    assert game.js("$('help').style.display") == "block"
    game.press("h", 200)
    assert game.js("$('help').style.display") != "block" and game.js(box, "goals") == goals
    game.wait(f"agents.filter((a) => a.online).length >= 2 && agents.some((a) => a.name === {friend.name!r})", 10000)   # (the list is asked for now and then)
    game.page.keyboard.down("Tab")
    game.wait("document.body.classList.contains('tab')", 3000)       # (held: Tab is first the next thing in hand, the window comes after 350 ms of it held: keyboard.js tabDown, since 24dae98)
    shown = game.js("""() => new Promise((ok) => requestAnimationFrame(() => { const w = $('who'), r = w.getBoundingClientRect(), q = parseFloat(getComputedStyle(w).getPropertyValue('--q'));     // the frame after the key (its pixel: a size under the recipe book's)
      const ink = (c) => { const d = c.getContext('2d').getImageData(0, 0, 16, 16).data; let n = 0; for (let o = 3; o < d.length; o += 4) if (d[o]) n++; return n; };
      ok({top: r.top, right: r.right, wide: Math.round(r.width / q), px: [q, parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--q'))], moving: w.getAnimations({subtree: true}).length, day: $('whoday').textContent, hour: $('whohour').textContent,
        lines: [...w.querySelectorAll('.line')].map((l) => [l.querySelector('.n').textContent, l.classList.contains('cur'), !!l.querySelector('.tag'), l.querySelector('.lv').textContent, ink(l.querySelector('canvas'))]),
        sky: [$('whosky').dataset.night, ink($('whosky').querySelector('canvas'))], mark: parseFloat(getComputedStyle($('whomark')).left) / ($('whobar').offsetWidth - 4 * q), phase: clock.phase,
        foot: $('whofoot').innerText, whole: [...w.querySelectorAll('.line, .cell, #whobar')].every((e) => { const b = e.getBoundingClientRect(); return b.left >= r.left && b.right <= r.right && b.bottom <= r.bottom; })}); }))""")
    assert shown["top"] <= 16 and 8 <= game.js("innerWidth") - shown["right"] <= 16 and shown["wide"] == 150 and shown["px"] == [2, 3] and shown["moving"] == 0     # there, in the top right corner, 300 px wide (it was 450: too big), nothing sliding in
    assert shown["day"].startswith("Day ") and len(shown["hour"]) == 5 and shown["hour"][2] == ":"       # the day and the hour
    assert shown["sky"][0] == "0" and shown["sky"][1] > 40 and abs(shown["mark"] - shown["phase"]) < .02  # the sun; the mark where the hour is on the day's bar
    me, other = shown["lines"][0], [l for l in shown["lines"] if l[0] == friend.name][0]
    assert me[:4] == [game.name, True, True, "Lv 0"] and other[1:4] == [False, False, "Lv 0"]            # you first, lit and said to be you; then the others
    assert me[4] > 60 and other[4] > 60 and shown["whole"]                                                # each with their picture; all of it inside the window
    x, y = game.pos()
    assert shown["foot"].startswith(f"{x}, {y}") and "awake" in shown["foot"]
    assert game.js(box, "goals") == goals                                          # (the goals do not move for it)
    game.rpc("dev_time", phase=.86)                                                # night falls while it shows
    game.wait("$('whosky').dataset.night === '1' && Math.abs(parseFloat($('whomark').style.left.slice(5)) - clock.phase) < .02", 5000)
    game.page.keyboard.up("Tab")
    game.sleep(100)
    assert game.js(box, "who") is None
    game.give(wood=4)                                                              # a goal done: ticked where it is, no line of news for it
    game.sleep(600)
    assert "Goal done" not in game.toast() and game.js("document.querySelectorAll('.goal.done').length") == 1 and game.js("$('goalcount').textContent") == "1/12"
    game.press("g", 200)                                                           # away again: the tab is back, with how many are done
    assert game.js(box, "goals") is None and game.js("$('goalhint').textContent") == "Ggoals1/12" and game.js("localStorage.getItem('nexel-goals-off')") == "1"
    game.give(berries=1)                                                           # a goal done while the card is away: said in the line of news
    game.sleep(900)
    assert game.toast() == "Goal done: Pick berries"
    page = browser.new_page()                                                      # someone watching
    page.goto(f"{server}/?follow={game.name}")                                     # (by the link that follows someone: no menu)
    page.wait_for_function("typeof agents !== 'undefined' && agents.some((a) => a.online)", timeout=15000)
    assert page.evaluate("$('side').getBoundingClientRect().width") > 100 and page.evaluate("$('brand').innerText").startswith("NEXEL WORLDS")
    assert page.evaluate("$('who').getBoundingClientRect().width") == 0 and "help (H)" in page.evaluate("$('brand').innerText")
    page.close()


SAID = """() => { window.__said = []; const P = AudioBufferSourceNode.prototype, o = P.start, say = new Set(sounds.manifest.sounds.say.files.map((f) => sounds.buffers.get(f)));
  P.start = function (when, off, dur) { if (say.has(this.buffer)) window.__said.push([when, dur, this.playbackRate.value]); return o.apply(this, arguments); }; return say.size; }"""


@needs_sounds
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


@needs_sounds
def test_an_ai_player_talks_in_the_chip_voice_a_person_babbles(game, friend):
    """"The chip voice is very good": an AI player (persona not "human") says and shouts in the robot voice
    (robot_voice.js robotSay, kind "chip"); a person keeps the babble."""
    game.wait("sounds.manifest && sounds.manifest.sounds.say.files.every((f) => sounds.buffers.get(f) instanceof AudioBuffer)", 60000)
    game.js("""(() => { const ws = new WebSocket(`ws://${location.host}/agent`); window.rusty = ws;
      ws.onmessage = (m) => { const r = JSON.parse(m.data); (window.rustyDone = window.rustyDone || []).push(r.id); if (r.agent) window.rustyAt = [r.agent.x, r.agent.y]; };
      ws.onopen = () => ws.send(JSON.stringify({id: 1, op: "hello", name: "Rusty", token: "t", persona: "a quiet builder"})); })()""")
    game.wait("window.rustyAt", timeout=8000)
    x, y = game.js("rustyAt")
    game.rpc("dev_teleport", x=x + 1, y=y)
    friend.rpc("dev_teleport", x=x + 2, y=y)
    game.wait("[...ents.values()].some((q) => q.e && q.e.name === 'Rusty')", timeout=8000)
    game.press("ArrowLeft", 60)                                         # (a key: the page's sound is awake)
    game.js("""(() => { window.__talk = []; const b = babble, r = robotSay;
      babble = function (name, text, x, y, shout, robot) { const n = b.apply(this, arguments); window.__talk.push(["babble", name, !!robot, shout, n]); return n; };
      robotSay = function (a, d, bufs, name, text, shout, kind) { window.__talk.push(["robot", name, kind, shout]); return r.apply(this, arguments); };
      return 1; })()""")
    game.js("""rusty.send(JSON.stringify({id: 2, op: "act", tool: "say", args: {text: "hello there friend"}}))""")
    game.wait("rustyDone.includes(2)", 5000)                         # (one at a time: a new act replaces the one under way)
    game.js("""rusty.send(JSON.stringify({id: 3, op: "act", tool: "shout", args: {text: "GET AWAY FROM MY HOUSE"}}))""")
    friend.act("say", text="hello robot")
    game.wait("window.__talk.filter((t) => t[0] === 'babble').length >= 3", 8000)
    talk = game.js("window.__talk")
    rusty = [t for t in talk if t[1] == "Rusty"]
    assert [t[:4] for t in rusty] == [["robot", "Rusty", "chip", False], ["babble", "Rusty", True, False],     # said (robotSay inside babble)
                                      ["robot", "Rusty", "chip", True], ["babble", "Rusty", True, True]], talk   # and shouted
    assert all(t[-1] > 0 for t in rusty if t[0] == "babble"), talk                 # out loud: syllables on the clock
    pat = [t for t in talk if t[1] == friend.name]
    assert pat and all(t[0] == "babble" and t[2] is False for t in pat), talk     # a person: the babble only


@pytest.mark.animated                                  # (the goals' slide out and in: not with less motion, pages.py)
def test_a_goal_done_goes_out_and_only_the_new_one_comes_in(game):
    """"the item sliding animation on goals... looks buggy (low fps)": every row was made again at each change, so all
    three slid in again, in four jumps. The rows that stay are the same ones, only the new goal comes in, and nothing
    moves in steps."""
    game.press("g", 400)
    game.wait("document.querySelectorAll('.goal').length === 3")
    assert game.js("[...document.querySelectorAll('.goal')].every((r) => !r.classList.contains('in') && !r.getAnimations().length)")   # there at once
    game.js("(() => { document.querySelectorAll('.goal').forEach((r, k) => { r.kept = k; }); return 1; })()")
    game.give(berries=1)                                       # the third of the three
    game.wait("document.querySelector('.goal.done')", 5000)
    rows = game.js("[...document.querySelectorAll('.goal')].map((r) => [r.kept, r.classList.contains('done'), r.classList.contains('in')])")
    assert rows == [[0, False, False], [1, False, False], [2, True, False]], rows          # the same rows, each where it was
    assert "steps" not in game.js("getComputedStyle(document.querySelector('.goal.done')).animationTimingFunction")
    game.wait("!document.querySelector('.goal.done') && document.querySelectorAll('.goal').length === 3", 6000)
    rows = game.js("[...document.querySelectorAll('.goal')].map((r) => [r.kept ?? null, r.classList.contains('in')])")
    assert rows == [[0, False], [1, False], [None, True]], rows                             # two stayed; the new one came in
    assert "steps" not in game.js("getComputedStyle(document.querySelector('.goal.in')).animationTimingFunction")
