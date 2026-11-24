"""The curved world (web/js/curve.js; hd.js viewOf): the ground bends away to the horizon the view distance puts, with
a sky over it. A setting, on or off: off, the HD look's land is flat, drawn to the picture's top, no sky."""


def test_curved_world_is_a_setting_on_the_picture_page_on_unless_chosen_otherwise(game):
    """The settings' "Curved world", On by default, and what it says is what is drawn: on, the land bends (the bend
    viewOf works out for the view distance) to a horizon with the sky over it; off, no bend, no sky, and the land
    reaches the picture's top: no px of it without land. (Its Near and Far moved the sky's line; the land stayed bent.)"""
    assert game.js("OPT_DEFAULT.curve") is True and game.js("opt('curve')") is True
    assert game.js("MENU_PAGES.find((p) => p[0] === 'Picture')[1].find((r) => r.name === 'Curved world').kind") == "toggle"
    game.js("(() => { Curve.force = null; return 1; })()")       # (the setting decides, not the page's address)
    game.wait("Curve.on && HdLook.bend > 0")
    game.js("setOpt('curve', false)")
    game.wait("!Curve.on && HdLook.bend === 0 && HdLook.view.b === 0")
    game.rest()
    assert game.js("HdLook.bare()") == 0                         # the land to the picture's top
    game.js("setOpt('curve', true)")
    game.wait("Curve.on && HdLook.bend > 0")
