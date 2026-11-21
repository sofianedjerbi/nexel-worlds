"""The curved world (web/js/curve.js, vox_curve.js): the ground bends away to a horizon in the upper part of the screen,
with a sky over it; the HD look draws its sky there (hd.js sky). A setting: Off, Near, Far."""


def test_curved_world_is_a_setting_on_the_picture_page_far_unless_chosen_otherwise(game):
    """The settings' "Curved world": Off, Near or Far on the Picture page, Far by default, and what it says is what
    is drawn: Far shows more land before the horizon than Near, Off none of the bend."""
    assert game.js("OPT_DEFAULT.curve") == "far" and game.js("opt('curve')") == "far"
    assert game.js("MENU_PAGES.find((p) => p[0] === 'Picture')[1].find((r) => r.name === 'Curved world').list.map((q) => q[0])") == ["off", "near", "far"]
    game.js("(() => { Curve.force = null; return 1; })()")       # (the setting decides, not the page's address)
    game.wait("Curve.on")
    far = game.js("[Curve.c.yh, VoxCurve.edge(Curve.c)]")
    game.js("setOpt('curve', 'near')")
    game.wait(f"Curve.on && Curve.c.yh > {far[0]} + 20")         # Near: the horizon lower down the screen
    assert game.js("VoxCurve.edge(Curve.c)") > far[1] + 60       # ...and less ground before it (px of the flat picture)
    game.js("setOpt('curve', 'off')")
    game.wait("!Curve.on")
    game.js("setOpt('curve', 'far')")
    game.wait("Curve.on")
