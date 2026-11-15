"""Speech bubbles in Chrome: drawn in pixels, wrapped, piled oldest lowest, and coming down when one goes."""

import os

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


def test_what_is_typed_in_capitals_is_shouted(game):
    """A shout needed "!" before it. Now a line in capitals is one (three letters or more: "OK" is talk), and it is a
    yell: each syllable held longer and falling, through a breaking curve and an echo (babble.js SHOUT)."""
    assert game.js("['HELLO THERE', 'WAIT!!', 'Hello', 'OK', 'I', '123', 'ÉCOUTE'].map(shouted)") == [True, True, False, False, False, False, True]
    game.wait("sounds.manifest && sounds.manifest.sounds.say.files.every((f) => sounds.buffers.get(f) instanceof AudioBuffer)", 60000)
    game.js("""(() => { window.__said = []; window.__shaped = 0; const P = AudioBufferSourceNode.prototype, o = P.start;
      P.start = function (when, off, dur) { window.__said.push(dur / this.playbackRate.value); return o.apply(this, arguments); };
      const c = BaseAudioContext.prototype.createWaveShaper; BaseAudioContext.prototype.createWaveShaper = function () { window.__shaped++; return c.call(this); }; })()""")
    for line, shout in (("come here", False), ("COME HERE", True)):
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
