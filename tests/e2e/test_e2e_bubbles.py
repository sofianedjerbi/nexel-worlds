"""Speech bubbles in Chrome: drawn in pixels, wrapped, piled oldest lowest, and coming down when one goes."""

import pytest
import os

from conftest import needs_sounds

SHOT = os.environ.get("BUBBLE_SHOTS")        # a folder to keep a picture of each scene in

SAY = "(text, ago = 0, shout = false) => bubbles.push({name: me, text, t: performance.now() / 1000 - ago, shout})"
MINE = "bubbles.filter((b) => b.name === me && b.at).map((b) => ({text: b.text, x: b.at[0], y: b.at[1], w: b.w, h: b.h, rows: b.rows}))"


def shot(game, name):
    if SHOT:
        v = game.page.viewport_size
        game.page.screenshot(path=f"{SHOT}/{name}.png", clip={"x": v["width"] / 2 - 230, "y": v["height"] / 2 - 330, "width": 460, "height": 400})


def test_bubbles_are_pixels_pile_up_and_come_down(game):
    game.clear_area(6)
    game.js(f"({SAY})('hi!', 3)")
    game.sleep(300)
    one = game.js(MINE)[0]
    edge = game.js(f"""(() => {{ const d = (x, y) => [...ctx.getImageData(x, y, 1, 1).data].slice(0, 3).join(), x = {one['x']}, y = {one['y']}, w = {one['w']}, h = {one['h']};
      const top = new Set(); for (let i = 2; i < w - 2; i++) top.add(d(x + i, y)); for (let i = 2; i < w - 2; i++) top.add(d(x + i, y + 1));
      return {{top: [...top], corner: d(x, y), in1: d(x + 4, y + 2), side: d(x, y + 2), foot: d(x + 4, y + h - 3), over: d(x + w / 2, y + h - 3), tail: d(x + w / 2, y + h + 1)}}; }})()""")
    assert edge["top"] == ["91,63,54"] and edge["side"] == "91,63,54", edge       # a hard dark edge, two px thick: no smoothing
    assert edge["corner"] != "91,63,54" and edge["in1"] == "255,246,226" and edge["foot"] == "236,215,176", edge   # the corner stepped off; paper; the foot's shade
    # (the paper runs down into the tail: the foot's shade ran across over it, a line between the bubble and its tail)
    assert edge["over"] == "255,246,226" and edge["tail"] == "255,246,226", edge
    # the letters in the middle of the paper: as far under its top edge as over the foot's shade (they were 2 px and 6)
    rows = game.js(f"""(() => {{ const x = {one['x']}, y = {one['y']}, w = {one['w']}, h = {one['h']}, d = ctx.getImageData(x + 6, y + 2, w - 12, h - 6).data, rows = [];
      for (let j = 0; j < h - 6; j++) for (let i = 0; i < w - 12; i++) if (d[(j * (w - 12) + i) * 4] === 91 && d[(j * (w - 12) + i) * 4 + 1] === 63) {{ rows.push(j); break; }}
      return [rows[0], h - 6 - 1 - rows[rows.length - 1]]; }})()""")
    assert rows == [4, 4], rows
    shot(game, "one")
    long = "I found a cave full of iron past the river, bring a pickaxe and some torches when you come"
    game.js(f"({SAY})({long!r}, 4); ({SAY})('ok, coming', 4, true)")
    game.sleep(400)
    a, b, c = game.js(MINE)
    assert [a["text"], c["text"]] == ["hi!", "ok, coming"]
    assert 2 <= len(b["rows"]) <= 7 and " ".join(b["rows"]) == long and b["w"] <= 400 + 16, b   # wrapped whole, no wider than a bubble
    assert a["y"] > b["y"] + b["h"] and b["y"] > c["y"] + c["h"]                 # the oldest lowest, then the next, none on another
    assert a["y"] - (b["y"] + b["h"]) == 2 and b["y"] - (c["y"] + c["h"]) == 2   # one gap between them
    shot(game, "three")
    game.js(f"({SAY})('wait for me', 4)")                                        # a fourth: the oldest goes at once
    game.sleep(500)
    now = game.js(MINE)
    assert [m["text"] for m in now] == [long, "ok, coming", "wait for me"]
    assert now[0]["y"] + now[0]["h"] == a["y"] + a["h"], (now[0], a)             # and the pile has come down onto its place
    assert now[1]["y"] + now[1]["h"] == now[0]["y"] - 2
    shot(game, "after_one_went")
    game.js("bubbles.length = 0")
    game.js(f"({SAY})({'a' * 200!r}, 11)")                                       # one endless word: broken into rows
    game.sleep(300)
    rows = game.js(MINE)[0]["rows"]
    assert len(rows) == 7 and "".join(rows) == "a" * 200, rows                  # all of the longest line a chat takes, nothing cut
    shot(game, "endless")
    assert not game.errors


# the names written in the next frame, and where: [[name, x, y]...]
NAMES = """() => new Promise((ok) => { const f = outlined, got = []; outlined = (text, x, y, c) => { got.push([text, x, y]); return f(text, x, y, c); };
  requestAnimationFrame(() => requestAnimationFrame(() => { outlined = f; ok(got); })); })"""


def test_a_name_under_someone_s_bubble_is_not_written_a_few_letters_past_its_edge(game, browser, server):
    """The first screen: Tobi's bubble over Nell's name, "Tobi ell", the end of her name past its tab. A name under
    another's bubble is not written (it is again when the bubble goes)."""
    from conftest import open_game
    game.clear_area(6)
    other = open_game(browser, server)
    x, y = game.pos()
    other.rpc("dev_teleport", x=x, y=y - 1)
    name = other.name
    game.wait(f"[...ents.values()].some((p) => p.e && p.e.name === {name!r} && p.x === {x} && p.y === {y - 1})", 8000)
    game.rest()
    seen = [n for n in game.js(NAMES) if n[0] == name]
    assert seen, game.js(NAMES)                                                   # written, nobody speaking
    _, nx, ny = seen[0]
    game.js(f"({SAY})('I found a cave full of iron past the river, bring a pickaxe and some torches', 4)")
    game.wait("bubbles.some((b) => b.at)")
    b = game.js(MINE)[0]
    w = len(name) * 6
    assert nx - w < b["x"] + b["w"] and nx + w > b["x"] and ny - 18 < b["y"] + b["h"] and ny + 6 > b["y"], (b, nx, ny)   # (it is under the bubble)
    assert not [n for n in game.js(NAMES) if n[0] == name]
    game.js("bubbles.length = 0")
    game.frames(2)
    assert [n for n in game.js(NAMES) if n[0] == name]                            # the bubble gone: written again
    assert not game.errors and not other.errors


@needs_sounds
@pytest.mark.realtime
def test_what_is_typed_in_capitals_is_shouted(game):
    """A shout needed "!" before it. Now a line in capitals is one (three letters or more: "OK" is talk), and it is a
    yell: each syllable held longer and falling, through a breaking curve and an echo (babble.js SHOUT).
    (The line was "come here": its syllables c, m, h, r all take the shortest recording (say_4, 0.21 s), and a shout is
    held only as long as the recording lasts at its pitch: a name whose voice is high (voiceOf, +4) held it 0.096 s, not
    over 0.1, one run in a few. "papa kafka" takes say_2 (0.43 s) at every syllable: held 0.15 s in any voice.)"""
    assert game.js("['HELLO THERE', 'WAIT!!', 'Hello', 'OK', 'I', '123', 'ÉCOUTE'].map(shouted)") == [True, True, False, False, False, False, True]
    game.wait("sounds.manifest && sounds.manifest.sounds.say.files.every((f) => sounds.buffers.get(f) instanceof AudioBuffer)", 60000)
    game.js("""(() => { window.__said = []; window.__shaped = 0; const P = AudioBufferSourceNode.prototype, o = P.start;
      P.start = function (when, off, dur) { window.__said.push(dur / this.playbackRate.value); return o.apply(this, arguments); };
      const c = BaseAudioContext.prototype.createWaveShaper; BaseAudioContext.prototype.createWaveShaper = function () { window.__shaped++; return c.call(this); }; })()""")
    for line, shout in (("papa kafka", False), ("PAPA KAFKA", True)):
        game.js("window.__said = []")
        game.press("Enter", 200)
        game.page.keyboard.type(line)
        game.page.keyboard.press("Enter")
        game.wait(f"bubbles.some((b) => b.text === {line!r})", 5000)
        assert game.js(f"bubbles.find((b) => b.text === {line!r}).shout") is shout
        game.sleep(300)
        said = game.js("window.__said")
        assert len(said) >= 3 and (max(said) > .1) is shout, said               # a shout's syllables are held longer (as long as the recording lasts)
    assert game.js("window.__shaped") == 1                                      # only the shout went through the breaking curve
    assert not game.errors


def test_two_people_on_one_row_at_two_heights_each_has_its_name_over_its_own_head(game, browser, server):
    """The audit's prediction: the HD look found a body's place on the screen by its row alone (hd.js written, who):
    two people on the same row, one on a pillar three levels up, had their names at the same height, the first one's.
    Each name is over its own body: the one on the pillar some 100 px higher on the screen. Either of the two up."""
    from conftest import open_game
    game.clear_area(8)
    other = open_game(browser, server)
    x, y = game.pos()
    game.stamp(2, 0, ["."], levels=["3"])
    other.rpc("dev_teleport", x=x + 2, y=y, z=3)
    for up, low, ux in ((other, game, x + 2), (game, other, x)):
        game.wait(f"[...ents.values()].some((p) => p.e && p.e.name === {other.name!r} && p.x === {x + 2 if up is other else x - 2} && p.y === {y})", 8000)
        game.rest()
        names = {n[0]: n[2] for n in game.js(NAMES)}
        assert up.name in names and low.name in names, names
        assert names[up.name] < names[low.name] - 60, (up.name, names)
        if up is other:                                                          # (and the other way round: you on a pillar, they on the meadow)
            game.stamp(0, 0, ["."], levels=["3"])
            game.rpc("dev_teleport", x=x, y=y, z=3); game.arrive()
            other.rpc("dev_teleport", x=x - 2, y=y, z=0)
    assert not game.errors and not other.errors


# your name as it is written, frame by frame through a jump (Space): [its y, your body's place's y (View.of), BodyPlace's lift]
JUMPED = """() => new Promise((ok) => { const f = outlined, got = []; let n = 0;
  outlined = (text, x, y, c) => { if (text === me) { const p = ents.get('agent' + myId), v = View.of(p); got.push([y, v && v[1], BodyPlace.of(p).up]); } return f(text, x, y, c); };
  const key = (type) => dispatchEvent(new KeyboardEvent(type, {key: ' ', code: 'Space', bubbles: true, cancelable: true}));
  const tick = () => { n++; if (n === 4) key('keydown'); if (n === 6) key('keyup'); if (n > 50) { outlined = f; ok(got); } else requestAnimationFrame(tick); };
  requestAnimationFrame(tick); })"""


def test_at_a_screen_density_of_one_and_a_quarter_your_name_is_over_your_own_head(browser, server):
    """A laptop at 125 %: an art px of the land is 3.2 CSS px at zoom 3 (state.js artPx), not 3. Your name is written
    over the middle of your body, on the land's pixel, as far over your head as on a plain screen (what is written over
    a body is put from the body's own place, view.js View.of; its offsets were counted in zoom px, 16 x 3 a tile where
    the picture's tile is 16 x 3.2)."""
    from conftest import Game, new_name
    got = {}
    for dsf in (1, 1.25):
        ctx = browser.new_context(viewport={"width": 960, "height": 540}, device_scale_factor=dsf)
        try:
            g = Game(ctx.new_page(), server)
            g.join(new_name("dn"), 3)
            g.rpc("dev_creatures", clear=40)
            g.clear_area(8)
            g.rest()
            u, body, foot = g.js("artPx()"), g.js("HdLook.art().body"), g.js("View.of(ents.get('agent' + myId))")
            name = [n for n in g.js(NAMES) if n[0] == g.name]
            assert name and body, (dsf, name, body)
            _, nx, ny = name[0]
            got[dsf] = (u, nx - (body["x"] + body["w"] / 2), foot[1] - ny, nx / u)
            # and in a jump: the name goes up with the body, by its lift in the land's pixel (it was zoom px: at 125 % a px
            # an art px short of it, 3 at a jump's top)
            jump = [r for r in g.js(JUMPED) if r[1] is not None]
            stand = [foot - y for y, foot, up in jump if up == 0]
            assert stand and max(r[2] for r in jump) >= 12, (dsf, jump)
            assert all(abs((foot - y - stand[0]) / u - up) < .6 for y, foot, up in jump), (dsf, stand[0], u, jump)
            assert not g.errors
        finally:
            ctx.close()
    assert abs(got[1][0] - 3) < 1e-6 and abs(got[1.25][0] - 3.2) < 1e-6, got
    for dsf, (u, off, gap, cell) in got.items():
        assert abs(off) <= u + .01, (dsf, got)                                # over the middle of your body, an art px at the most
        assert abs(cell - round(cell)) < .02, (dsf, got)                      # on the land's pixel
    # as far over your feet on both screens, in the land's own pixel: 20 art px (half a tile, where a body stands in it, its head) and the letters' own
    # few px: 4 CSS px further at 3.2 px a pixel than at 3. (It was the same CSS px on both, counted in zoom: the name 4 px into the head at 125 %)
    assert 2.4 <= got[1.25][2] - got[1][2] <= 5.6, got
