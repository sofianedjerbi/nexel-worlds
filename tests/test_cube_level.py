"""A level is a CUBE ("1 block = player": the owner's choice): drawn 16 art px high, as tall as a tile is wide and as
the cat is. The game's px a level (relief.js RELIEF_STEP), the engine's height of a level in tiles (vox_style_glsl.js
H) and its rows of side paint (LV) say the same; the engine's files take H from one place, never a number of their own
(a level drawn 8 px on a 16 px tile read as a slab: "no half block confusion anymore")."""

import re
from pathlib import Path

JS = Path(__file__).parent.parent / "src" / "megastructure" / "web" / "js"


def test_a_level_is_drawn_as_tall_as_a_tile_everywhere():
    step = int(re.search(r"^const RELIEF_STEP = (\d+);", (JS / "relief.js").read_text(), re.M).group(1))
    glsl = (JS / "vox_style_glsl.js").read_text()
    h, lv = re.search(r"const AW = [^,]*\? 2048 : 1024, H = ([\d.]+), LV = (\d+),", glsl).groups()   # (AW: the sheet's px, by the screen's size)
    assert step == 16 and float(h) * 16 == step and int(lv) == step
    for f in ("vox_style.js", "vox_style_land.js", "vox_style_win.js"):
        assert re.search(r"const H = VoxStyleGLSL\.H\b", (JS / f).read_text()), f          # (one H, not a .5 of its own)
    assert "8. + whole(" not in glsl and "/ .5" not in glsl                                 # (no 8-row level left in the shader)


def test_a_wall_a_fence_a_door_are_a_block_high():
    things = (JS / "hd_things.js").read_text()
    assert "12 / KF()" not in things and "16 / KF()" not in things                           # (they were their art's 12 rows, at any pitch)
    assert "const full = over ? (over - 1 - zl) * UP : UP;" in things
