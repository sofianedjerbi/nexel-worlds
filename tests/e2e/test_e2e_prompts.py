"""The keys beside what they act on (web/js/prompts.js). "the keys appear in the chat, as a guide in each mode. can't
you make it more intuitive ??": each mode said its keys in the chat, and the rest were a list in the far corner."""

PART = "(k) => { const r = document.querySelector('#prompts .' + k).getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom, document.querySelector('#prompts .' + k).innerText.trim()]; }"


def test_build_mode_says_its_keys_by_the_cursor_and_nothing_in_the_chat(game):
    game.clear_area(8)
    game.give(pickaxe=1)
    chat = game.js("$('chatlog').children.length")
    game.press("ArrowDown", 200)
    game.press("b")
    game.sleep(200)
    assert game.js("$('chatlog').children.length") == chat     # (it said its keys there each time)
    r = game.js("Build.S.rect")
    side, up, down = (game.js(PART, k) for k in ("side", "up", "down"))
    assert "Pick a piece" in side[4] and "Break" in side[4] and abs(side[0] - (r["x"] + r["w"] + 10)) < 2   # at its right
    assert up[4].replace(" ", "") == "EUp" and down[4].replace(" ", "") == "QDown"     # at its left, E over Q
    assert up[1] < r["x"] and down[1] < r["x"] and up[3] < r["y"] + r["h"] / 2 < down[2]
    assert game.js("$('actions').textContent") == "ZBUILD MODE · leave"                  # the corner: only the mode (Z to leave: under A, the hand stays on WASD)
    game.press("ArrowRight", 150)                              # it goes with the cursor; east of you: its keys under it and at its right, none over you
    r = game.js("Build.S.rect"); side, up = game.js(PART, "side"), game.js(PART, "up")
    assert r["under"] and r["right"] and side[2] >= r["y"] + r["h"] and up[0] >= r["x"] + r["w"]
    game.press("b")
    game.sleep(200)
    assert game.js("$('prompts').innerText").strip() == "" and not game.errors


def test_what_you_face_has_its_key_beside_it(game):
    game.clear_area(8)
    game.stamp(1, 0, ["T"])                                    # a tree east of you
    game.press("ArrowRight", 400)
    game.wait("$('prompts').innerText.includes('Chop tree')", 3000)
    side = game.js(PART, "side")
    assert side[4].startswith(game.js("capOf('alt')")) and "Chop tree" not in game.js("$('actions').innerText")
    assert not game.errors


def test_no_row_is_written_on_you_or_on_another_row(game):
    """Facing west the rows lay across your face; under the build cursor Q's row lay on Space's."""
    hit = """(() => { const k = Prompts.keep, r = (c) => { const e = document.querySelector('#prompts .' + c); if (!e || !e.innerText.trim()) return null; const b = e.getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; },
      on = (a, b) => Array.isArray(b) ? b.some((c) => on(a, c)) : !!a && !!b && a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h, s = r('side'), u = r('up'), d = r('down');
      return [!!s, !!k, on(s, k), on(u, k), on(d, k), on(s, u), on(s, d)]; })()"""
    game.clear_area(8)
    game.stamp(-1, 0, ["T"])                                   # a tree west of you
    game.press("ArrowLeft", 400)
    game.wait("$('prompts').innerText.includes('Chop tree')", 3000)
    for d in (0, 1, 1, -1, -1, -1, -1):                          # as it is, then to both ends of the zoom
        game.js(f"(() => {{ if ({d}) zoomBy({d}); return 1; }})()")
        game.wait("!ZOOM.busy && zoom === ZOOM.to")                 # (the zoom glides there: the rows laid out at it once it is there,
        game.rest()                                                # not 500 ms on, a busy runner still mid-glide: the side row on you)
        assert game.js(hit) == [True, True, False, False, False, False, False], (d, game.js("zoom"), game.js(hit))
    game.give(wood_wall=4)
    game.hold_item("wood_wall")
    game.press("b"); game.sleep(200)
    for key in ("ArrowRight", "ArrowRight", "ArrowLeft", "ArrowLeft", "ArrowLeft", "ArrowLeft", "ArrowDown"):
        game.press(key, 150)
        game.settle(f"{hit}.slice(2).every((v) => !v)")              # (the view pans half way to the cursor: once it is there)
        assert game.js(hit)[2:] == [False] * 5, (key, game.js(hit), game.js("[Prompts.keep, Build.S.rect, Build.S.at, myPos(), ...['side', 'up', 'down'].map((c) => document.querySelector('#prompts .' + c).style.transform)]"))
    game.press("b")
    assert not game.errors


def test_only_what_your_hand_gets_to_is_offered(game):
    """A flower six layers up a pillar, one six layers down a pit, a tusker six layers up: no row, nothing in red,
    and Space says nothing. A flower three layers up is picked (the server takes it). A pickaxe at a hill's foot
    digs into the hill; on open meadow X digs down, said in the corner (nothing is faced to say it beside)."""
    game.clear_area(8)
    x, y = game.pos()
    game.press("ArrowDown", 300)
    for dx, dy, lv, said in ((-1, 0, "6", "Dig into the hill"), (0, 1, "f", "")):
        game.stamp(dx, dy, ["f"], levels=[lv])
        game.face(dx, dy)
        game.sleep(400)
        assert game.actions() == (said and game.js("capOf('alt')") + said), (lv, game.actions())      # (X digs the block you face: the pillar's at your feet; nothing of a floor six down, nor of the flower)
        game.js("$('toast').style.display = 'none'")
        game.press("e", 300)
        assert game.toast() == "" and game.inv("flower") == 0
        game.stamp(dx, dy, ["."], levels=["0"])
    game.stamp(1, 0, ["f"], levels=["3"])
    game.face(1, 0)
    game.wait("$('prompts').innerText.includes('Pick flower')", 3000)
    game.press("e", 100)
    game.wait("(meObs.self.inventory.flower || 0) === 1", 4000)
    game.give(pickaxe=1)
    game.hold_item("pickaxe")
    game.wait("$('prompts').innerText.includes('Dig into the hill')", 3000)
    game.face(-1, 0)
    game.wait("$('prompts').innerText.trim() === '' && $('actions').innerText.includes('Dig down')", 3000)
    game.js("selectItem(null)")
    game.stamp(-1, 0, ["."], levels=["6"])
    game.spawn("tusker", -1, 0, still=600)
    game.wait("[...ents.values()].some((q) => q.e && q.e.kind === 'tusker')", 4000)
    game.sleep(400)
    assert "tusker" not in game.actions() and not game.errors
