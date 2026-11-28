"""Admins (admin.py, js/commands.js): the server's commands typed in the chat line, refused to a player, done for an
admin; their names and words finished with Tab; a crown by an admin's name in the list Tab shows."""

import os

LAST = "[...$('chatlog').children].map((d) => d.textContent)"
ROWS = "[...$('sayhelp').children].map((d) => (d.querySelector('b') || d).textContent)"


def said(game, text):
    game.wait(f"[...$('chatlog').children].some((d) => d.textContent.includes({text!r}))")


def test_tp_is_refused_to_a_player_and_done_for_an_admin_and_the_crown_shows(game):
    page = game.page
    x0, y0 = game.server()["x"], game.server()["y"]
    page.keyboard.press("/")
    page.keyboard.type("tp 0 0")
    page.keyboard.press("Enter")
    said(game, "You can't do that")
    s = game.server()
    assert (s["x"], s["y"]) == (x0, y0)                                   # (not moved)
    assert game.rpc("dev_admin")["admin"] is True
    page.keyboard.press("/")
    game.wait("!!serverCmds && serverCmds.admin")                         # (asked again as the line opens: an admin now)
    page.keyboard.type("su")
    assert game.js(ROWS)[0] == "summon"
    page.keyboard.press("Tab")
    assert game.js("$('say').value") == "/summon " and "cow" in game.js(ROWS)    # (its words: the creatures)
    game.wait(f"agents.some((a) => a.name === {game.name!r})", 3000)   # (the players' list, asked every 1.5 s of the page's time (state.js): the page was there before you joined)
    page.fill("#say", "/give ")
    page.keyboard.type(game.name[:4])
    assert game.name in game.js(ROWS)                                     # (a player's name)
    page.fill("#say", "/tp 0 0")
    page.keyboard.press("Enter")
    said(game, "Teleported to 0, 0")
    s = game.server()
    assert (s["x"], s["y"]) == (0, 0)
    page.keyboard.down("Tab")
    game.wait("!!document.querySelector('#wholist .line.cur canvas.crown')", 8000)     # (the list is asked again every 1.5 s)
    if os.environ.get("E2E_SHOTS"):
        page.locator("#who").screenshot(path=os.environ["E2E_SHOTS"] + "/admin_crown.png")
    page.keyboard.up("Tab")
