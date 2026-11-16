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
    assert "Pick a piece" in side[4] and "Dig a hole" in side[4] and abs(side[0] - (r["x"] + r["w"] + 10)) < 2   # at its right
    assert up[4].replace(" ", "") == "EUp" and down[4].replace(" ", "") == "QDown"     # at its left, E over Q
    assert up[1] < r["x"] and down[1] < r["x"] and up[3] < r["y"] + r["h"] / 2 < down[2]
    assert game.js("$('actions').textContent") == "BBUILD MODE · leave"                  # the corner: only the mode (B to leave)
    game.press("ArrowRight", 150)                              # it goes with the cursor
    assert abs(game.js(PART, "side")[0] - game.js("Build.S.rect.x + Build.S.rect.w + 10")) < 2
    game.press("b")
    game.sleep(200)
    assert game.js("$('prompts').innerText").strip() == "" and not game.errors


def test_what_you_face_has_its_key_beside_it(game):
    game.clear_area(8)
    game.stamp(1, 0, ["T"])                                    # a tree east of you
    game.press("ArrowRight", 400)
    game.wait("$('prompts').innerText.includes('Chop tree')", 3000)
    side = game.js(PART, "side")
    assert side[4].startswith("Space") and "Chop tree" not in game.js("$('actions').innerText")
    assert not game.errors
