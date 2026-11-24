"""The game's art that is not in this repository: the sheets of the premium "Sprout Lands" packs by Cup Nooble
(https://cupnooble.itch.io/), and the tiles made from them. Their license lets a game use them but forbids
redistributing the packs, even modified, so each player installs them from their own copy:

    python tools/install_assets.py "Sprout Lands - Sprites - premium pack.zip" "Sprout Lands - UI Pack - Premium pack.zip"

They go into web/assets/ beside the game's own pictures (enemy sheets, title pictures, the font), and are git-ignored
there (.gitignore, from this list)."""

from pathlib import Path

ASSETS = Path(__file__).parent / "web" / "assets"

# copied from the packs as they are (tools/build_assets.py COPY)
PACK = [
    "water.png", "soil.png", "grass.png", "tilled.png", "stone.png", "hedge.png", "hill1.png", "hill2.png", "hill3.png",
    "cobble.png", "planks.png", "fences.png", "gates.png", "bridge.png", "furniture.png", "house_walls.png",
    "house_roof.png", "chest.png", "door.png", "trees.png", "nature.png", "workbench.png", "signs.png", "crops.png",
    "items.png", "character.png", "tree_anim.png", "tree_apple.png", "tree_pear.png", "tree_peach.png",
    "tree_orange.png", "water_objects.png", "boats.png", "mailbox.png", "emoji.png", "well.png", "blanket.png",
    "basket.png", "barn.png", "coop.png", "tree_fall.png", "chicken.png", "cow.png", "chicken_brown.png",
    "chicken_red.png", "chicken_blue.png", "chicken_green.png", "cow_light.png", "cow_pink.png", "cow_purple.png",
    "cow_green.png", "chick.png", "chick_brown.png", "chick_red.png", "chick_blue.png", "chick_green.png", "calf.png",
    "calf_light.png", "calf_pink.png", "calf_purple.png", "calf_green.png", "ui.png", "hearts.png", "sliders.png",
]
# made from the packs' sheets by tools/build_assets.py (recoloured, cut out, cropped; gen.png is drawn in the
# packs' palette by tools/pixel_art.py and is made there too)
DERIVED = [
    "ash.png", "water_deep.png", "tilled_wet.png", "deep_mask.png", "cursor.png", "cursor_point.png", "panel.png",
    "slot.png", "slot_sel.png", "fruit_bare.png", "thin_fall.png", "stump_thin.png", "gen.png", "boot_cat.png",
]
FILES = PACK + DERIVED


def missing(assets: Path = ASSETS) -> list[str]:
    """The pack's files not installed in `assets`."""
    return [n for n in FILES if not (assets / n).is_file()]


def installed(assets: Path = ASSETS) -> bool:
    return not missing(assets)


HOW = ("the Sprout Lands art is not installed (it is not in this repository: its license forbids redistributing it). "
       "Buy the Sprites and UI premium packs at https://cupnooble.itch.io/ and run "
       "`python tools/install_assets.py <the two zips>` (README.md, 'Art').")
