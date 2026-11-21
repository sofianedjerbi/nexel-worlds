"""What was a command is a box (ask.js): a sign is written as it goes up, an animal is named with a name tag.
"turn the command that could be turned into UI (signs, naming mobs) into ui. As example Signs = write when placing.
Naming mobs = naming tag required." """

ASKING = "$('ask').style.display === 'block' && document.activeElement === $('asktext')"


def test_a_sign_is_written_as_it_goes_up(game):
    game.give(sign=2)
    game.hold_item("sign")
    game.face(0, -1)
    game.press("e", 300)
    game.wait(ASKING)
    assert "sign say" in game.js("$('asktitle').textContent") and game.tile(0, -1) != "?"      # not up yet
    game.page.keyboard.type("wasd Fresh eggs")                 # (its letters are the box's: nobody walks)
    at = game.pos()
    game.page.keyboard.press("Enter")
    game.wait("$('ask').style.display === 'none'")
    game.sleep(900)
    assert game.tile(0, -1) == "?" and game.pos() == at and game.inv("sign") == 1
    game.hold_item(None)
    game.face(0, -1)
    game.press("e", 700)                                   # reading it
    assert "wasd Fresh eggs" in game.toast()
    game.hold_item("sign")                                     # Esc: no sign goes up
    game.face(1, 0)
    game.press("e", 300)
    game.wait(ASKING)
    game.page.keyboard.press("Escape")
    game.sleep(600)
    assert game.js("$('ask').style.display") == "none" and game.tile(1, 0) != "?" and game.inv("sign") == 1


def test_an_animal_is_named_with_a_name_tag(game):
    cow = game.spawn("cow", 1, 0, still=600)
    game.give(name_tag=1)
    game.hold_item("name_tag")
    game.face(1, 0)
    game.sleep(300)
    game.press("e", 300)
    game.wait(ASKING)
    assert game.js("$('asktitle').textContent") == "Name the cow"
    game.page.keyboard.type("Daisy")
    game.page.keyboard.press("Enter")
    game.wait("[...ents.values()].some((p) => p.e && p.e.kind === 'cow' && p.e.name === 'Daisy')", 6000)
    game.sleep(900)
    assert game.inv("name_tag") == 0 and cow                   # the tag stays on her
    lines = game.js("[...$('chatlog').children].map((d) => d.textContent)")
    assert any("Its name is Daisy" in ln for ln in lines), lines
