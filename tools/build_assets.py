"""Build the web client's art from the Sprout Lands packs (by Cup Nooble) plus generated extras.

    uv run --with pillow python tools/build_assets.py ~/Downloads

Only the sheets the game uses are copied into src/megastructure/web/assets/ (the license forbids
redistributing the pack itself). Extra tiles in the same palette are generated here.
"""

import io
import sys
import zipfile
from pathlib import Path

from derived_art import largest_shape, ramp_art, thin_fall_sheet, thin_stump
from PIL import Image
from pixel_art import GEN, P, art

OUT = Path(__file__).resolve().parent.parent / "src" / "megastructure" / "web" / "assets"
SPRITES = "Sprout Lands - Sprites - premium pack.zip"
UI = "Sprout Lands - UI Pack - Premium pack.zip"

COPY = {  # zip-internal path suffix -> output name
    "Tilesets/ground tiles/Water.png": "water.png",
    "Tilesets/ground tiles/New tiles/Soil_Ground_Tiles.png": "soil.png",
    "Tilesets/ground tiles/New tiles/Grass_Tile_Layers.png": "grass.png",
    "Tilesets/ground tiles/Old tiles/Tilled_Dirt_v2.png": "tilled.png",
    "Tilesets/ground tiles/New tiles/Stone_Ground_Tiles.png": "stone.png",
    "Tilesets/ground tiles/New tiles/Bush_Tiles.png": "hedge.png",
    "Tilesets/ground tiles/New tiles/Grass_Hill_Tiles_v2.png": "hill1.png",          # relief: one sheet a level
    "Tilesets/ground tiles/New tiles/Darker_Grass_Hills_Tiles_v2.png": "hill2.png",
    "Tilesets/ground tiles/New tiles/Stone_Ground_Hills_Tiles.png": "hill3.png",
    "Tilesets/Building parts/Stone_Path.png": "cobble.png",
    "Tilesets/Building parts/Paths.png": "planks.png",
    "Tilesets/Building parts/Fences.png": "fences.png",
    "Tilesets/Building parts/Fence gates animation sprites .png": "gates.png",
    "Tilesets/Building parts/Wooden_Bridge_v2.png": "bridge.png",
    "Tilesets/Building parts/Basic_Furniture.png": "furniture.png",
    "Tilesets/Building parts/Wooden_House_Walls_Tilset.png": "house_walls.png",
    "Tilesets/Building parts/Wooden_House_Roof_Tilset.png": "house_roof.png",
    "Tilesets/Building parts/Chest.png": "chest.png",
    "Tilesets/Building parts/door animation sprites.png": "door.png",
    "Objects/Trees, stumps and bushes.png": "trees.png",
    "Objects/Mushrooms, Flowers, Stones.png": "nature.png",
    "Objects/work station.png": "workbench.png",
    "Objects/signs.png": "signs.png",
    "Objects/Farming Plants.png": "crops.png",
    "Objects/Items/All items.png": "items.png",
    "Characters/Premium Charakter Spritesheet.png": "character.png",
    "Objects/Tree animations/tree_sprites.png": "tree_anim.png",
    "Objects/Tree animations/tree apple sprites.png": "tree_apple.png",
    "Objects/Tree animations/tree pear sprites.png": "tree_pear.png",
    "Objects/Tree animations/tree peach sprites.png": "tree_peach.png",
    "Objects/Tree animations/tree orange sprites.png": "tree_orange.png",
    "Objects/Water Objects.png": "water_objects.png",
    "Objects/Boats.png": "boats.png",
    "Tilesets/Building parts/Mailbox Animation Frames.png": "mailbox.png",
    "emojis/Emoji spritesheet.png": "emoji.png",
    "Objects/Water well.png": "well.png",
    "Objects/Piknik blanket.png": "blanket.png",
    "Objects/Piknik basket.png": "basket.png",
    "Tilesets/Building parts/Animal Structures/Barn structures.png": "barn.png",
    "Tilesets/Building parts/Animal Structures/Chikcen_Houses.png": "coop.png",
    "Objects/Tree animations/tree_fall_animation_sprite_sheet.png": "tree_fall.png",
    "Animals/Chicken/chicken default.png": "chicken.png",
    "Animals/Cow/Brown cow animations.png": "cow.png",
    "Animals/Chicken/chicken brown.png": "chicken_brown.png",
    "Animals/Chicken/chicken red.png": "chicken_red.png",
    "Animals/Chicken/chicken blue.png": "chicken_blue.png",
    "Animals/Chicken/chicken green.png": "chicken_green.png",
    "Animals/Cow/Light cow animations.png": "cow_light.png",
    "Animals/Cow/Pink cow animation sprites.png": "cow_pink.png",
    "Animals/Cow/Purple cow animation sprites.png": "cow_purple.png",
    "Animals/Cow/Green cow animation sprites.png": "cow_green.png",
    "Animals/Chicken_Baby/Chicken_Baby.png": "chick.png",
    "Animals/Chicken_Baby/Chicken_Baby_Brown.png": "chick_brown.png",
    "Animals/Chicken_Baby/Chicken_Baby_Red.png": "chick_red.png",
    "Animals/Chicken_Baby/Chicken_Baby_Blue.png": "chick_blue.png",
    "Animals/Chicken_Baby/Chicken_Baby_Green.png": "chick_green.png",
    "Animals/Cow_Baby/baby brown cow animations sprites.png": "calf.png",
    "Animals/Cow_Baby/baby light cow animations sprites.png": "calf_light.png",
    "Animals/Cow_Baby/baby pink cow animations sprites.png": "calf_pink.png",
    "Animals/Cow_Baby/baby purple cow animations sprites.png": "calf_purple.png",
    "Animals/Cow_Baby/baby green cow animations sprites.png": "calf_green.png",
    "UI Sprites/ALL UI ASSETS on one sheet.png": "ui.png",
    "UI Sprites/Icons/special icons/Hearts.png": "hearts.png",
    "UI Sprites/Other UI sprites/Sliders/Sliders.png": "sliders.png",
}


def read_member(z: zipfile.ZipFile, suffix: str) -> bytes:
    for name in z.namelist():
        if name.endswith(suffix) and "__MACOSX" not in name:
            return z.read(name)
    raise KeyError(suffix)


def recolor(img: Image.Image, fn) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = (*fn(r, g, b), a)
    return img


P["x"] = (0, 0, 0, 70)  # soft shadow


def build(downloads: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(downloads / SPRITES) as zs, zipfile.ZipFile(downloads / UI) as zu:
        for suffix, name in COPY.items():
            z = zu if suffix.startswith(("UI Sprites", "fonts", "emojis")) else zs
            (OUT / name).write_bytes(read_member(z, suffix))
        tilled = Image.open(io.BytesIO(read_member(zs, "Tilesets/ground tiles/Old tiles/Tilled_Dirt_v2.png")))
        water = Image.open(io.BytesIO(read_member(zs, "Tilesets/ground tiles/Water.png")))
        ui = Image.open(io.BytesIO(read_member(zu, "UI Sprites/ALL UI ASSETS on one sheet.png"))).convert("RGBA")
        paw = Image.open(io.BytesIO(read_member(zu, "UI Sprites/Mouse sprites/Catpaw Mouse icon.png"))).convert("RGBA")
        point = Image.open(io.BytesIO(read_member(zu, "UI Sprites/Mouse sprites/Catpaw pointing Mouse icon.png"))).convert("RGBA")

    # burnt ground: the tilled-soil layer, darkened and desaturated toward ash grey
    def ashen(r, g, b):
        lum = (r * 0.3 + g * 0.59 + b * 0.11)
        return (int(lum * 0.45 + r * 0.12), int(lum * 0.43 + g * 0.1), int(lum * 0.45 + b * 0.1))
    with zipfile.ZipFile(downloads / SPRITES) as zs3:
        layers = Image.open(io.BytesIO(read_member(zs3, "Tilesets/ground tiles/New tiles/Grass_Tile_Layers.png"))).convert("RGBA")
    def charred(r, g, b):  # green → warm charcoal, keeping the light/dark structure
        v = (r + g + b) / 3
        return (int(v * 0.42 + 18), int(v * 0.36 + 14), int(v * 0.33 + 12))
    recolor(layers, charred).save(OUT / "ash.png")
    recolor(water, lambda r, g, b: (int(r * 0.62), int(g * 0.74), int(b * 0.86))).save(OUT / "water_deep.png")
    recolor(tilled.copy(), lambda r, g, b: (int(r * 0.72), int(g * 0.62), int(b * 0.55))).save(OUT / "tilled_wet.png")
    # deep water: the grass layer's rounded blob shapes as a translucent dark-blue overlay
    with zipfile.ZipFile(downloads / SPRITES) as zs2:
        grass = Image.open(io.BytesIO(read_member(zs2, "Tilesets/ground tiles/New tiles/Grass_Tile_Layers.png"))).convert("RGBA")
    deep = Image.new("RGBA", grass.size)
    gp, dp = grass.load(), deep.load()
    for y in range(grass.height):
        for x in range(grass.width):
            if gp[x, y][3] > 128:
                dp[x, y] = (18, 52, 92, 80)
    deep.save(OUT / "deep_mask.png")
    # UI pieces used as CSS 9-slices
    paw.resize((32, 32), Image.NEAREST).save(OUT / "cursor.png")
    point.resize((32, 32), Image.NEAREST).save(OUT / "cursor_point.png")
    ui.crop((11, 59, 37, 87)).save(OUT / "panel.png")
    ui.crop((345, 9, 375, 39)).save(OUT / "slot.png")
    ui.crop((345, 57, 375, 87)).save(OUT / "slot_sel.png")

    # picked fruit trees: each sheet's last fruit-drop frame (row 3, frame 11) is the bare tree with the fruit on
    # the ground beside it; keep only the tree (the largest opaque shape) so the bare tree is the same tree
    bare = Image.new("RGBA", (48 * 4, 48))
    for i, fruit in enumerate(["tree_apple", "tree_pear", "tree_peach", "tree_orange"]):
        frame = Image.open(OUT / f"{fruit}.png").convert("RGBA").crop((11 * 48, 3 * 48, 12 * 48, 4 * 48))
        bare.alpha_composite(largest_shape(frame), (48 * i, 0))
    bare.save(OUT / "fruit_bare.png")

    thin_fall_sheet(OUT).save(OUT / "thin_fall.png")
    thin_stump(OUT).save(OUT / "stump_thin.png")
    # slopes up to level 1 (light hill grass) and level 2 (darker), drawn from each hill sheet's colours
    meadow = Image.open(OUT / "grass.png").convert("RGBA").getpixel((1 * 16 + 8, 1 * 16 + 8))   # plain grass
    hill_top = Image.open(OUT / "hill1.png").convert("RGBA").getpixel((1 * 16 + 8, 1 * 16 + 8))
    ramp_art(OUT / "hill1.png", meadow).save(OUT / "ramp1.png")
    ramp_art(OUT / "hill2.png", hill_top).save(OUT / "ramp2.png")

    names = list(GEN)
    sheet = Image.new("RGBA", (16 * len(names), 16))
    for i, n in enumerate(names):
        sheet.alpha_composite(art(GEN[n], P), (16 * i, 0))
    sheet.save(OUT / "gen.png")
    (OUT / "gen.txt").write_text("\n".join(names) + "\n")

    (OUT / "CREDITS.md").write_text(
        "# Art credits\n\n"
        "Assets - From: **Sprout Lands** (Sprites pack and UI pack, premium) - By: **Cup Nooble**\n"
        "https://cupnooble.itch.io/\n\n"
        "License summary: modification allowed; use in commercial and non-commercial projects allowed;\n"
        "the asset pack itself may not be redistributed or resold, even modified; no NFTs or AI training;\n"
        "credit required. Only the sheets this game uses are included here.\n\n"
        "`gen.png`, `ash.png`, `water_deep.png` and `fruit_bare.png` are extra tiles made for this game from the pack;\n"
        "`ramp1.png` and `ramp2.png` (slopes) are drawn for this game in the hill sheets' colours.\n")
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    build(Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "Downloads")
